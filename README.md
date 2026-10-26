# Fornecimento e Produtos | Portal B2B Distribuído

Microsserviços de **Produtos** e **Fornecimentos** do Portal B2B Distribuído, trabalho da disciplina de Sistemas Distribuídos. O portal é dividido entre vários grupos da turma, e os módulos se comunicam por eventos no Redpanda, compatível com a API do Apache Kafka.

## Integrantes

- Daniel Carvalho Coutinho
- Davi Coelho de Alvarenga
- Gabriel Vicentte dos Santos Ferreira
- Rafael de Castro Noleto

## Responsabilidades do grupo

| Serviço | Porta local | Schema no banco | O que faz |
|---|---|---|---|
| `produtos-service` | 8102 | `produtos` | Cadastro de produtos, categoria, unidade e tipo de transporte |
| `fornecimentos-service` | 8103 | `fornecimentos` | Relação de fornecimento entre fornecedor e produto, preço, quantidade, origem e controle de estoque |

O controle de estoque separa a **quantidade disponível** da **quantidade reservada**. Quando um pedido é criado, a quantidade é reservada. Se o pedido for cancelado, ela volta a ficar disponível. Se a venda for concluída, ela sai do estoque.

O grupo se integra por eventos com os serviços de outros grupos da turma:

| Grupo | Serviços | Integração com o nosso grupo |
|---|---|---|
| Autenticação (Equipe A) | `usuarios-service` | Token JWT validado em cada requisição e evento `empresa_cadastrada` |
| Compra e Demanda | `demanda-service` | Consome `produto_cadastrado` |
| Mercado, Negociação/Leilão e Pedidos | `mercado-service`, `negociacao-service`, `pedidos-service` | Mercado consome os nossos eventos. Pedidos publica os eventos que reservam e liberam estoque |
| Logística/Transporte | `logistica-service`, `transportadoras-service` | Usa o tipo de transporte do produto |
| Banco de Dados | PostgreSQL 16 | Cria as tabelas dos schemas `produtos` e `fornecimentos` |
| Infraestrutura | Gateway, Redpanda, observabilidade | Mantém o [kit de integração](https://github.com/Printf-PedroCardoso/portal-b2b-kit-infra) usado como base |
| UX/UI | Front-ends | Faz a tela `/app/produtos`, que consome a nossa API |
| Teste | Suíte de testes | Testa os nossos serviços com base no Documento de Requisitos |

## Eventos

| Tópico | Chave | Papel do grupo |
|---|---|---|
| `produto_cadastrado` | `produtoId` | Publica (Produtos) e consome (Fornecimentos) |
| `fornecimento_criado` | `fornecimentoId` | Publica |
| `estoque_atualizado` | `fornecimentoId` | Publica |
| `pedido_criado`, `pedido_atualizado` | `pedidoId` | Consome, para reservar, liberar ou dar baixa no estoque |
| `empresa_cadastrada` | `empresaId` | Consome |
| `produtos.dlt`, `fornecimentos.dlt` | a do evento original | Publica as mensagens que falharam após 3 tentativas |

Os tópicos e o envelope dos eventos seguem o catálogo do kit de integração. O conteúdo de cada evento está no [Contrato de Eventos](docs/contrato-eventos.md). Os eventos de alteração e exclusão de produto ainda não têm tópico no kit (pendência P-26 do Documento de Requisitos).

## Documentação

| Documento | Conteúdo |
|---|---|
| [Documento de Requisitos](docs/documento-de-requisitos.md) | Requisitos funcionais e não funcionais, regras de negócio, casos de uso e critérios de aceitação. Referência do Grupo de Teste (QA). Versão 0.4 |
| [Relatório Técnico](docs/relatorio-tecnico.md) | Arquitetura, implementação, análise do kit de infraestrutura e registro de cada decisão técnica com a sua justificativa. Versão 0.3 |
| [Contrato de Eventos](docs/contrato-eventos.md) | Conteúdo de cada evento publicado e consumido, com [JSON Schemas](docs/contratos/schemas/) e [exemplos](docs/contratos/exemplos/) |
| [Proposta de DDL](docs/banco/README.md) | Ajustes nos schemas `produtos` e `fornecimentos` para o grupo de Banco de Dados, com o resultado dos testes |
| [Análise de Requisitos (SWEBOK)](docs/analise-requisitos/Analise-de-Requisitos-SWEBOK.pdf) | Análise do Documento de Requisitos v0.3 organizada pelas subáreas de *Software Requirements* do SWEBOK V3.0. Fonte em [HTML](docs/analise-requisitos/analise-requisitos.html) |

## Situação atual

O projeto está na fase de requisitos e arquitetura. Ainda não há código dos serviços. A base de implementação será o kit de integração do grupo de Infraestrutura, com as correções descritas na seção 3.4 do Relatório Técnico.

As decisões em aberto estão nas [issues](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues):

| Issue | Assunto |
|---|---|
| [#1](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/1) | Integração com Pedidos |
| [#2](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/2) | Integração com autenticação |
| [#3](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/3) | Contrato de eventos Kafka |
| [#4](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/4) | Modelo de dados do produto |
| [#5](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/5) | Modelo de dados do fornecimento |
| [#6](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/6) | Permissões sobre produtos e regra de exclusão |
| [#7](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/7) | Pedido de fornecimento entre fornecedor e grupo |
| [#8](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/8) | Infra e banco de dados |
| [#9](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/9) | Telas do módulo |
| [#10](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/10) | Decisões internas do grupo |
| [#12](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/12) | Correções e ajustes a pedir ao grupo de Infraestrutura |
| [#13](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/13) | Conflitos entre o professor e o kit de infraestrutura |

## Tecnologias

| Item | Escolha | Situação |
|---|---|---|
| Mensageria | Redpanda, compatível com a API do Kafka (3 brokers) | Definido pelo kit |
| Banco de dados | PostgreSQL 16, banco `portal_b2b`, um schema por serviço | Definido pelo kit |
| Contêineres | Docker | Exigido pelo professor |
| Gateway | Nginx na porta 8080 | Definido pelo kit |
| Linguagem e framework | Python 3.12 com FastAPI | Proposta do grupo ([issue #10](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/10)) |

## Como executar

O ambiente local vem do [kit de integração](https://github.com/Printf-PedroCardoso/portal-b2b-kit-infra). É preciso ter Docker e Docker Compose instalados.

```bash
git clone https://github.com/Printf-PedroCardoso/portal-b2b-kit-infra
cd portal-b2b-kit-infra
make env        # copia .env.example para .env
make infra-up   # sobe PostgreSQL, Redpanda, gateway, PgAdmin e Kafka UI
```

| Ferramenta | Endereço |
|---|---|
| Gateway (APIs e front-ends) | http://localhost:8080 |
| PgAdmin | http://localhost:5050 |
| Kafka UI | http://localhost:8090 |
| Redpanda (clientes Kafka) | localhost:19092 |
| PostgreSQL | localhost:5432 |

As instruções para rodar os nossos serviços serão adicionadas quando o primeiro serviço estiver implementado. Antes disso, veja a seção 3.4 do [Relatório Técnico](docs/relatorio-tecnico.md): o script do banco do kit não dá aos serviços permissão nas próprias tabelas, e a correção está descrita lá.

## Estrutura do repositório

```
.
├── README.md
├── docs/
│   ├── documento-de-requisitos.md
│   ├── relatorio-tecnico.md
│   ├── contrato-eventos.md
│   ├── contratos/
│   │   ├── schemas/
│   │   └── exemplos/
│   ├── banco/
│   │   ├── README.md
│   │   └── 01-proposta-ddl-produtos-fornecimentos.sql
│   ├── AGENTE-VALIDACAO.md
│   └── analise-requisitos/
│       ├── Analise-de-Requisitos-SWEBOK.pdf
│       └── analise-requisitos.html
└── entrega_grupo/
    ├── 1_processo/
    ├── 2_artefato_instrucoes/
    ├── 3_relatorio_tecnico/
    ├── 4_evidencias/
    └── 5_cenario_real/
```

## Como contribuir

1. Antes de implementar algo que dependa de uma decisão em aberto, confira a issue correspondente.
2. Ao tomar uma decisão técnica, registre-a no [Relatório Técnico](docs/relatorio-tecnico.md) como ADR, com contexto, alternativas e justificativa.
3. Ao implementar uma decisão, preencha o campo "Evidência na implementação" do ADR com o caminho do código.
4. Se a implementação divergir de um requisito ou de um ADR, registre na seção 14 do relatório.
