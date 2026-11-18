"""produtos-service: implementação da ESP-PRD-001 v2.0."""

import traceback
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Protocol

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .http_comum import (
    AUDIENCIA_PADRAO,
    EMISSOR_PADRAO,
    ChavesPublicas,
    Clock,
    ErroApi,
    agora_utc,
    autenticar,
    configurar_http,
    corpo_json,
    correlation_id,
    criar_logger,
    envelope,
    exigir_escopo,
    filtro_texto,
    instante,
    paginacao,
    preenchido,
)

NOME_SERVICO = "produtos-service"
TOPICO_DLT = "produtos.dlt"
UNIDADES = ("KG", "TON", "UN", "CX", "L")
TIPOS_TRANSPORTE = ("GRANEL", "REFRIGERADO", "CARGA_SECA", "PERIGOSO")
# RN-09: lista fixa de categorias (professor, F16 do Documento de Requisitos); conteúdo definido pelo grupo
CATEGORIAS = ("GRAOS", "INSUMOS", "SUBPRODUTOS", "LATICINIOS", "CARNES", "HORTIFRUTI", "BEBIDAS", "OUTROS")
ESCOPOS_CADASTRO = ("SUPPLIER", "BUYER")  # RN-01
PESO_MAXIMO = Decimal("999999999.999")  # RN-08


class EventBus(Protocol):
    def publish(self, topic: str, key: str, message: dict) -> None: ...
    def subscribe(self, topic: str, handler: Callable[[dict], None]) -> None: ...
    def disponivel(self) -> bool: ...


class ProdutoRepositorio(Protocol):
    def inserir(self, produto: dict) -> None: ...
    def obter(self, produto_id: str) -> dict | None: ...
    def listar(self, categoria: str | None, offset: int, limite: int) -> tuple[list[dict], int]: ...
    def marcar_movimentado(self, produto_id: str) -> bool: ...
    def atualizar_se_sem_movimentacao(self, produto: dict) -> bool: ...
    def excluir_se_sem_movimentacao(self, produto_id: str) -> bool: ...
    def disponivel(self) -> bool: ...


def _texto(corpo: dict, campo: str, minimo: int, maximo: int) -> str:
    valor = corpo.get(campo)
    if not isinstance(valor, str):
        raise ErroApi(422, "DADOS_INVALIDOS", f"O campo {campo} é obrigatório e deve ser texto.")
    valor = valor.strip()
    if not minimo <= len(valor) <= maximo:
        raise ErroApi(422, "DADOS_INVALIDOS", f"O campo {campo} deve ter de {minimo} a {maximo} caracteres.")
    return valor


def _enum(corpo: dict, campo: str, permitidos: tuple[str, ...], aparar: bool = False) -> str:
    valor = corpo.get(campo)
    if aparar and isinstance(valor, str):
        valor = valor.strip()
    if valor not in permitidos:
        raise ErroApi(422, "DADOS_INVALIDOS", f"O campo {campo} deve ser um de: {', '.join(permitidos)}.")
    return valor


def _peso_unitario(corpo: dict) -> Decimal | None:
    """RN-08: peso_unitario_kg é opcional; ausente ou null vira None."""
    valor: Any = corpo.get("peso_unitario_kg")
    if valor is None:
        return None
    erro = ErroApi(422, "DADOS_INVALIDOS", "peso_unitario_kg deve ser número maior que 0, com até 3 casas decimais e até 999999999.999.")
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise erro
    try:
        numero = Decimal(str(valor))
    except InvalidOperation:
        raise erro
    if not numero.is_finite() or numero.as_tuple().exponent < -3 or numero <= 0 or numero > PESO_MAXIMO:
        raise erro
    return numero


def _dados_do_corpo(corpo: Any) -> dict:
    """RN-02 e RN-09: campos editáveis do produto, iguais no cadastro (API-04) e na alteração (API-07)."""
    if not isinstance(corpo, dict):
        raise ErroApi(422, "DADOS_INVALIDOS", "O corpo deve ser um objeto JSON.")
    return {
        "nome": _texto(corpo, "nome", 2, 255),
        "categoria": _enum(corpo, "categoria", CATEGORIAS, aparar=True),
        "unidade": _enum(corpo, "unidade", UNIDADES),
        "tipo_transporte": _enum(corpo, "tipo_transporte", TIPOS_TRANSPORTE),
        "peso_unitario_kg": _peso_unitario(corpo),
    }


def _numero_json(valor) -> float | None:
    return None if valor is None else float(valor)


def _projecao(produto: dict) -> dict:
    """Resposta das APIs: atributos do §6.1, com o peso como número JSON."""
    resposta = dict(produto)
    resposta["peso_unitario_kg"] = _numero_json(produto.get("peso_unitario_kg"))
    resposta["com_movimentacao"] = bool(produto.get("com_movimentacao"))
    return resposta


def _payload_evento(produto: dict) -> dict:
    """Mapeamento do §7.4: atributos em snake_case para o payload em camelCase."""
    return {
        "produtoId": produto["produto_id"],
        "nome": produto["nome"],
        "categoria": produto["categoria"],
        "unidade": produto["unidade"],
        "tipoTransporte": produto["tipo_transporte"],
        "pesoUnitarioKg": _numero_json(produto["peso_unitario_kg"]),
        "cadastradoPor": {"empresaId": produto["cadastrado_por_empresa_id"], "usuarioId": produto["cadastrado_por_usuario_id"]},
        "cadastradoEm": produto["cadastrado_em"],
    }


def create_app(event_bus: EventBus, clock: Clock, repositorio: ProdutoRepositorio, chaves_publicas: ChavesPublicas,
               emissor: str = EMISSOR_PADRAO, audiencia: str = AUDIENCIA_PADRAO) -> FastAPI:
    app = FastAPI(title="Produtos API", version="2.1", docs_url="/docs", openapi_url="/openapi.json")
    logger = criar_logger(NOME_SERVICO)

    def prontas() -> bool:
        return bool(repositorio.disponivel()) and bool(event_bus.disponivel())

    configurar_http(app, clock, NOME_SERVICO, prontas, logger)

    def publicar(topico: str, chave: str, correlacao: str, payload: dict) -> None:
        event_bus.publish(topico, chave, envelope(topico, NOME_SERVICO, chave, correlacao, clock, payload))

    @app.post("/api/v1/produtos", status_code=201)
    async def cadastrar_produto(request: Request):
        claims = autenticar(request, chaves_publicas, clock, emissor, audiencia)
        exigir_escopo(claims, ESCOPOS_CADASTRO)
        dados = _dados_do_corpo(await corpo_json(request))
        momento = instante(agora_utc(clock))
        produto = {
            "produto_id": str(uuid.uuid4()),
            **dados,
            "cadastrado_por_empresa_id": claims["tenant_id"],
            "cadastrado_por_usuario_id": claims["sub"],
            "cadastrado_em": momento,
            "atualizado_em": momento,
            "com_movimentacao": False,
        }
        try:
            repositorio.inserir(dict(produto))
        except Exception:
            logger.exception("falha ao gravar produto", extra={"correlationId": correlation_id(request)})
            raise ErroApi(500, "ERRO_INTERNO", "Não foi possível gravar o produto.")
        publicar("produto_cadastrado", produto["produto_id"], correlation_id(request), _payload_evento(produto))
        logger.info(f"produto cadastrado {produto['produto_id']}", extra={"correlationId": correlation_id(request)})
        return JSONResponse(_projecao(produto), status_code=201)

    @app.get("/api/v1/produtos/{produto_id}")
    async def consultar_produto(produto_id: str, request: Request):
        autenticar(request, chaves_publicas, clock, emissor, audiencia, exige_empresa=False)
        produto = repositorio.obter(produto_id)
        if produto is None:
            raise ErroApi(404, "PRODUTO_NAO_ENCONTRADO", f"Produto {produto_id} não cadastrado.")
        return JSONResponse(_projecao(produto))

    @app.get("/api/v1/produtos")
    async def listar_produtos(request: Request):
        autenticar(request, chaves_publicas, clock, emissor, audiencia, exige_empresa=False)
        page, size = paginacao(request)
        itens, total = repositorio.listar(filtro_texto(request, "categoria"), (page - 1) * size, size)
        return JSONResponse({"itens": [_projecao(p) for p in itens], "page": page, "size": size, "total": total})

    def produto_alteravel(produto_id: str, claims: dict) -> dict:
        """RN-10 e RN-11: só a empresa que cadastrou altera ou exclui, e só enquanto não houver movimentação."""
        produto = repositorio.obter(produto_id)
        if produto is None:
            raise ErroApi(404, "PRODUTO_NAO_ENCONTRADO", f"Produto {produto_id} não cadastrado.")
        if produto["cadastrado_por_empresa_id"] != claims["tenant_id"]:
            raise ErroApi(403, "PRODUTO_DE_OUTRA_EMPRESA", "Só a empresa que cadastrou o produto pode alterá-lo ou excluí-lo.")
        if produto.get("com_movimentacao"):
            raise ErroApi(409, "PRODUTO_COM_MOVIMENTACAO", "O produto já tem fornecimento e não pode ser alterado nem excluído. "
                                                          "Uma especificação diferente é outro produto: cadastre um novo.")
        return produto

    @app.put("/api/v1/produtos/{produto_id}")
    async def alterar_produto(produto_id: str, request: Request):
        claims = autenticar(request, chaves_publicas, clock, emissor, audiencia)
        exigir_escopo(claims, ESCOPOS_CADASTRO)
        dados = _dados_do_corpo(await corpo_json(request))
        atual = produto_alteravel(produto_id, claims)
        momento = instante(agora_utc(clock))
        novo = {**atual, **dados, "atualizado_em": momento}
        try:
            alterado = repositorio.atualizar_se_sem_movimentacao(dict(novo))
        except Exception:
            logger.exception("falha ao alterar produto", extra={"correlationId": correlation_id(request)})
            raise ErroApi(500, "ERRO_INTERNO", "Não foi possível alterar o produto.")
        if not alterado:
            # O fornecimento_criado chegou entre a leitura e a gravação
            raise ErroApi(409, "PRODUTO_COM_MOVIMENTACAO", "O produto passou a ter fornecimento e não pode mais ser alterado.")
        publicar("produto_atualizado", produto_id, correlation_id(request), {
            "produtoId": produto_id,
            "nome": novo["nome"],
            "categoria": novo["categoria"],
            "unidade": novo["unidade"],
            "tipoTransporte": novo["tipo_transporte"],
            "pesoUnitarioKg": _numero_json(novo["peso_unitario_kg"]),
            "atualizadoPor": {"empresaId": claims["tenant_id"], "usuarioId": claims["sub"]},
            "atualizadoEm": momento,
        })
        return JSONResponse(_projecao(novo))

    @app.delete("/api/v1/produtos/{produto_id}", status_code=204)
    async def excluir_produto(produto_id: str, request: Request):
        claims = autenticar(request, chaves_publicas, clock, emissor, audiencia)
        exigir_escopo(claims, ESCOPOS_CADASTRO)
        produto_alteravel(produto_id, claims)
        try:
            excluido = repositorio.excluir_se_sem_movimentacao(produto_id)
        except Exception:
            logger.exception("falha ao excluir produto", extra={"correlationId": correlation_id(request)})
            raise ErroApi(500, "ERRO_INTERNO", "Não foi possível excluir o produto.")
        if not excluido:
            raise ErroApi(409, "PRODUTO_COM_MOVIMENTACAO", "O produto passou a ter fornecimento e não pode mais ser excluído.")
        publicar("produto_excluido", produto_id, correlation_id(request), {
            "produtoId": produto_id,
            "excluidoPor": {"empresaId": claims["tenant_id"], "usuarioId": claims["sub"]},
            "excluidoEm": instante(agora_utc(clock)),
        })
        return Response(status_code=204)

    # ------------------------------------------------ fornecimento_criado (RN-11)

    def enviar_dlt(mensagem: Any, erro: str, pilha: str) -> None:
        chave = "desconhecido"
        correlacao = str(uuid.uuid4())
        if isinstance(mensagem, dict):
            if preenchido(mensagem.get("aggregateId")):
                chave = mensagem["aggregateId"]
            elif preenchido(mensagem.get("eventId")):
                chave = mensagem["eventId"]
            if preenchido(mensagem.get("correlationId")):
                correlacao = mensagem["correlationId"]
        publicar(TOPICO_DLT, chave, correlacao, {"originalEvent": mensagem, "error": erro, "stackTrace": pilha, "failedAtAttempt": 1})

    def ao_receber_fornecimento(mensagem: Any) -> None:
        """Marca o produto como movimentado. Marcar de novo não muda nada, então não precisa de processed_events."""
        payload = mensagem.get("payload") if isinstance(mensagem, dict) else None
        if not isinstance(mensagem, dict) or not preenchido(mensagem.get("eventId")) or not isinstance(payload, dict) \
                or not preenchido(payload.get("produtoId")):
            logger.warning("fornecimento_criado invalido enviado para a DLT")
            enviar_dlt(mensagem, "Mensagem sem eventId ou sem payload.produtoId.", "")
            return
        try:
            if not repositorio.marcar_movimentado(payload["produtoId"]):
                logger.info(f"fornecimento de produto desconhecido ignorado: {payload['produtoId']}")
        except Exception as erro:
            logger.exception("falha ao marcar produto movimentado")
            enviar_dlt(mensagem, str(erro) or erro.__class__.__name__, traceback.format_exc())

    event_bus.subscribe("fornecimento_criado", ao_receber_fornecimento)

    return app
