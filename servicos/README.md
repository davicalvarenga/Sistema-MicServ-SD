# Serviços do grupo Fornecimento e Produtos

| Serviço | Porta | Especificação | Testes |
|---|---|---|---|
| [`produtos-service`](produtos-service/) | 8102 | [ESP-PRD-001](../docs/especificacoes/ESP-PRD-001_Produtos.md) | CA-01 a CA-27 |
| [`fornecimentos-service`](fornecimentos-service/) | 8103 | [ESP-FRN-001](../docs/especificacoes/ESP-FRN-001_Fornecimentos.md) | CA-01 a CA-47 |

Os dois seguem a arquitetura de portas das ESPs: o pacote `app` contém o domínio e a API e só conhece interfaces (`EventBus`, `Clock`, repositório e `ChavesPublicas`). As implementações reais ficam em `adaptadores/` e são montadas em `servidor.py`.

```
<servico>/
├── app/                  domínio e API (create_app)
├── adaptadores/          PostgreSQL, Kafka, JWKS e relógio
├── servidor.py           ponto de entrada de produção
├── tests/
│   ├── test_conformidade.py   um teste por critério de aceitação
│   └── test_postgres.py       integração com PostgreSQL
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
```

## Rodar os testes

Requer Python 3.12.

```bash
cd servicos/fornecimentos-service      # ou produtos-service
pip install -r requirements-dev.txt
python -m pytest
```

Sem banco configurado, os testes de integração são pulados. Para incluí-los, informe um PostgreSQL 16 com usuário administrador e o script do banco do kit de infraestrutura:

```bash
export PG_ADMIN_DSN="host=localhost port=5432 dbname=postgres user=postgres"
export KIT_INIT_SQL=/caminho/para/portal-b2b-kit-infra/database/01-init.sql
python -m pytest
```

Os testes criam um banco temporário, aplicam o script do kit e a [proposta de DDL](../docs/banco/), conectam como `svc_produtos` ou `svc_fornecimentos` e apagam o banco no fim. O GitHub roda tudo isso automaticamente (`.github/workflows/testes.yml`).

## Rodar no ambiente do kit

1. Suba a infraestrutura do [kit](https://github.com/Printf-PedroCardoso/portal-b2b-kit-infra) (`make env` e `make infra-up`).
2. Aplique a proposta de DDL no banco `portal_b2b` (até o grupo de Banco de Dados incorporá-la ao kit).
3. Construa a imagem na pasta do serviço (`docker build -t fornecimentos-service .`) e rode na rede do kit com as variáveis abaixo.

| Variável | Padrão | Uso |
|---|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME` | `pg-primary`, `5432`, `portal_b2b` | PostgreSQL |
| `DB_USER` | `svc_produtos` / `svc_fornecimentos` | Usuário com DML só no próprio schema |
| `DB_PASSWORD` | obrigatória | Senha do usuário do banco |
| `DB_POOL_MAX` | `5` | Conexões por instância |
| `KAFKA_BOOTSTRAP_SERVERS` | `rp-0:9092` | Redpanda |
| `AUTH_JWKS_URL` | `http://gateway:8080/.well-known/jwks.json` | Chaves públicas do serviço de Autenticação |
| `PORT` | `8102` / `8103` | Porta HTTP |

## Situação

- Testes de conformidade e de integração com PostgreSQL aprovados.
- Os serviços rodam dentro do kit de infraestrutura, com duas instâncias de cada um: passo a passo, teste de fumaça e problemas encontrados no kit em [`integracao-kit/`](integracao-kit/README.md).
- Os eventos passam pela tabela `outbox` do schema antes do Kafka (`adaptadores/outbox.py`, ADR-010): com o Redpanda fora, eles esperam na tabela e saem quando ele voltar.
- Novas tentativas antes da DLT não foram implementadas. Detalhes nas seções 13 e 14 do [Relatório Técnico](../docs/relatorio-tecnico.md).
