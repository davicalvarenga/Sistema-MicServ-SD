"""fornecimentos-service: implementação da ESP-FRN-001 v2.0."""

import traceback
import uuid
from contextlib import AbstractContextManager
from datetime import datetime, timezone
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
    empresas_do_token,
    envelope,
    exigir_escopo,
    filtro_texto,
    instante,
    paginacao,
    preenchido,
)

NOME_SERVICO = "fornecimentos-service"
TOPICO_DLT = "fornecimentos.dlt"
ESCOPOS_CADASTRO = ("SUPPLIER",)  # RN-01
ESCOPOS_CONSULTA = ("BUYER", "SUPPLIER", "TENANT_ADMIN")  # RN-05
ESCOPOS_ALTERACAO = ("SUPPLIER",)  # RN-17
STATUS_CANCELADO = "CANCELADO"
STATUS_VENDA_CONCLUIDA = "VENDA_CONCLUIDA"
MAXIMO = Decimal("9999999999.99")
ZERO = Decimal("0")
# Siglas das 27 unidades da federação (IBGE), usadas na origem do fornecimento (RN-02)
UFS = ("AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
       "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO")


class EventBus(Protocol):
    def publish(self, topic: str, key: str, message: dict) -> None: ...
    def subscribe(self, topic: str, handler: Callable[[dict], None]) -> None: ...
    def disponivel(self) -> bool: ...


class RepositorioFornecimentos(Protocol):
    def transacao(self) -> AbstractContextManager[None]: ...
    def evento_processado(self, event_id: str) -> bool: ...
    def registrar_evento_processado(self, event_id: str) -> None: ...
    def salvar_produto_referencia(self, produto: dict) -> None: ...
    def obter_produto_referencia(self, produto_id: str) -> dict | None: ...
    def inserir_fornecimento(self, fornecimento: dict) -> None: ...
    def obter_fornecimento(self, fornecimento_id: str) -> dict | None: ...
    def listar_fornecimentos(self, produto_id: str | None, offset: int, limite: int,
                             incluir_zeradas_de: tuple[str, ...]) -> tuple[list[dict], int]: ...
    def alterar_preco(self, fornecimento_id: str, preco: Decimal, atualizado_em: datetime) -> dict | None: ...
    def zerar_disponivel(self, fornecimento_id: str, atualizado_em: datetime) -> tuple[dict, Decimal] | None: ...
    def aplicar_movimento(self, fornecimento_id: str, delta_disponivel: Decimal,
                          delta_reservada: Decimal, atualizado_em: datetime) -> dict | None: ...
    def obter_reserva(self, pedido_id: str, fornecimento_id: str) -> dict | None: ...
    def salvar_reserva(self, reserva: dict) -> None: ...
    def disponivel(self) -> bool: ...


class MensagemInvalida(Exception):
    """Mensagem consumida que não atende às regras RN-07, RN-09, RN-13 ou RN-15."""


def decimal_valido(valor: Any, minimo_exclusivo: bool = True, maximo: Decimal | None = MAXIMO) -> Decimal | None:
    """Valor decimal do glossário: número JSON (não booleano), até 2 casas, dentro dos limites."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    try:
        numero = Decimal(str(valor))
    except InvalidOperation:
        return None
    if not numero.is_finite() or numero.as_tuple().exponent < -2:
        return None
    if (minimo_exclusivo and numero <= ZERO) or numero < ZERO:
        return None
    if maximo is not None and numero > maximo:
        return None
    return numero


def origem_valida(valor: Any) -> dict | None:
    """Origem do fornecimento (RN-02): objeto com cidade (1 a 255 caracteres) e uf (sigla da lista UFS)."""
    if not isinstance(valor, dict):
        return None
    cidade, uf = valor.get("cidade"), valor.get("uf")
    if not isinstance(cidade, str) or not 1 <= len(cidade.strip()) <= 255:
        return None
    if not isinstance(uf, str) or uf.strip() not in UFS:
        return None
    return {"cidade": cidade.strip(), "uf": uf.strip()}


def numero_json(valor: Decimal | None) -> float | None:
    return None if valor is None else float(valor)


def projecao(fornecimento: dict) -> dict:
    """Resposta da API-04/05/06: atributos do §6.1 com decimais como número JSON."""
    resposta = dict(fornecimento)
    resposta["origem"] = dict(fornecimento["origem"])
    for campo in ("preco", "quantidade_disponivel", "quantidade_reservada"):
        resposta[campo] = numero_json(fornecimento[campo])
    for campo in ("criado_em", "atualizado_em"):
        if isinstance(resposta[campo], datetime):
            resposta[campo] = instante(resposta[campo])
    return resposta


def create_app(event_bus: EventBus, clock: Clock, repositorio: RepositorioFornecimentos, chaves_publicas: ChavesPublicas,
               emissor: str = EMISSOR_PADRAO, audiencia: str = AUDIENCIA_PADRAO) -> FastAPI:
    app = FastAPI(title="Fornecimentos API", version="2.0", docs_url="/docs", openapi_url="/openapi.json")
    logger = criar_logger(NOME_SERVICO)

    def prontas() -> bool:
        return bool(repositorio.disponivel()) and bool(event_bus.disponivel())

    configurar_http(app, clock, NOME_SERVICO, prontas, logger)

    # ------------------------------------------------------------------ API REST

    @app.post("/api/v1/fornecimentos", status_code=201)
    async def cadastrar_fornecimento(request: Request):
        claims = autenticar(request, chaves_publicas, clock, emissor, audiencia)
        exigir_escopo(claims, ESCOPOS_CADASTRO)
        corpo = await corpo_json(request)
        if not isinstance(corpo, dict):
            raise ErroApi(422, "DADOS_INVALIDOS", "O corpo deve ser um objeto JSON.")
        produto_id = corpo.get("produto_id")
        if not isinstance(produto_id, str) or not preenchido(produto_id):
            raise ErroApi(422, "DADOS_INVALIDOS", "O campo produto_id é obrigatório e deve ser texto.")
        preco = decimal_valido(corpo.get("preco"), minimo_exclusivo=False)  # RN-02: zero é permitido (RN-16 do Documento)
        if preco is None:
            raise ErroApi(422, "DADOS_INVALIDOS", "preco deve ser número maior ou igual a 0, com até 2 casas decimais e até 9999999999.99.")
        quantidade = decimal_valido(corpo.get("quantidade_disponivel"), minimo_exclusivo=False)
        if quantidade is None:
            raise ErroApi(422, "DADOS_INVALIDOS", "quantidade_disponivel deve ser número maior ou igual a 0, com até 2 casas decimais e até 9999999999.99.")
        origem = origem_valida(corpo.get("origem"))
        if origem is None:
            raise ErroApi(422, "DADOS_INVALIDOS", "origem deve ser objeto com cidade (1 a 255 caracteres) e uf (sigla de UF em maiúsculas).")
        produto_id = produto_id.strip()
        produto = repositorio.obter_produto_referencia(produto_id)
        if produto is None or not produto["ativo"]:
            raise ErroApi(422, "PRODUTO_INEXISTENTE", f"Produto {produto_id} não é conhecido ou foi excluído.")
        momento = instante(agora_utc(clock))
        fornecimento = {
            "fornecimento_id": str(uuid.uuid4()),
            "fornecedor_id": claims["tenant_id"],
            "produto_id": produto_id,
            "unidade": produto["unidade"],
            "preco": preco,
            "quantidade_disponivel": quantidade,
            "quantidade_reservada": ZERO,
            "origem": origem,
            "criado_por_usuario_id": claims["sub"],
            "criado_em": momento,
            "atualizado_em": momento,
        }
        try:
            with repositorio.transacao():
                repositorio.inserir_fornecimento(dict(fornecimento))
        except Exception:
            logger.exception("falha ao gravar fornecimento", extra={"correlationId": correlation_id(request)})
            raise ErroApi(500, "ERRO_INTERNO", "Não foi possível gravar o fornecimento.")
        payload = {
            "fornecimentoId": fornecimento["fornecimento_id"],
            "fornecedorId": fornecimento["fornecedor_id"],
            "produtoId": produto_id,
            "unidade": fornecimento["unidade"],
            "preco": numero_json(preco),
            "quantidadeDisponivel": numero_json(quantidade),
            "origem": dict(origem),
            "criadoPor": {"empresaId": claims["tenant_id"], "usuarioId": claims["sub"]},
            "criadoEm": momento,
            # Grupo econômico do fornecedor (claim group_id), para Mercado e Negociação aplicarem a trava de auto-negociação
            "grupoId": claims["group_id"] if preenchido(claims.get("group_id")) else None,
        }
        chave = fornecimento["fornecimento_id"]
        event_bus.publish("fornecimento_criado", chave, envelope("fornecimento_criado", NOME_SERVICO, chave, correlation_id(request), clock, payload))
        return JSONResponse(projecao(fornecimento), status_code=201)

    @app.get("/api/v1/fornecimentos/{fornecimento_id}")
    async def consultar_fornecimento(fornecimento_id: str, request: Request):
        claims = autenticar(request, chaves_publicas, clock, emissor, audiencia, exige_empresa=False)
        exigir_escopo(claims, ESCOPOS_CONSULTA)
        fornecimento = repositorio.obter_fornecimento(fornecimento_id)
        if fornecimento is None:
            raise ErroApi(404, "FORNECIMENTO_NAO_ENCONTRADO", f"Fornecimento {fornecimento_id} não cadastrado.")
        return JSONResponse(projecao(fornecimento))

    @app.get("/api/v1/fornecimentos")
    async def listar_fornecimentos(request: Request):
        claims = autenticar(request, chaves_publicas, clock, emissor, audiencia, exige_empresa=False)
        exigir_escopo(claims, ESCOPOS_CONSULTA)
        page, size = paginacao(request)
        # RN-18: oferta com disponível zero não aparece, exceto para o próprio fornecedor (histórico).
        # Na visão de grupo econômico, o fornecedor vê as ofertas zeradas de todas as empresas do grupo.
        dono = empresas_do_token(claims) if claims["active_scope"] == "SUPPLIER" else ()
        itens, total = repositorio.listar_fornecimentos(filtro_texto(request, "produto_id"), (page - 1) * size, size, dono)
        return JSONResponse({"itens": [projecao(f) for f in itens], "page": page, "size": size, "total": total})

    @app.patch("/api/v1/fornecimentos/{fornecimento_id}")
    async def alterar_fornecimento(fornecimento_id: str, request: Request):
        """RF-11: repor quantidade, mudar o preço (vale para todo o estoque da oferta) ou encerrar a oferta."""
        claims = autenticar(request, chaves_publicas, clock, emissor, audiencia)
        exigir_escopo(claims, ESCOPOS_ALTERACAO)
        corpo = await corpo_json(request)
        if not isinstance(corpo, dict):
            raise ErroApi(422, "DADOS_INVALIDOS", "O corpo deve ser um objeto JSON.")
        if not any(campo in corpo for campo in ("preco", "repor", "encerrar")):
            raise ErroApi(422, "DADOS_INVALIDOS", "Informe preco, repor ou encerrar.")
        encerrar = corpo.get("encerrar")
        if "encerrar" in corpo and encerrar is not True:
            raise ErroApi(422, "DADOS_INVALIDOS", "encerrar só aceita o valor true.")
        if encerrar and ("preco" in corpo or "repor" in corpo):
            raise ErroApi(422, "DADOS_INVALIDOS", "encerrar não pode ser combinado com preco ou repor.")
        preco = None
        if "preco" in corpo:
            preco = decimal_valido(corpo["preco"], minimo_exclusivo=False)
            if preco is None:
                raise ErroApi(422, "DADOS_INVALIDOS", "preco deve ser número maior ou igual a 0, com até 2 casas decimais e até 9999999999.99.")
        repor = None
        if "repor" in corpo:
            repor = decimal_valido(corpo["repor"])
            if repor is None:
                raise ErroApi(422, "DADOS_INVALIDOS", "repor deve ser número maior que 0, com até 2 casas decimais e até 9999999999.99.")
        atual = repositorio.obter_fornecimento(fornecimento_id)
        if atual is None:
            raise ErroApi(404, "FORNECIMENTO_NAO_ENCONTRADO", f"Fornecimento {fornecimento_id} não cadastrado.")
        if atual["fornecedor_id"] != claims["tenant_id"]:
            raise ErroApi(403, "FORNECIMENTO_DE_OUTRA_EMPRESA", "Só o fornecedor dono da oferta pode alterá-la.")
        if repor is not None and Decimal(str(atual["quantidade_disponivel"])) + repor > MAXIMO:
            raise ErroApi(422, "DADOS_INVALIDOS", "A reposição deixaria a quantidade disponível acima de 9999999999.99.")
        momento = agora_utc(clock)
        movimentos: list[tuple[str, Decimal]] = []
        alterado = None
        try:
            with repositorio.transacao():
                if preco is not None:
                    alterado = repositorio.alterar_preco(fornecimento_id, preco, momento)
                if repor is not None:
                    alterado = repositorio.aplicar_movimento(fornecimento_id, repor, ZERO, momento)
                    movimentos.append(("REPOSICAO", repor))
                if encerrar:
                    resultado = repositorio.zerar_disponivel(fornecimento_id, momento)
                    alterado = resultado[0] if resultado else None
                    if resultado and resultado[1] > ZERO:
                        movimentos.append(("ENCERRAMENTO", resultado[1]))
                if alterado is None:
                    raise RuntimeError(f"Fornecimento {fornecimento_id} não pôde ser alterado.")
        except Exception:
            logger.exception("falha ao alterar fornecimento", extra={"correlationId": correlation_id(request)})
            raise ErroApi(500, "ERRO_INTERNO", "Não foi possível alterar o fornecimento.")
        correlacao = correlation_id(request)
        for operacao, quantidade in movimentos:
            topico, chave, dados = estoque_atualizado(alterado, operacao, quantidade, None)
            publicar(topico, chave, correlacao, dados)
        if preco is not None or movimentos:
            publicar("fornecimento_atualizado", fornecimento_id, correlacao, {
                "fornecimentoId": fornecimento_id,
                "fornecedorId": alterado["fornecedor_id"],
                "produtoId": alterado["produto_id"],
                "unidade": alterado["unidade"],
                "preco": numero_json(alterado["preco"]),
                "quantidadeDisponivel": numero_json(alterado["quantidade_disponivel"]),
                "origem": dict(alterado["origem"]),
                "atualizadoPor": {"empresaId": claims["tenant_id"], "usuarioId": claims["sub"]},
                "atualizadoEm": instante(momento),
            })
        return JSONResponse(projecao(alterado))

    # --------------------------------------------------------- Eventos consumidos

    def publicar(topico: str, chave: str, correlacao: str, payload: dict) -> None:
        event_bus.publish(topico, chave, envelope(topico, NOME_SERVICO, chave, correlacao, clock, payload))

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

    def validar_envelope(mensagem: Any) -> dict:
        if not isinstance(mensagem, dict):
            raise MensagemInvalida("A mensagem não é um objeto.")
        if not preenchido(mensagem.get("eventId")):
            raise MensagemInvalida("eventId ausente ou vazio.")
        if not isinstance(mensagem.get("payload"), dict):
            raise MensagemInvalida("payload ausente ou não é objeto.")
        return mensagem["payload"]

    def exigir_textos(payload: dict, campos: tuple[str, ...]) -> None:
        for campo in campos:
            if not preenchido(payload.get(campo)):
                raise MensagemInvalida(f"payload.{campo} ausente ou vazio.")

    def ao_receber(processar: Callable[[dict, dict, str], list[tuple[str, str, dict]]], validar: Callable[[dict, dict], None]):
        """Moldura comum dos handlers: valida, aplica idempotência, processa numa transação e publica depois."""

        def handler(mensagem: Any) -> None:
            try:
                payload = validar_envelope(mensagem)
                validar(payload, mensagem)
            except MensagemInvalida as erro:
                logger.warning(f"mensagem invalida enviada para a DLT: {erro}")
                enviar_dlt(mensagem, str(erro), "")
                return
            correlacao = mensagem["correlationId"] if preenchido(mensagem.get("correlationId")) else str(uuid.uuid4())
            try:
                with repositorio.transacao():
                    if repositorio.evento_processado(mensagem["eventId"]):
                        logger.info(f"evento ja processado ignorado: {mensagem['eventId']}", extra={"correlationId": correlacao})
                        return
                    publicacoes = processar(mensagem, payload, correlacao)
                    repositorio.registrar_evento_processado(mensagem["eventId"])
            except Exception as erro:
                logger.exception("falha ao processar mensagem", extra={"correlationId": correlacao})
                enviar_dlt(mensagem, str(erro) or erro.__class__.__name__, traceback.format_exc())
                return
            for topico, chave, dados in publicacoes:
                publicar(topico, chave, correlacao, dados)

        return handler

    # produto_cadastrado (RF-05, RN-07)

    def validar_produto(payload: dict, mensagem: dict) -> None:
        exigir_textos(payload, ("produtoId", "nome", "unidade", "tipoTransporte"))
        texto = mensagem.get("timestamp")
        if not isinstance(texto, str):
            raise MensagemInvalida("timestamp ausente.")
        try:
            datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except ValueError:
            raise MensagemInvalida("timestamp não é um instante válido.")

    def processar_produto(mensagem: dict, payload: dict, correlacao: str):
        if repositorio.obter_produto_referencia(payload["produtoId"]) is None:
            versao = datetime.fromisoformat(mensagem["timestamp"].replace("Z", "+00:00"))
            if versao.tzinfo is None:
                versao = versao.replace(tzinfo=timezone.utc)
            repositorio.salvar_produto_referencia({
                "produto_id": payload["produtoId"], "nome": payload["nome"], "unidade": payload["unidade"],
                "tipo_transporte": payload["tipoTransporte"], "ativo": True, "versao_evento": instante(versao),
            })
        return []

    # produto_atualizado e produto_excluido (RN-20)

    def versao_da(mensagem: dict) -> str:
        versao = datetime.fromisoformat(mensagem["timestamp"].replace("Z", "+00:00"))
        if versao.tzinfo is None:
            versao = versao.replace(tzinfo=timezone.utc)
        return instante(versao)

    def processar_produto_atualizado(mensagem: dict, payload: dict, correlacao: str):
        atual = repositorio.obter_produto_referencia(payload["produtoId"])
        versao = versao_da(mensagem)
        # Eventos de produto chegam por tópicos diferentes: só aplica o que for mais novo que o último aplicado
        if atual is None or versao > atual["versao_evento"]:
            repositorio.salvar_produto_referencia({
                "produto_id": payload["produtoId"], "nome": payload["nome"], "unidade": payload["unidade"],
                "tipo_transporte": payload["tipoTransporte"], "ativo": True if atual is None else atual["ativo"],
                "versao_evento": versao,
            })
        return []

    def validar_produto_excluido(payload: dict, mensagem: dict) -> None:
        exigir_textos(payload, ("produtoId",))
        validar_produto({"produtoId": payload["produtoId"], "nome": "-", "unidade": "-", "tipoTransporte": "-"}, mensagem)

    def processar_produto_excluido(mensagem: dict, payload: dict, correlacao: str):
        atual = repositorio.obter_produto_referencia(payload["produtoId"])
        versao = versao_da(mensagem)
        if atual is None:
            # Exclusão antes do cadastro (tópicos diferentes): guarda o produto inativo para recusar o cadastro tardio
            repositorio.salvar_produto_referencia({"produto_id": payload["produtoId"], "nome": "", "unidade": "",
                                                   "tipo_transporte": "", "ativo": False, "versao_evento": versao})
        elif versao >= atual["versao_evento"]:
            repositorio.salvar_produto_referencia({**atual, "ativo": False, "versao_evento": versao})
        return []

    # pedido_criado (RF-06, RN-13, RN-14)

    def validar_pedido_criado(payload: dict, mensagem: dict) -> None:
        exigir_textos(payload, ("pedidoId", "fornecimentoId", "produtoId", "fornecedorId", "status"))
        if decimal_valido(payload.get("quantidade"), maximo=None) is None:
            raise MensagemInvalida("payload.quantidade deve ser número maior que 0 com até 2 casas decimais.")

    def estoque_atualizado(fornecimento: dict, operacao: str, quantidade: Decimal, pedido_id: str | None) -> tuple[str, str, dict]:
        return ("estoque_atualizado", fornecimento["fornecimento_id"], {
            "fornecimentoId": fornecimento["fornecimento_id"],
            "produtoId": fornecimento["produto_id"],
            "fornecedorId": fornecimento["fornecedor_id"],
            "operacao": operacao,
            "quantidadeMovimentada": numero_json(quantidade),
            "quantidadeDisponivel": numero_json(fornecimento["quantidade_disponivel"]),
            "quantidadeReservada": numero_json(fornecimento["quantidade_reservada"]),
            "pedidoId": pedido_id,
            "atualizadoEm": instante(agora_utc(clock)),
        })

    def processar_pedido_criado(mensagem: dict, payload: dict, correlacao: str):
        pedido_id, fornecimento_id = payload["pedidoId"], payload["fornecimentoId"]
        quantidade = decimal_valido(payload["quantidade"], maximo=None)
        if repositorio.obter_reserva(pedido_id, fornecimento_id) is not None:
            return []
        momento = agora_utc(clock)
        atual = repositorio.obter_fornecimento(fornecimento_id)
        if atual is not None:
            atualizado = repositorio.aplicar_movimento(fornecimento_id, -quantidade, quantidade, momento)
            if atualizado is not None:
                repositorio.salvar_reserva({
                    "pedido_id": pedido_id, "fornecimento_id": fornecimento_id, "quantidade": quantidade,
                    "situacao": "RESERVADA", "criado_em": instante(momento), "atualizado_em": instante(momento),
                })
                return [estoque_atualizado(atualizado, "RESERVA", quantidade, pedido_id)]
        recusa = {
            "pedidoId": pedido_id,
            "fornecimentoId": fornecimento_id,
            "quantidadeSolicitada": numero_json(quantidade),
            "quantidadeDisponivel": None if atual is None else numero_json(atual["quantidade_disponivel"]),
            "motivo": "FORNECIMENTO_INEXISTENTE" if atual is None else "ESTOQUE_INSUFICIENTE",
            "recusadoEm": instante(momento),
        }
        return [("reserva_estoque_recusada", pedido_id, recusa)]

    # pedido_atualizado (RF-07, RN-15, RN-16)

    def validar_pedido_atualizado(payload: dict, mensagem: dict) -> None:
        exigir_textos(payload, ("pedidoId", "fornecimentoId", "status"))

    def processar_pedido_atualizado(mensagem: dict, payload: dict, correlacao: str):
        pedido_id, fornecimento_id, status = payload["pedidoId"], payload["fornecimentoId"], payload["status"]
        reserva = repositorio.obter_reserva(pedido_id, fornecimento_id)
        momento = agora_utc(clock)
        if status == STATUS_CANCELADO and reserva is None:
            repositorio.salvar_reserva({
                "pedido_id": pedido_id, "fornecimento_id": fornecimento_id, "quantidade": ZERO,
                "situacao": "CANCELADA_SEM_RESERVA", "criado_em": instante(momento), "atualizado_em": instante(momento),
            })
            return []
        if reserva is None or reserva["situacao"] != "RESERVADA" or status not in (STATUS_CANCELADO, STATUS_VENDA_CONCLUIDA):
            return []
        quantidade = Decimal(str(reserva["quantidade"]))
        if status == STATUS_CANCELADO:
            delta_disponivel, nova_situacao, operacao = quantidade, "LIBERADA", "LIBERACAO"
        else:
            delta_disponivel, nova_situacao, operacao = ZERO, "BAIXADA", "BAIXA"
        atualizado = repositorio.aplicar_movimento(fornecimento_id, delta_disponivel, -quantidade, momento)
        if atualizado is None:
            raise RuntimeError(f"Reserva de {pedido_id} inconsistente com o saldo do fornecimento {fornecimento_id}.")
        repositorio.salvar_reserva({**reserva, "situacao": nova_situacao, "atualizado_em": instante(momento)})
        return [estoque_atualizado(atualizado, operacao, quantidade, pedido_id)]

    event_bus.subscribe("produto_cadastrado", ao_receber(processar_produto, validar_produto))
    event_bus.subscribe("produto_atualizado", ao_receber(processar_produto_atualizado, validar_produto))
    event_bus.subscribe("produto_excluido", ao_receber(processar_produto_excluido, validar_produto_excluido))
    event_bus.subscribe("pedido_criado", ao_receber(processar_pedido_criado, validar_pedido_criado))
    event_bus.subscribe("pedido_atualizado", ao_receber(processar_pedido_atualizado, validar_pedido_atualizado))

    return app
