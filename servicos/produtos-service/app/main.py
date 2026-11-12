"""produtos-service: implementação da ESP-PRD-001 v1.4."""

import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Protocol

from fastapi import FastAPI, Request
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
UNIDADES = ("KG", "TON", "UN", "CX", "L")
TIPOS_TRANSPORTE = ("GRANEL", "REFRIGERADO", "CARGA_SECA", "PERIGOSO")
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
    def disponivel(self) -> bool: ...


def _texto(corpo: dict, campo: str, minimo: int, maximo: int) -> str:
    valor = corpo.get(campo)
    if not isinstance(valor, str):
        raise ErroApi(422, "DADOS_INVALIDOS", f"O campo {campo} é obrigatório e deve ser texto.")
    valor = valor.strip()
    if not minimo <= len(valor) <= maximo:
        raise ErroApi(422, "DADOS_INVALIDOS", f"O campo {campo} deve ter de {minimo} a {maximo} caracteres.")
    return valor


def _enum(corpo: dict, campo: str, permitidos: tuple[str, ...]) -> str:
    valor = corpo.get(campo)
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


def _numero_json(valor) -> float | None:
    return None if valor is None else float(valor)


def _projecao(produto: dict) -> dict:
    """Resposta da API-04/05/06: atributos do §6.1, com o peso como número JSON."""
    resposta = dict(produto)
    resposta["peso_unitario_kg"] = _numero_json(produto.get("peso_unitario_kg"))
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
    app = FastAPI(title="Produtos API", version="1.4", docs_url="/docs", openapi_url="/openapi.json")
    logger = criar_logger(NOME_SERVICO)

    def prontas() -> bool:
        return bool(repositorio.disponivel()) and bool(event_bus.disponivel())

    configurar_http(app, clock, NOME_SERVICO, prontas, logger)

    @app.post("/api/v1/produtos", status_code=201)
    async def cadastrar_produto(request: Request):
        claims = autenticar(request, chaves_publicas, clock, emissor, audiencia)
        exigir_escopo(claims, ESCOPOS_CADASTRO)
        corpo = await corpo_json(request)
        if not isinstance(corpo, dict):
            raise ErroApi(422, "DADOS_INVALIDOS", "O corpo deve ser um objeto JSON.")
        produto = {
            "produto_id": str(uuid.uuid4()),
            "nome": _texto(corpo, "nome", 2, 255),
            "categoria": _texto(corpo, "categoria", 2, 64),
            "unidade": _enum(corpo, "unidade", UNIDADES),
            "tipo_transporte": _enum(corpo, "tipo_transporte", TIPOS_TRANSPORTE),
            "peso_unitario_kg": _peso_unitario(corpo),
            "cadastrado_por_empresa_id": claims["tenant_id"],
            "cadastrado_por_usuario_id": claims["sub"],
            "cadastrado_em": instante(agora_utc(clock)),
        }
        try:
            repositorio.inserir(dict(produto))
        except Exception:
            logger.exception("falha ao gravar produto", extra={"correlationId": correlation_id(request)})
            raise ErroApi(500, "ERRO_INTERNO", "Não foi possível gravar o produto.")
        mensagem = envelope("produto_cadastrado", NOME_SERVICO, produto["produto_id"], correlation_id(request), clock, _payload_evento(produto))
        event_bus.publish("produto_cadastrado", produto["produto_id"], mensagem)
        logger.info(f"produto cadastrado {produto['produto_id']}", extra={"correlationId": correlation_id(request)})
        return JSONResponse(_projecao(produto), status_code=201)

    @app.get("/api/v1/produtos/{produto_id}")
    async def consultar_produto(produto_id: str, request: Request):
        autenticar(request, chaves_publicas, clock, emissor, audiencia)
        produto = repositorio.obter(produto_id)
        if produto is None:
            raise ErroApi(404, "PRODUTO_NAO_ENCONTRADO", f"Produto {produto_id} não cadastrado.")
        return JSONResponse(_projecao(produto))

    @app.get("/api/v1/produtos")
    async def listar_produtos(request: Request):
        autenticar(request, chaves_publicas, clock, emissor, audiencia)
        page, size = paginacao(request)
        itens, total = repositorio.listar(filtro_texto(request, "categoria"), (page - 1) * size, size)
        return JSONResponse({"itens": [_projecao(p) for p in itens], "page": page, "size": size, "total": total})

    return app
