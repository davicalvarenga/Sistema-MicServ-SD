"""Ponto de entrada de produção do produtos-service: monta os adaptadores e sobe o uvicorn."""

import os

import uvicorn

from adaptadores.chaves_jwks import ChavesJwks
from adaptadores.kafka import BarramentoKafka
from adaptadores.outbox import BarramentoOutbox
from adaptadores.postgres import RepositorioProdutosPostgres
from adaptadores.relogio import RelogioSistema
from app.main import NOME_SERVICO, create_app


def dsn() -> str:
    return (f"host={os.environ.get('DB_HOST', 'pg-primary')} port={os.environ.get('DB_PORT', '5432')} "
            f"dbname={os.environ.get('DB_NAME', 'portal_b2b')} user={os.environ.get('DB_USER', 'svc_produtos')} "
            f"password={os.environ['DB_PASSWORD']} connect_timeout=3")


def main() -> None:
    kafka = BarramentoKafka(os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "rp-0:9092"), NOME_SERVICO)
    repositorio = RepositorioProdutosPostgres(dsn(), int(os.environ.get("DB_POOL_MAX", "5")))
    # Os eventos passam pela tabela produtos.outbox antes do Kafka (ADR-010)
    barramento = BarramentoOutbox(repositorio.pool, "produtos", kafka)
    app = create_app(
        barramento,
        RelogioSistema(),
        repositorio,
        ChavesJwks(os.environ.get("AUTH_JWKS_URL", "http://gateway:8080/.well-known/jwks.json")),
    )
    kafka.iniciar()
    barramento.iniciar()
    try:
        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8102")), log_level="info")
    finally:
        barramento.parar()
        kafka.parar()


if __name__ == "__main__":
    main()
