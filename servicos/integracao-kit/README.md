# Integração com o kit de infraestrutura

Como rodar o `produtos-service` e o `fornecimentos-service` dentro do kit de infraestrutura da turma ([`Printf-PedroCardoso/portal-b2b-kit-infra`](https://github.com/Printf-PedroCardoso/portal-b2b-kit-infra), commit `630515c`), com duas instâncias de cada serviço, o PostgreSQL e o Redpanda do kit.

| Arquivo | Para que serve |
|---|---|
| [`docker-compose.override.yml`](docker-compose.override.yml) | Troca o build dos contêineres `app1-produtos`, `app2-produtos`, `app1-fornecimentos` e `app2-fornecimentos` do kit pelos nossos serviços, passa as variáveis de que eles precisam e aplica a [proposta de DDL](../../docs/banco/README.md) na primeira inicialização do banco. Não altera nenhum arquivo do kit |
| [`docker-compose.teste-local.yml`](docker-compose.teste-local.yml) | Contorno **opcional e só para teste local** do defeito K12 do kit (seção "Problemas encontrados no kit") |
| [`teste_fumaca.py`](teste_fumaca.py) | Teste de ponta a ponta: HTTP nas quatro instâncias, Redpanda, PostgreSQL e token RS256 validado por JWKS |

## Pré-requisitos

- Docker com Docker Compose v2.
- **Terminal:** Git Bash ou WSL no Windows, ou o terminal do Linux/macOS. O kit usa `make` e scripts bash, e os comandos abaixo seguem a mesma sintaxe. Não use PowerShell nem CMD para eles.
- O kit e este repositório clonados lado a lado, na mesma pasta:

```text
pasta-de-trabalho/
├── portal-b2b-kit-infra/   (kit da Infraestrutura)
└── Sistema-MicServ-SD/     (este repositório)
```

Todos os comandos abaixo rodam **dentro da pasta do kit**. Se este repositório estiver em outro lugar, defina `REPO_FORNECIMENTO_PRODUTOS` no `.env` do kit com o caminho dele.

## Passo a passo

**1. Variáveis no `.env` do kit.** O `make env` copia o `.env.example`. Em seguida, acrescente as nossas variáveis. As senhas são as de desenvolvimento que o próprio kit define no `database/01-init.sql`. Não as use fora da máquina local.

```bash
make env
cat >> .env <<'EOF'

# Grupo de Fornecimento e Produtos
SVC_PRODUTOS_DB_PASSWORD='SvcProdutosPass2026!#'
SVC_FORNECIMENTOS_DB_PASSWORD='SvcFornecimentosPass2026!#'
# Enquanto o gateway não tiver a rota /.well-known/jwks.json, use o servidor de teste do passo 4
AUTH_JWKS_URL=http://jwks-teste:8000/.well-known/jwks.json
EOF
```

**2. Atalho para os arquivos do compose.** Sem o contorno de teste local, o banco do kit não sobe (K12). Quando a Infraestrutura corrigir o kit, retire o terceiro arquivo.

```bash
F="-f docker-compose.yml -f ../Sistema-MicServ-SD/servicos/integracao-kit/docker-compose.override.yml -f ../Sistema-MicServ-SD/servicos/integracao-kit/docker-compose.teste-local.yml"
```

**3. Banco, Redpanda e tópicos.** O banco aplica o `01-init.sql` do kit e, depois, a nossa proposta de DDL. O tópico `reserva_estoque_recusada` ainda não está no script do kit e precisa ser criado à parte.

```bash
docker compose $F up -d pg-primary rp-0 rp-1 rp-2
sleep 20
bash scripts/init_topics.sh
docker exec portal-b2b-rp-0 rpk topic create reserva_estoque_recusada --brokers rp-0:9092 -p 3 -r 3 --topic-config retention.ms=604800000
```

**4. Servidor de chaves de teste.** Enquanto o serviço de Autenticação não estiver no gateway, um servidor JWKS de teste faz esse papel. As chaves ficam na pasta `teste-chaves`, dentro do kit. A pasta não deve ir para nenhum repositório.

```bash
docker compose $F build app1-produtos app2-produtos app1-fornecimentos app2-fornecimentos
docker compose $F run --rm --no-deps --user root -v "$PWD/teste-chaves:/t" -v "$PWD/../Sistema-MicServ-SD/servicos/integracao-kit:/script:ro" app1-produtos python /script/teste_fumaca.py gerar-chaves /t
docker run -d --name jwks-teste --network portal-net -v "$PWD/teste-chaves/.well-known:/srv/.well-known:ro" -w /srv python:3.12-slim python -m http.server 8000
```

**5. Nossos serviços.**

```bash
docker compose $F up -d --no-deps app1-produtos app2-produtos app1-fornecimentos app2-fornecimentos
sleep 20
docker compose $F ps
```

Resultado esperado: os quatro contêineres `Up` e `(healthy)`. Se algum ficar `unhealthy`, veja o motivo com `docker logs app1-produtos` (os logs são JSON, uma linha por registro).

**6. Teste de fumaça.**

```bash
docker compose $F run --rm --no-deps -v "$PWD/teste-chaves:/t:ro" -v "$PWD/../Sistema-MicServ-SD/servicos/integracao-kit:/script:ro" app1-produtos python /script/teste_fumaca.py executar
```

Resultado esperado: 13 linhas `OK` e `RESULTADO: TUDO OK`. O teste:

- confere a prontidão das quatro instâncias;
- recusa um token HS256;
- cadastra um produto numa instância e o consulta na outra;
- espera o `produto_cadastrado` chegar ao Fornecimentos pelo Redpanda e cadastra um fornecimento;
- publica `pedido_criado` e `pedido_atualizado` (cancelamento) e confere a reserva e a liberação do estoque;
- lê no Redpanda os eventos publicados.

**7. Outbox com o Redpanda fora (opcional).** Com o Redpanda parado, o cadastro continua respondendo 201 e o evento espera na tabela `produtos.outbox`. Quando o Redpanda volta, o evento é publicado sozinho.

```bash
docker stop portal-b2b-rp-0 portal-b2b-rp-1 portal-b2b-rp-2
docker compose $F run --rm --no-deps -v "$PWD/teste-chaves:/t:ro" -v "$PWD/../Sistema-MicServ-SD/servicos/integracao-kit:/script:ro" app1-produtos python /script/teste_fumaca.py executar
docker exec portal-b2b-pg-primary psql -U portal_admin -d portal_b2b -c "SELECT topico, chave, publicado_em FROM produtos.outbox WHERE publicado_em IS NULL"
docker start portal-b2b-rp-0 portal-b2b-rp-1 portal-b2b-rp-2
```

Com o Redpanda parado, o teste de fumaça falha na prontidão e na chegada ao Fornecimentos, mas o cadastro do produto responde 201, e a consulta mostra o evento pendente. Alguns segundos depois do `docker start` (entre 6 e 25 segundos nos nossos testes), a mesma consulta volta vazia.

**8. Encerrar.** O `-v` apaga os volumes, e o banco começa do zero na próxima subida.

```bash
docker compose $F down -v
docker rm -f jwks-teste
```

## Problemas encontrados no kit

Encontrados ao rodar o kit em 11/11/2026, além dos pontos K1 a K11 da seção 3.4 do [Relatório Técnico](../../docs/relatorio-tecnico.md):

| # | Problema | Efeito | Correção sugerida à Infraestrutura |
|---|---|---|---|
| K12 | O `pg-primary` sobe com `synchronous_commit=on` e `synchronous_standby_names='pg_replica'`. Durante a inicialização, o PostgreSQL só escuta o socket local, a réplica não consegue se conectar e o `CREATE DATABASE "portal_b2b"` fica esperando por ela para sempre (`wait_event` `SyncRep`) | O banco `portal_b2b` nunca é criado, e nenhum serviço do kit consegue usar o banco | Tirar `synchronous_standby_names` do comando do primário, ou configurá-lo só depois da inicialização. Vale conferir também se a réplica se identifica como `pg_replica`, porque o primário espera esse nome. Não verificamos a réplica: no nosso teste, ela não conseguiu resolver o nome `pg-primary` enquanto o primário ainda estava iniciando |
| K13 | O gateway não tem a rota `/.well-known/jwks.json` | Nenhum serviço consegue validar os tokens RS256 do serviço de Autenticação | Rota pedida pela Autenticação à Infraestrutura (issue #2 deste repositório) |
| K14 | O tópico `reserva_estoque_recusada` não está no `scripts/init_topics.sh` | O Redpanda do kit roda em modo `dev-container`, que cria o tópico sozinho na primeira publicação, mas com 1 partição (`default_topic_partitions`), fora do padrão de 3 partições e replicação 3 do kit | Incluir o tópico no script (pedido na issue #12). Até lá, criar à mão, como no passo 3 |

## O que foi verificado

Em 11/11/2026, com Docker 29 e as imagens do kit (`postgres:16.3-alpine` e `redpanda:v24.1.8`):

- As imagens dos dois serviços foram construídas com os nossos Dockerfiles, sem alteração.
- O banco foi criado com o script do kit e a nossa DDL. Os quatro contêineres ficaram saudáveis.
- O teste de fumaça passou nas 13 verificações.
- No teste de queda do Redpanda, o cadastro respondeu 201 e a prontidão respondeu 503. O evento ficou no outbox e foi publicado de 6 a 25 segundos depois que o Redpanda voltou. O consumidor do Fornecimentos se reconectou sozinho e processou o evento.
- Os logs dos dois serviços saem em JSON, inclusive os da biblioteca do Kafka. A exceção é o log de acesso do uvicorn.
