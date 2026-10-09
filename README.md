# Fornecimento e Produtos | Portal B2B Distribuído

Microsserviços de **Produtos** e **Fornecimentos** do Portal B2B Distribuído, trabalho da disciplina de Sistemas Distribuídos. O portal é dividido entre vários grupos da turma, e os módulos se comunicam por eventos no Apache Kafka.

## Integrantes

- Daniel Carvalho Coutinho
- Davi Coelho de Alvarenga
- Gabriel Vicentte dos Santos Ferreira
- Rafael de Castro Noleto

## Responsabilidades do grupo

| Serviço | O que faz |
|---|---|
| Produtos | Cadastro de produtos, categoria, unidade e tipo de transporte |
| Fornecimentos | Relação de fornecimento entre fornecedor e produto, preço, quantidade, origem e controle de estoque |

O controle de estoque separa a **quantidade disponível** da **quantidade reservada**. Quando um pedido é criado, a quantidade é reservada. Se o pedido for cancelado, ela volta a ficar disponível. Se a venda for concluída, ela sai do estoque.

O grupo se integra, por eventos Kafka, com os módulos de Usuários/Acesso, Mercado, Negociação/Leilão, Pedidos e Logística/Frete, que são de outros grupos.

## Eventos

| Evento | Papel do grupo |
|---|---|
| `produto_cadastrado`, `produto_atualizado`, `produto_excluido` | Publica (Produtos) e consome (Fornecimentos) |
| `fornecimento_criado` | Publica |
| `estoque_atualizado` | Publica |
| `pedido_criado`, `pedido_atualizado` | Consome, para reservar, liberar ou dar baixa no estoque |
| `empresa_cadastrada` | Consome |

O formato dos eventos e os nomes finais dos tópicos ainda estão em definição ([issue #3](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/3)).

## Documentação

| Documento | Conteúdo |
|---|---|
| [Documento de Requisitos](docs/documento-de-requisitos.md) | Requisitos funcionais e não funcionais, regras de negócio, casos de uso e critérios de aceitação. Referência do time de QA |
| [Relatório Técnico](docs/relatorio-tecnico.md) | Arquitetura, implementação e registro de cada decisão técnica com a sua justificativa |

## Situação atual

O projeto está na fase de levantamento de requisitos e definição de arquitetura. Ainda não há código.

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

## Tecnologias

| Item | Escolha |
|---|---|
| Mensageria | Apache Kafka (definido pela turma) |
| Contêineres | Docker (exigido pelo professor) |
| Linguagem, framework e banco | Em definição ([issue #10](https://github.com/davicalvarenga/Sistema-MicServ-SD/issues/10)) |

## Como executar

As instruções de execução serão adicionadas quando a stack for definida e o primeiro serviço estiver implementado. A execução será feita com Docker.

## Estrutura do repositório

```
.
├── README.md
└── docs/
    ├── documento-de-requisitos.md
    └── relatorio-tecnico.md
```

## Como contribuir

1. Antes de implementar algo que dependa de uma decisão em aberto, confira a issue correspondente.
2. Ao tomar uma decisão técnica, registre-a no [Relatório Técnico](docs/relatorio-tecnico.md) como ADR, com contexto, alternativas e justificativa.
3. Ao implementar uma decisão, preencha o campo "Evidência na implementação" do ADR com o caminho do código.
4. Se a implementação divergir de um requisito ou de um ADR, registre na seção 14 do relatório.
