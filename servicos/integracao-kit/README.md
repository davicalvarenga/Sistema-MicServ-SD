# Integração com o kit de infraestrutura

Como rodar o `produtos-service` e o `fornecimentos-service` dentro do kit de infraestrutura da turma ([`Printf-PedroCardoso/portal-b2b-kit-infra`](https://github.com/Printf-PedroCardoso/portal-b2b-kit-infra), commit `90085b3`; o passo a passo foi executado no `b23af3b`), com duas instâncias de cada serviço, o PostgreSQL e o Redpanda do kit.

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
# Enquanto o serviço de Autenticação não estiver no lugar do usuarios-service do kit, use o servidor de teste do passo 4
AUTH_JWKS_URL=http://jwks-teste:8000/.well-known/jwks.json
EOF
```

**2. Atalho para os arquivos do compose.** Sem o contorno de teste local, o banco do kit não sobe (K12). Quando a Infraestrutura corrigir o kit, retire o terceiro arquivo.

```bash
F="-f docker-compose.yml -f ../Sistema-MicServ-SD/servicos/integracao-kit/docker-compose.override.yml -f ../Sistema-MicServ-SD/servicos/integracao-kit/docker-compose.teste-local.yml"
```

**3. Banco, Redpanda e tópicos.** O banco aplica o `01-init.sql` do kit e, depois, a nossa proposta de DDL. O script de tópicos do kit só funciona com os três brokers no ar (K15), por isso o `until` espera o `rp-2` aparecer. Mesmo assim, em 23/11/2026 os dois primeiros tópicos da lista (`empresa_cadastrada` e `produto_cadastrado`) não foram criados na primeira execução; por isso o script roda duas vezes, e a segunda cria o que faltou. Os tópicos `reserva_estoque_recusada`, `produto_atualizado`, `produto_excluido` e `fornecimento_atualizado` ainda não estão no script do kit (K14) e precisam ser criados à parte.

```bash
docker compose $F up -d pg-primary rp-0 rp-1 rp-2
until docker exec portal-b2b-rp-0 rpk cluster info --brokers rp-0:9092 -b 2>/dev/null | grep -q rp-2; do sleep 2; done
bash scripts/init_topics.sh
bash scripts/init_topics.sh
for t in reserva_estoque_recusada produto_atualizado produto_excluido fornecimento_atualizado; do docker exec portal-b2b-rp-0 rpk topic create $t --brokers rp-0:9092 -p 3 -r 3 --topic-config retention.ms=604800000; done
docker exec portal-b2b-rp-0 rpk topic list --brokers rp-0:9092
```

Resultado esperado no commit `90085b3`: 31 tópicos (22 de negócio, contando os 3 do serviço de Autenticação, e 9 DLTs); no `b23af3b`, eram 28, os de negócio com 3 partições e 3 réplicas. Se ainda faltar algum, rode o `init_topics.sh` de novo; ele ignora os tópicos que já existem.

**4. Servidor de chaves de teste.** O gateway do kit tem a rota `/.well-known/jwks.json` desde o commit `90085b3`, mas ela leva ao `usuarios-service` do kit, que ainda é o modelo da Infraestrutura e não publica chaves. Enquanto o serviço de Autenticação não ocupar esse lugar, um servidor JWKS de teste faz esse papel. As chaves ficam na pasta `teste-chaves`, dentro do kit. A pasta não deve ir para nenhum repositório.

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

Resultado esperado: 18 linhas `OK` e `RESULTADO: TUDO OK`. O teste:

- confere a prontidão das quatro instâncias;
- recusa um token HS256 e um token do login ainda sem empresa (403);
- cadastra um produto numa instância e o consulta na outra;
- confere que o token de visão de grupo econômico consulta (200), mas não cadastra (403 `CONTEXTO_DE_GRUPO_NAO_PERMITIDO`);
- espera o `produto_cadastrado` chegar ao Fornecimentos pelo Redpanda e cadastra um fornecimento;
- espera o `fornecimento_criado` chegar ao Produtos e confere que a alteração do produto passa a ser recusada (409);
- publica `pedido_criado` e `pedido_atualizado` (cancelamento) e confere a reserva e a liberação do estoque;
- repõe a oferta e muda o preço (`PATCH`);
- lê no Redpanda os eventos publicados, inclusive o `grupoId` do `fornecimento_criado`.

Se a verificação "produto chegou ao fornecimentos" falhar, confira se o tópico `produto_cadastrado` existe com 3 partições e se o grupo consumidor recebeu partições dele:

```bash
docker exec portal-b2b-rp-0 rpk group describe fornecimentos-service --brokers rp-0:9092
```

O esperado é `STATE Stable`, `MEMBERS 2` e linhas de `produto_cadastrado` na tabela. Em 16/11/2026, essa verificação falhou porque o `init_topics.sh` rodou antes de os três brokers estarem prontos e não criou o `produto_cadastrado` (K15). O tópico acabou criado sozinho na primeira publicação, com 1 partição, e o consumidor só o enxerga quando renova os metadados, o que leva até 5 minutos no padrão da biblioteca. É a causa provável da falha de 12/11/2026 registrada na issue #24, mas não temos o log daquela rodada para confirmar.

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
| K12 | O `pg-primary` sobe com `synchronous_commit=on` e `synchronous_standby_names='pg_replica'`. Durante a inicialização, o PostgreSQL só escuta o socket local, a réplica não consegue se conectar e o `CREATE DATABASE "portal_b2b"` fica esperando por ela para sempre (`wait_event` `SyncRep`) | O banco `portal_b2b` nunca é criado, e nenhum serviço do kit consegue usar o banco. **Continua no commit `b23af3b` (22/11/2026):** o valor passou a `FIRST 1 (walreceiver)` e a réplica agora espera o primário com `pg_isready`, mas o primário segue exigindo réplica síncrona durante a inicialização; em 22/11/2026, o `CREATE DATABASE` ficou em `SyncRep` e a réplica em "no response" | Tirar `synchronous_standby_names` do comando do primário, ou configurá-lo só depois da inicialização. Vale conferir também se a réplica se identifica como `pg_replica`, porque o primário espera esse nome. Não verificamos a réplica: no nosso teste, ela não conseguiu resolver o nome `pg-primary` enquanto o primário ainda estava iniciando |
| K13 | O gateway não tem a rota `/.well-known/jwks.json` | Nenhum serviço consegue validar os tokens RS256 do serviço de Autenticação | **Resolvido no commit `90085b3` (23/11/2026)**, pela issue #2 do repositório do kit. A rota leva ao `usuarios-service` do kit, que ainda não publica chaves; falta o serviço de Autenticação ocupar esse lugar |
| K14 | Os tópicos `reserva_estoque_recusada` e, desde a versão 2.0 do contrato, `produto_atualizado`, `produto_excluido` e `fornecimento_atualizado` não estão no `scripts/init_topics.sh` | O Redpanda do kit roda em modo `dev-container`, que cria o tópico sozinho na primeira publicação, mas com 1 partição (`default_topic_partitions`), fora do padrão de 3 partições e replicação 3 do kit | Incluir os tópicos no script (pedido na issue #12). Até lá, criar à mão, como no passo 3 |
| K15 | O `scripts/init_topics.sh` usa `|| true` em cada `rpk topic create` e imprime "criados com sucesso" mesmo quando a criação falha. Rodado logo depois de subir o Redpanda, com menos de três brokers no ar, a criação com 3 réplicas falha nos primeiros tópicos da lista (em 16/11/2026, `empresa_cadastrada` e `produto_cadastrado`) | O tópico fica faltando, ou é criado sozinho na primeira publicação com 1 partição e 1 réplica. Em 23/11/2026, aconteceu mesmo depois de o `rp-2` aparecer no `rpk cluster info`. Um consumidor que já estava inscrito demora até 5 minutos para enxergá-lo | Esperar os três brokers antes de criar os tópicos (por exemplo, `rpk cluster info -b`) e terminar com erro quando um `rpk topic create` falhar por outro motivo que não "já existe" |

## O que foi verificado

Em 11/11/2026, com Docker 29 e as imagens do kit (`postgres:16.3-alpine` e `redpanda:v24.1.8`):

- As imagens dos dois serviços foram construídas com os nossos Dockerfiles, sem alteração.
- O banco foi criado com o script do kit e a nossa DDL. Os quatro contêineres ficaram saudáveis.
- O teste de fumaça passou nas 13 verificações da época. Em 12/11/2026, com a validação de token da versão 1.4 das ESPs, passou nas 14 verificações atuais em três de quatro rodadas (veja o passo 6).
- Com o servidor de chaves parado, uma instância sem a chave em cache respondeu 503 `DEPENDENCIA_INDISPONIVEL`, e uma instância com a chave em cache continuou respondendo 200. Quando o servidor de chaves voltou, a primeira instância voltou a responder 200 sem reiniciar.
- No teste de queda do Redpanda, o cadastro respondeu 201 e a prontidão respondeu 503. O evento ficou no outbox e foi publicado de 6 a 25 segundos depois que o Redpanda voltou. O consumidor do Fornecimentos se reconectou sozinho e processou o evento.
- Os logs dos dois serviços saem em JSON, inclusive os da biblioteca do Kafka. A exceção é o log de acesso do uvicorn.
- Em 16/11/2026, com a versão 2.0 dos serviços e do contrato, o teste de fumaça passou nas 17 verificações em duas rodadas seguidas, seguindo este passo a passo do zero numa pasta nova. A primeira tentativa, ainda com `sleep 20` no passo 3, falhou na chegada ao Fornecimentos pelo K15.
- Em 19/11/2026, com a versão 2.1, o teste passou nas 18 verificações em duas rodadas seguidas, seguindo este passo a passo do zero numa pasta nova.
- Em 24/11/2026, o commit `90085b3` foi conferido só pela leitura das mudanças (rotas do serviço de Autenticação e do JWKS no gateway, Redis e três tópicos novos); o passo a passo não foi executado de novo. O K12, o K14 e o K15 não foram tocados por esse commit.
- Em 22 e 23/11/2026, com o kit no commit `b23af3b`:
  - sem o contorno de teste local, o banco continua sem subir (K12);
  - com o contorno, as novas permissões do kit (`SELECT`, `INSERT`, `UPDATE` e `DELETE` nas tabelas, e privilégios padrão para tabelas criadas pelo `portal_ddl`) deram ao `svc_produtos` e ao `svc_fornecimentos` exatamente essas quatro permissões em todas as tabelas da nossa DDL, como na nossa proposta;
  - o teste de fumaça passou nas 18 verificações em quatro rodadas seguidas, seguindo este passo a passo do zero numa pasta nova.
