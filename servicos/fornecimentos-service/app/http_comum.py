"""Infraestrutura HTTP comum aos serviços do grupo Fornecimento e Produtos.

Autenticação RS256 (§7.1 das ESPs), erros RFC 7807 (§10), correlation id,
métricas (API-03) e paginação (RN-06). Este arquivo é idêntico em
produtos-service e fornecimentos-service, porque cada pacote `app` só pode
importar a si mesmo e as dependências permitidas.
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException


class Clock(Protocol):
    def now(self) -> datetime: ...


class ChavesPublicas(Protocol):
    def obter(self, kid: str) -> object | None: ...


ESCOPOS = ("SUPPLIER", "BUYER", "CARRIER", "TENANT_ADMIN")
# Emissor e audiência dos tokens do Identity-Service (§7.1). Podem ser trocados em create_app.
EMISSOR_PADRAO = "identity-service"
AUDIENCIA_PADRAO = "b2b-platform"

TITULOS = {
    "TOKEN_AUSENTE": "Não Autenticado",
    "TOKEN_INVALIDO": "Token Inválido",
    "TOKEN_EXPIRADO": "Token Expirado",
    "PERFIL_NAO_PERMITIDO": "Acesso Negado",
    "CONTEXTO_NAO_SELECIONADO": "Contexto Não Selecionado",
    "PRODUTO_NAO_ENCONTRADO": "Produto Não Encontrado",
    "FORNECIMENTO_NAO_ENCONTRADO": "Fornecimento Não Encontrado",
    "ROTA_NAO_ENCONTRADA": "Rota Não Encontrada",
    "METODO_NAO_PERMITIDO": "Método Não Permitido",
    "DADOS_INVALIDOS": "Dados Inválidos",
    "PRODUTO_INEXISTENTE": "Produto Inexistente",
    "PAGINACAO_INVALIDA": "Paginação Inválida",
    "ERRO_INTERNO": "Erro Interno",
    "DEPENDENCIA_INDISPONIVEL": "Dependência Indisponível",
}

ROTAS_PUBLICAS = ("/health", "/health/ready", "/metrics", "/docs", "/openapi.json", "/docs/oauth2-redirect")

_INTEIRO = re.compile(r"^[0-9]+$")


class ErroApi(Exception):
    """Erro de negócio que vira uma resposta RFC 7807."""

    def __init__(self, status: int, codigo: str, detalhe: str):
        super().__init__(detalhe)
        self.status = status
        self.codigo = codigo
        self.detalhe = detalhe


def preenchido(valor: Any) -> bool:
    """Texto preenchido: string com pelo menos 1 caractere depois de strip()."""
    return isinstance(valor, str) and valor.strip() != ""


def agora_utc(clock: Clock) -> datetime:
    momento = clock.now()
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def instante(momento: datetime) -> str:
    """Instante ISO-8601 em UTC com sufixo Z e sem frações de segundo."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def correlation_id(request: Request) -> str:
    return request.state.correlation_id


def resposta_erro(request: Request, clock: Clock, status: int, codigo: str, detalhe: str) -> JSONResponse:
    corpo = {
        "type": "https://portal-b2b.corp/erros/" + codigo.lower().replace("_", "-"),
        "title": TITULOS[codigo],
        "status": status,
        "detail": detalhe,
        "instance": request.url.path,
        "codigo": codigo,
        "correlationId": correlation_id(request),
        "timestamp": instante(agora_utc(clock)),
    }
    return JSONResponse(corpo, status_code=status, media_type="application/problem+json")


def autenticar(request: Request, chaves: ChavesPublicas, clock: Clock,
               emissor: str = EMISSOR_PADRAO, audiencia: str = AUDIENCIA_PADRAO) -> dict:
    """Valida o token na ordem do §7.1 e devolve os claims."""
    cabecalho = request.headers.get("authorization")
    if cabecalho is None or not cabecalho.startswith("Bearer ") or not preenchido(cabecalho[7:]):
        raise ErroApi(401, "TOKEN_AUSENTE", "Cabeçalho Authorization Bearer ausente.")
    token = cabecalho[7:].strip()
    try:
        cabecalho_token = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError:
        raise ErroApi(401, "TOKEN_INVALIDO", "Token malformado.")
    kid = cabecalho_token.get("kid")
    if cabecalho_token.get("alg") != "RS256" or not preenchido(kid):
        raise ErroApi(401, "TOKEN_INVALIDO", "Token sem kid ou com algoritmo diferente de RS256.")
    try:
        chave = chaves.obter(kid)
    except Exception:
        # Serviço de chaves fora do ar: 503 (tentar de novo), não 401, para a tela não deslogar o usuário
        raise ErroApi(503, "DEPENDENCIA_INDISPONIVEL", "Não foi possível obter as chaves do serviço de Autenticação.")
    if chave is None:
        raise ErroApi(401, "TOKEN_INVALIDO", "Chave do token desconhecida.")
    try:
        claims = jwt.decode(
            token,
            chave,
            algorithms=["RS256"],
            issuer=emissor,
            audience=audiencia,
            options={"verify_exp": False, "verify_nbf": False, "verify_iat": False, "verify_aud": True, "verify_iss": True},
        )
    except jwt.InvalidTokenError:
        raise ErroApi(401, "TOKEN_INVALIDO", "Assinatura, emissor ou audiência do token inválidos.")
    exp = claims.get("exp")
    escopo = claims.get("active_scope")
    empresa = claims.get("tenant_id")
    if (
        not preenchido(claims.get("sub"))
        or (escopo is not None and escopo not in ESCOPOS)
        or (empresa is not None and not isinstance(empresa, str))
        or not isinstance(exp, int)
        or isinstance(exp, bool)
    ):
        raise ErroApi(401, "TOKEN_INVALIDO", "Claims do token ausentes ou inválidos.")
    if exp <= int(agora_utc(clock).timestamp()):
        raise ErroApi(401, "TOKEN_EXPIRADO", "O token está expirado.")
    if not preenchido(empresa) or escopo is None:
        # Token do login, antes da escolha de empresa e escopo (switch-context): válido, mas sem contexto
        raise ErroApi(403, "CONTEXTO_NAO_SELECIONADO", "Selecione a empresa e o escopo de atuação antes de usar o serviço.")
    return claims


def exigir_escopo(claims: dict, permitidos: tuple[str, ...]) -> None:
    if claims["active_scope"] not in permitidos:
        raise ErroApi(403, "PERFIL_NAO_PERMITIDO", f"O escopo {claims['active_scope']} não tem permissão para esta operação.")


def paginacao(request: Request) -> tuple[int, int]:
    """Lê page e size (RN-06) sem a validação automática do framework."""
    texto_page = request.query_params.get("page")
    texto_size = request.query_params.get("size")
    page, size = 1, 10
    if texto_page is not None:
        if not _INTEIRO.match(texto_page):
            raise ErroApi(422, "PAGINACAO_INVALIDA", "page deve ser inteiro maior ou igual a 1.")
        page = int(texto_page)
    if texto_size is not None:
        if not _INTEIRO.match(texto_size):
            raise ErroApi(422, "PAGINACAO_INVALIDA", "size deve ser inteiro de 1 a 100.")
        size = int(texto_size)
    if page < 1:
        raise ErroApi(422, "PAGINACAO_INVALIDA", "page deve ser inteiro maior ou igual a 1.")
    if size < 1 or size > 100:
        raise ErroApi(422, "PAGINACAO_INVALIDA", "size deve ser inteiro de 1 a 100.")
    return page, size


def filtro_texto(request: Request, nome: str) -> str | None:
    valor = request.query_params.get(nome)
    return valor.strip() if preenchido(valor) else None


async def corpo_json(request: Request) -> Any:
    """Lê o corpo bruto e devolve o JSON; JSON malformado vira DADOS_INVALIDOS."""

    def rejeitar_constante(nome: str) -> Any:
        raise ValueError(nome)

    bruto = await request.body()
    try:
        return json.loads(bruto, parse_constant=rejeitar_constante)
    except ValueError:
        raise ErroApi(422, "DADOS_INVALIDOS", "Corpo da requisição não é um JSON válido.")


def configurar_http(app: FastAPI, clock: Clock, nome_servico: str, dependencias_prontas: Callable[[], bool], logger) -> None:
    """Registra correlation id, métricas, tratamento de erros e endpoints técnicos."""
    contador: dict[int, int] = {}

    @app.middleware("http")
    async def contexto(request: Request, call_next):
        recebido = request.headers.get("x-correlation-id")
        request.state.correlation_id = recebido.strip() if preenchido(recebido) else str(uuid.uuid4())
        try:
            resposta = await call_next(request)
        except Exception:
            logger.exception("erro nao tratado", extra={"correlationId": request.state.correlation_id})
            resposta = resposta_erro(request, clock, 500, "ERRO_INTERNO", "Erro interno do serviço.")
        resposta.headers["X-Correlation-Id"] = request.state.correlation_id
        if request.url.path != "/metrics":
            contador[resposta.status_code] = contador.get(resposta.status_code, 0) + 1
        return resposta

    @app.exception_handler(ErroApi)
    async def tratar_erro_api(request: Request, erro: ErroApi):
        return resposta_erro(request, clock, erro.status, erro.codigo, erro.detalhe)

    @app.exception_handler(StarletteHTTPException)
    async def tratar_http(request: Request, erro: StarletteHTTPException):
        if erro.status_code == 405:
            return resposta_erro(request, clock, 405, "METODO_NAO_PERMITIDO", "Método não permitido para esta rota.")
        if erro.status_code == 404:
            return resposta_erro(request, clock, 404, "ROTA_NAO_ENCONTRADA", "Rota não encontrada.")
        return resposta_erro(request, clock, 500, "ERRO_INTERNO", "Erro interno do serviço.")

    @app.get("/health", include_in_schema=False)
    async def saude():
        return {"status": "UP", "service": nome_servico, "timestamp": instante(agora_utc(clock))}

    @app.get("/health/ready", include_in_schema=False)
    async def prontidao(request: Request):
        try:
            pronto = bool(dependencias_prontas())
        except Exception:
            pronto = False
        if not pronto:
            return resposta_erro(request, clock, 503, "DEPENDENCIA_INDISPONIVEL", "Banco ou barramento indisponível.")
        return {"status": "READY", "service": nome_servico, "timestamp": instante(agora_utc(clock))}

    @app.get("/metrics", include_in_schema=False)
    async def metricas():
        linhas = [
            "# HELP http_requests_total Total de requisicoes HTTP respondidas",
            "# TYPE http_requests_total counter",
        ]
        for status in sorted(contador):
            linhas.append(f'http_requests_total{{service="{nome_servico}",status="{status}"}} {contador[status]}')
        return PlainTextResponse("\n".join(linhas) + "\n", media_type="text/plain; version=0.0.4")


def envelope(evento: str, origem: str, chave: str, correlacao: str, clock: Clock, payload: dict) -> dict:
    """Envelope canônico do kit de infraestrutura (§7.4)."""
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": evento,
        "eventVersion": "1.0",
        "timestamp": instante(agora_utc(clock)),
        "source": origem,
        "correlationId": correlacao,
        "aggregateId": chave,
        "payload": payload,
    }


def criar_logger(nome: str):
    """Logger com saída JSON em stdout, uma linha por registro, sem dados do token."""
    import logging
    import sys

    class FormatoJson(logging.Formatter):
        def format(self, registro: logging.LogRecord) -> str:
            dados = {
                "timestamp": datetime.fromtimestamp(registro.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "level": registro.levelname,
                "service": nome,
                "message": registro.getMessage(),
            }
            correlacao = getattr(registro, "correlationId", None)
            if correlacao:
                dados["correlationId"] = correlacao
            if registro.exc_info:
                dados["exception"] = self.formatException(registro.exc_info)
            return json.dumps(dados, ensure_ascii=False)

    logger = logging.getLogger(nome)
    if not logger.handlers:
        saida = logging.StreamHandler(sys.stdout)
        saida.setFormatter(FormatoJson())
        logger.addHandler(saida)
        logger.setLevel(logging.INFO)
        logger.propagate = True
    return logger


__all__ = [
    "AUDIENCIA_PADRAO", "ChavesPublicas", "Clock", "EMISSOR_PADRAO", "ErroApi", "ESCOPOS", "ROTAS_PUBLICAS", "Response", "agora_utc", "autenticar",
    "configurar_http", "corpo_json", "correlation_id", "criar_logger", "envelope", "exigir_escopo",
    "filtro_texto", "instante", "paginacao", "preenchido", "resposta_erro",
]
