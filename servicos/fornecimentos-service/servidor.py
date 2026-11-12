"""Ponto de entrada de produção do fornecimentos-service: monta os adaptadores e sobe o uvicorn."""

import logging
import os

import uvicorn

from adaptadores.chaves_jwks import ChavesJwks
from adaptadores.kafka import BarramentoKafka
from adaptadores.outbox import BarramentoOutbox
from adaptadores.postgres import RepositorioFornecimentosPostgres
from adaptadores.relogio import RelogioSistema
from app.http_comum import AUDIENCIA_PADRAO, EMISSOR_PADRAO
from app.main import NOME_SERVICO, create_app


def dsn() -> str:
    return (f"host={os.environ.get('DB_HOST', 'pg-primary')} port={os.environ.get('DB_PORT', '5432')} "
            f"dbname={os.environ.get('DB_NAME', 'portal_b2b')} user={os.environ.get('DB_USER', 'svc_fornecimentos')} "
            f"password={os.environ['DB_PASSWORD']} connect_timeout=3")


def main() -> None:
    kafka = BarramentoKafka(os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "rp-0:9092"), NOME_SERVICO)
    repositorio = RepositorioFornecimentosPostgres(dsn(), int(os.environ.get("DB_POOL_MAX", "5")))
    # Os eventos passam pela tabela fornecimentos.outbox antes do Kafka (ADR-010)
    barramento = BarramentoOutbox(repositorio.pool, "fornecimentos", kafka)
    app = create_app(
        barramento,
        RelogioSistema(),
        repositorio,
        ChavesJwks(os.environ.get("AUTH_JWKS_URL", "http://gateway:8080/.well-known/jwks.json")),
        emissor=os.environ.get("JWT_ISSUER", EMISSOR_PADRAO),
        audiencia=os.environ.get("JWT_AUDIENCE", AUDIENCIA_PADRAO),
    )
    # Os adaptadores (Kafka, outbox) usam o mesmo formato JSON de log do serviço
    logs_adaptadores = logging.getLogger("adaptadores")
    logs_adaptadores.handlers = list(logging.getLogger(NOME_SERVICO).handlers)
    logs_adaptadores.setLevel(logging.INFO)
    logs_adaptadores.propagate = False
    kafka.iniciar()
    barramento.iniciar()
    try:
        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8103")), log_level="info")
    finally:
        barramento.parar()
        kafka.parar()


if __name__ == "__main__":
    main()
