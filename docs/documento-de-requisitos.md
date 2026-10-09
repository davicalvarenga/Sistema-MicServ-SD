# Documento de Requisitos

**Grupo:** Fornecimento e Produtos
**Sistema:** Portal B2B Distribuído (disciplina de Sistemas Distribuídos)
**Integrantes:** Daniel Carvalho Coutinho, Davi Coelho de Alvarenga, Gabriel Vicentte dos Santos Ferreira, Rafael de Castro Noleto
**Versão:** 0.2 (rascunho para revisão interna)
**Data:** 09/10/2026

> Itens com status **Pendente** ou **Proposto** ainda podem mudar. O time de QA deve testar apenas itens com status **Confirmado** até a versão 1.0 deste documento.

---

## 1. Introdução

### 1.1 Propósito

Este documento descreve os requisitos dos serviços sob responsabilidade do grupo Fornecimento e Produtos. Ele é a referência do time de QA para planejar e executar testes. Cada requisito indica a fonte de onde veio e o seu status, para que fique claro o que foi exigido pelo professor, o que vem do diagrama de arquitetura e o que é decisão do grupo.

### 1.2 Escopo

Conforme o diagrama "Arquitetura do Portal B2B Distribuído" fornecido pelo professor (fonte F2), o grupo é responsável por dois microsserviços:

| Serviço | Bloco no diagrama | Responsabilidades | Banco |
|---|---|---|---|
| Produtos | 2 | Catálogo de produtos, categoria, unidade, tipo de transporte | db produtos |
| Fornecimentos | 3 | Relação entre fornecedor e produto, preço, quantidade, origem, estoque | db fornecimentos |

Os dois serviços se comunicam com os demais módulos por eventos no Kafka.

A lista de responsabilidades do grupo (F1) diz "conversar com o time de mercado e negociação, logística frete e transportadoras". O texto fala em conversar com outros times, e o diagrama (F2) mostra esses módulos como serviços próprios (blocos 5, 6, 8 e 9). O papel do grupo em relação a eles é de **integração** por eventos, e não de implementação.

### 1.3 Fora do escopo

Os itens abaixo pertencem a outros grupos. Este documento descreve apenas a interface que esperamos deles (seção 2.2).

- Cadastro de empresas, perfis de acesso, emissão e validação de tokens (Usuários/Acesso e API Gateway)
- Frontend (Web/App)
- Demanda, Mercado (matching), Negociação/Leilão e Pedidos
- Solicitação e cotação de frete, cadastro de transportadoras (Logística/Frete e Transportadoras)
- Infraestrutura de plataforma: cluster Kafka, Schema Registry, API Gateway, monitoramento e logs centralizados

### 1.4 Fontes

| ID | Fonte |
|---|---|
| F1 | Lista de responsabilidades do grupo (arquivo "FORNECIMENTO E PRODUTOS - MEMBROS"): gestão de estoque, conversa com os times de mercado e negociação, logística, frete e transportadoras, fornecimento e produtos, estoque, tipo de transporte, cadastro de produtos, categoria de produto, quantidade e origem de produtos, preço, relação entre fornecedor e produto, criação de relação de fornecimento pelos fornecedores |
| F2 | Diagrama "Arquitetura do Portal B2B Distribuído", elaborado pelo professor |
| F3 | Requisitos gerais do professor: autenticação obrigatória e token temporário |
| F4 | Decisões do grupo, justificadas no Relatório Técnico |
| F5 | Orientações de integração via Kafka (tecnologia definida pela turma): o módulo produz e consome tópicos para atualizar o estoque, publica e consome eventos de criação, alteração e exclusão de produtos e eventos de pedido de fornecimento entre fornecedor e grupo |

### 1.5 Convenções

**Identificadores:** RF (requisito funcional), RNF (requisito não funcional), RD (requisito de dados), RN (regra de negócio), UC (caso de uso), CA (critério de aceitação), P (pendência).

**Origem:** identificador da fonte (F1 a F5, seção 1.4). F4 indica decisão do grupo.

**Status:**

| Status | Significado |
|---|---|
| Confirmado | Definido por fonte oficial (F1, F2 ou F3). Pode ser testado |
| Proposto | Decisão do grupo. Pode mudar até a versão 1.0 |
| Pendente | Depende de resposta externa. A pendência correspondente é indicada |

### 1.6 Glossário

| Termo | Definição |
|---|---|
| Produto | Item do catálogo, com categoria, unidade e tipo de transporte (F2, bloco 2) |
| Categoria | Classificação do produto. Forma de cadastro em aberto (P-10) |
| Unidade | Unidade de medida em que o produto é negociado. Valores em aberto (P-06) |
| Tipo de transporte | Atributo do produto relacionado ao transporte (F2, bloco 2). Valores em aberto (P-06) |
| Fornecedor | Empresa (CNPJ) com perfil de fornecedor, cadastrada no módulo Usuários/Acesso (F2, bloco 1) |
| Fornecimento | Registro em que um fornecedor oferece um produto, com preço, quantidade e origem (F2, bloco 3). Corresponde ao passo 1 do fluxo do diagrama: "Fornecedor publica fornecimento" |
| Estoque | Interpretação adotada: quantidade disponível de um fornecimento. Pendente de confirmação (P-03) |
| Origem | Significado em aberto (P-05). F1 a associa ao produto ("quantidade e origem de produtos") e F2 a coloca no bloco Fornecimentos |
| Evento | Mensagem publicada no Kafka que informa algo que já aconteceu |
| Token | Credencial temporária de acesso. O diagrama cita JWT/OAuth2 (F2, infraestrutura) |

---

## 2. Contexto

### 2.1 Atores

| Ator | Interação com os nossos serviços | Status |
|---|---|---|
| Fornecedor | Publica fornecimentos (F2, fluxo passo 1) | Confirmado |
| Administrador | Aparece como cliente no diagrama. Permissões nos nossos serviços não definidas | Pendente (P-07) |
| Comprador | Aparece como cliente no diagrama. Acesso ao catálogo não definido | Pendente (P-07) |
| Serviços de outros grupos | Publicam e consomem eventos via Kafka | Ver seção 9 |

### 2.2 Interfaces esperadas de outros módulos

| Módulo | O que esperamos dele | Status |
|---|---|---|
| Usuários/Acesso | Token com identificação da empresa e do perfil (fornecedor, comprador, transportadora). Evento `empresa_cadastrada` com identificador e perfis da empresa | Pendente (P-07, P-12) |
| API Gateway | Autenticação das requisições e roteamento para os nossos serviços. Definição de como a identidade do usuário chega ao serviço | Pendente (P-04) |
| Negociação/Leilão ou Pedidos | Evento que altera o estoque, com identificador único, fornecimento, quantidade e tipo de alteração | Pendente (P-02) |
| Mercado | Consumo de `fornecimento_criado` e `estoque_atualizado` para o cálculo de oferta e demanda (F2, fluxo passo 4) | Pendente (P-19) |
| Logística/Frete | Possível consumo do tipo de transporte do produto | Pendente (P-19) |
| Plataforma | Cluster Kafka disponível. Definição sobre o uso do Schema Registry | Pendente (P-08) |

### 2.3 Premissas

1. A autenticação usa tokens JWT/OAuth2, como indicado na camada de segurança do diagrama (F2). O mecanismo exato de validação é definido pelo grupo de autenticação (P-04).
2. Cada serviço tem banco de dados próprio e nenhum outro serviço o acessa diretamente (F2, legenda "Banco de dados próprio de cada serviço").
3. Toda comunicação entre módulos acontece por eventos Kafka. Chamadas REST ocorrem apenas entre Frontend, API Gateway e serviços (F2, legenda).

---

## 3. Requisitos funcionais

### 3.1 Serviço de Produtos

| ID | Requisito | Origem | Status |
|---|---|---|---|
| RF-01 | O sistema deve permitir cadastrar produto com categoria, unidade e tipo de transporte | F1, F2 | Confirmado (atributos completos: P-06) |
| RF-02 | O sistema deve permitir consultar produtos, em lista e por identificador | F4 | Proposto |
| RF-03 | O sistema deve permitir alterar um produto cadastrado | F5 | Confirmado |
| RF-04 | O sistema deve permitir excluir um produto | F5 | Confirmado (regra de exclusão: P-09) |
| RF-05 | O sistema deve permitir gerenciar as categorias de produto | F1, F2 | Pendente (P-10) |
| RF-06 | Ao cadastrar um produto, o serviço deve publicar o evento `produto_cadastrado` | F2, F5 | Confirmado |
| RF-07 | Ao alterar um produto, o serviço deve publicar o evento `produto_atualizado` | F5 | Confirmado (nome do evento: Proposto) |
| RF-08 | Ao excluir um produto, o serviço deve publicar o evento `produto_excluido` | F5 | Confirmado (nome do evento: Proposto) |

### 3.2 Serviço de Fornecimentos

| ID | Requisito | Origem | Status |
|---|---|---|---|
| RF-09 | O fornecedor deve poder criar um fornecimento (relação de fornecimento) informando produto, preço, quantidade e origem | F1, F2 | Confirmado |
| RF-10 | O sistema deve permitir consultar fornecimentos, em lista e por identificador, incluindo a quantidade disponível | F4 | Proposto |
| RF-11 | O sistema deve permitir alterar ou encerrar um fornecimento | F4 | Pendente (P-11) |
| RF-12 | Ao criar um fornecimento, o serviço deve publicar o evento `fornecimento_criado` | F2 | Confirmado |
| RF-13 | O serviço deve manter a quantidade disponível (estoque) de cada fornecimento | F1, F2 | Pendente (P-03) |
| RF-14 | O serviço deve atualizar o estoque ao consumir eventos de outros módulos | F5 | Pendente (P-02) |
| RF-15 | Sempre que o estoque mudar, o serviço deve publicar o evento `estoque_atualizado` | F2, F5 | Confirmado |
| RF-16 | O serviço de Fornecimentos deve consumir os eventos de produto (criação, alteração e exclusão) para manter uma referência local dos produtos válidos | F5, F4 | Proposto |
| RF-17 | O serviço de Fornecimentos deve consumir o evento `empresa_cadastrada` para reconhecer as empresas com perfil de fornecedor | F2, F4 | Pendente (P-12) |
| RF-18 | O sistema deve publicar e consumir eventos de pedido de fornecimento entre fornecedor e grupo | F5 | Pendente (P-13) |

**Justificativa do RF-16:** as orientações de integração (F5) exigem que o módulo consuma eventos de produto. Com Produtos e Fornecimentos em serviços separados e com bancos separados (F2), o serviço de Fornecimentos precisa saber quais produtos existem sem acessar o banco de Produtos. Consumir os eventos de produto atende às duas exigências.

---

## 4. Requisitos não funcionais

| ID | Requisito | Categoria | Origem | Status |
|---|---|---|---|---|
| RNF-01 | Todos os endpoints dos dois serviços exigem autenticação. Requisição sem token é recusada | Segurança | F3 | Confirmado |
| RNF-02 | Requisição com token expirado ou inválido é recusada com HTTP 401, e o cliente precisa se autenticar novamente | Segurança | F3 | Confirmado (formato da resposta: P-04) |
| RNF-03 | Requisição autenticada sem o perfil necessário é recusada com HTTP 403 | Segurança | F4 | Proposto (perfis: P-07) |
| RNF-04 | A comunicação entre módulos é feita por eventos Kafka | Interoperabilidade | F2, F5 | Confirmado |
| RNF-05 | Cada serviço tem banco próprio, inacessível diretamente por outros serviços | Manutenibilidade | F2 | Confirmado |
| RNF-06 | O processamento de eventos consumidos é idempotente: o mesmo evento recebido mais de uma vez produz o mesmo resultado que uma única vez | Confiabilidade | F4 | Proposto |
| RNF-07 | Eventos de uma mesma entidade são publicados com o identificador da entidade como chave da mensagem | Confiabilidade | F4 | Proposto |
| RNF-08 | Os produtores Kafka são configurados com `acks=all` e `enable.idempotence=true` | Confiabilidade | F4 | Proposto |
| RNF-09 | Nenhum evento publicado contém token de acesso | Segurança | F4 | Proposto |
| RNF-10 | Um evento que falha no processamento depois de esgotadas as tentativas é enviado a um tópico de erro, sem bloquear o consumo dos demais | Confiabilidade | F4 | Proposto |
| RNF-11 | Os serviços registram logs com identificador de correlação por requisição e por evento | Manutenibilidade | F4 | Proposto (integração com ELK/Loki: P-14) |
| RNF-12 | Os serviços são executáveis em contêiner Docker | Portabilidade | F2 | Pendente (P-14) |
| RNF-13 | Os esquemas dos eventos são registrados no Schema Registry | Interoperabilidade | F2 | Pendente (P-08) |

**Justificativas técnicas:**

- **RNF-06:** em caso de falha do consumidor entre o processamento da mensagem e o registro do offset, o Kafka entrega a mensagem novamente (semântica "at least once", documentação do Apache Kafka, seção *Message Delivery Semantics*). Sem idempotência, uma mesma baixa de estoque poderia ser aplicada duas vezes.
- **RNF-07:** o Kafka garante ordem apenas dentro de uma partição, e mensagens com a mesma chave vão para a mesma partição (documentação do Apache Kafka, seção *Topics and Partitions*). Usar o identificador da entidade como chave preserva a ordem dos eventos de um mesmo produto ou fornecimento.
- **RNF-08:** são os padrões do produtor desde o Kafka 3.0 (KIP-679). Um defeito impediu que fossem aplicados nas versões 3.0.0 e 3.1.0, corrigido em 3.0.1, 3.1.1 e 3.2.0 (notas de atualização do Apache Kafka). A configuração explícita elimina a dependência da versão usada.
- **RNF-09:** o token expira, e o evento permanece armazenado no Kafka durante o período de retenção. Gravar o token no evento expõe uma credencial. O evento leva apenas o identificador de quem executou a ação.

**Desempenho:** nenhuma fonte define metas de desempenho. Nenhum requisito de desempenho é incluído até essa definição (P-18), porque um requisito sem meta mensurável não pode ser verificado pelo QA.

---

## 5. Requisitos de dados

| ID | Entidade | Atributos | Origem | Status |
|---|---|---|---|---|
| RD-01 | Produto | Identificador, categoria, unidade, tipo de transporte | F1, F2 | Confirmado |
| RD-02 | Produto | Nome e descrição | F4 | Proposto (P-06) |
| RD-03 | Fornecimento | Identificador, fornecedor (empresa), produto, preço, quantidade, origem | F1, F2 | Confirmado (posição de origem: P-05) |
| RD-04 | Fornecimento | Formato do preço (moeda e precisão) | F4 | Pendente (P-15) |
| RD-05 | Categoria | Estrutura (lista fixa, cadastro, hierarquia) | F1 | Pendente (P-10) |

---

## 6. Regras de negócio

### 6.1 Regras definidas

| ID | Regra | Origem | Status |
|---|---|---|---|
| RN-01 | Um fornecimento relaciona um fornecedor e um produto | F1, F2 | Confirmado |
| RN-02 | Apenas empresas com perfil de fornecedor podem criar fornecimentos | F1, F2 | Proposto (P-07) |
| RN-03 | Um fornecimento só pode referenciar um produto existente no catálogo | F4 | Proposto |

### 6.2 Regras em aberto

As perguntas abaixo não têm resposta nas fontes. Não devem ser testadas até a definição.

| Pendência | Pergunta |
|---|---|
| P-09 | A exclusão de produto é lógica ou física? O que acontece com os fornecimentos ativos do produto excluído? |
| P-16 | O estoque pode ficar negativo? O que acontece quando chega uma baixa maior que a quantidade disponível? |
| P-20 | Um fornecedor pode ter mais de um fornecimento do mesmo produto? |
| P-21 | Preço e quantidade podem ser zero? |

---

## 7. Casos de uso

### UC-01 Cadastrar produto

- **Ator:** em aberto (P-07)
- **Pré-condição:** ator autenticado com token válido
- **Fluxo principal:**
  1. O ator envia os dados do produto.
  2. O serviço valida os dados obrigatórios.
  3. O serviço grava o produto.
  4. O serviço publica `produto_cadastrado`.
  5. O serviço retorna HTTP 201 com o identificador do produto.
- **Fluxos alternativos:**
  - A1. Token ausente, expirado ou inválido: o serviço retorna HTTP 401. Nada é gravado nem publicado.
  - A2. Dados obrigatórios ausentes ou inválidos: o serviço retorna HTTP 400 indicando os campos com erro. Nada é gravado nem publicado.
- **Requisitos relacionados:** RF-01, RF-06, RNF-01, RNF-02

### UC-02 Publicar fornecimento

- **Ator:** Fornecedor
- **Pré-condição:** fornecedor autenticado com token válido
- **Fluxo principal** (F2, fluxo passo 1):
  1. O fornecedor informa produto, preço, quantidade e origem.
  2. O serviço valida os dados e verifica se o produto existe (RN-03).
  3. O serviço grava o fornecimento.
  4. O serviço publica `fornecimento_criado`.
  5. O serviço retorna HTTP 201 com o identificador do fornecimento.
- **Fluxos alternativos:**
  - A1. Token ausente, expirado ou inválido: HTTP 401. Nada é gravado nem publicado.
  - A2. Empresa sem perfil de fornecedor: HTTP 403 (RN-02, P-07).
  - A3. Produto inexistente: HTTP 422. Nada é gravado nem publicado.
  - A4. Dados inválidos: HTTP 400 indicando os campos com erro.
- **Requisitos relacionados:** RF-09, RF-12, RN-01, RN-02, RN-03

### UC-03 Atualizar estoque a partir de evento

- **Ator:** serviço de outro grupo (P-02)
- **Pré-condição:** fornecimento existente
- **Fluxo principal:**
  1. O serviço de Fornecimentos consome o evento de alteração de estoque.
  2. O serviço verifica se o identificador do evento já foi processado.
  3. O serviço aplica a alteração na quantidade disponível do fornecimento.
  4. O serviço publica `estoque_atualizado`.
- **Fluxos alternativos:**
  - A1. Evento já processado: o serviço ignora o evento e não publica novo `estoque_atualizado` (RNF-06).
  - A2. Evento com formato inválido ou que falha após as tentativas: o evento vai para o tópico de erro (RNF-10).
  - A3. Quantidade solicitada maior que a disponível: comportamento em aberto (P-16).
- **Requisitos relacionados:** RF-13, RF-14, RF-15, RNF-06, RNF-10

---

## 8. Critérios de aceitação

```gherkin
CA-01 (RNF-01)
Dado uma requisição sem token de acesso
Quando o cliente chama qualquer endpoint do serviço de Produtos ou de Fornecimentos
Então a resposta tem status 401
E nenhum dado é retornado

CA-02 (RNF-02)
Dado um token cuja data de expiração já passou
Quando o cliente chama qualquer endpoint do serviço de Produtos ou de Fornecimentos
Então a resposta tem status 401
E nenhum dado é retornado

CA-03 (RF-01, RF-06)
Dado um usuário autenticado com permissão de cadastro
Quando ele cadastra um produto com dados válidos
Então a resposta tem status 201 e contém o identificador do produto
E o evento produto_cadastrado é publicado com o identificador do produto como chave

CA-04 (RF-03, RF-07)
Dado um produto cadastrado
Quando um usuário autorizado altera o produto
Então o evento produto_atualizado é publicado com o identificador do produto como chave

CA-05 (RF-04, RF-08)
Dado um produto cadastrado
Quando um usuário autorizado exclui o produto
Então o evento produto_excluido é publicado com o identificador do produto como chave

CA-06 (RF-09, RF-12)
Dado um fornecedor autenticado
E um produto existente no catálogo
Quando o fornecedor cria um fornecimento com preço, quantidade e origem válidos
Então a resposta tem status 201
E o evento fornecimento_criado é publicado com o identificador do fornecimento como chave

CA-07 (RNF-06, UC-03)
Dado um evento de alteração de estoque já processado
Quando o mesmo evento é recebido novamente
Então a quantidade disponível do fornecimento não muda
E nenhum novo evento estoque_atualizado é publicado

CA-08 (RNF-09)
Dado qualquer evento publicado pelos serviços de Produtos ou de Fornecimentos
Quando o conteúdo e os headers do evento são inspecionados
Então nenhum token de acesso está presente

CA-09 (UC-01 A1, UC-02 A1)
Dado uma requisição de cadastro com token expirado
Quando o serviço recusa a requisição
Então nenhum registro é gravado
E nenhum evento é publicado
```

O CA-02 poderá exigir o cabeçalho `WWW-Authenticate: Bearer error="invalid_token"` (RFC 6750, seção 3.1) se o grupo de autenticação confirmar o uso de Bearer token (P-04).

---

## 9. Eventos

| Evento | Serviço | Papel do serviço | Chave | Consumidores esperados | Status |
|---|---|---|---|---|---|
| `produto_cadastrado` | Produtos | Publica | Identificador do produto | Fornecimentos. Outros: P-19 | Confirmado (F2) |
| `produto_atualizado` | Produtos | Publica | Identificador do produto | Fornecimentos. Outros: P-19 | Proposto |
| `produto_excluido` | Produtos | Publica | Identificador do produto | Fornecimentos. Outros: P-19 | Proposto |
| `produto_*` | Fornecimentos | Consome | Identificador do produto | | Proposto (RF-16) |
| `fornecimento_criado` | Fornecimentos | Publica | Identificador do fornecimento | Mercado (P-19) | Confirmado (F2) |
| `estoque_atualizado` | Fornecimentos | Publica | Identificador do fornecimento | P-19 | Confirmado (F2) |
| `empresa_cadastrada` | Fornecimentos | Consome | Definida por Usuários/Acesso | | Pendente (P-12) |
| Evento que altera o estoque | Fornecimentos | Consome | Definida pelo produtor | | Pendente (P-02) |
| Pedido de fornecimento | A definir | Publica e consome | A definir | | Pendente (P-13) |

O diagrama não deixa claro se os nomes acima são nomes de tópicos ou tipos de evento (P-17). A diferença importa: se `produto_cadastrado` e `produto_atualizado` estiverem em tópicos diferentes, o Kafka não garante a ordem entre eles, e um consumidor pode receber a alteração antes do cadastro (ver justificativa do RNF-07).

O formato do conteúdo de cada evento será detalhado em documento próprio de contrato de eventos, depois da definição da turma sobre serialização e envelope (P-08).

---

## 10. Matriz de rastreabilidade

| Requisito | Origem | Caso de uso | Critério de aceitação |
|---|---|---|---|
| RF-01 | F1, F2 | UC-01 | CA-03 |
| RF-03 | F5 | | CA-04 |
| RF-04 | F5 | | CA-05 |
| RF-06 | F2, F5 | UC-01 | CA-03 |
| RF-07 | F5 | | CA-04 |
| RF-08 | F5 | | CA-05 |
| RF-09 | F1, F2 | UC-02 | CA-06 |
| RF-12 | F2 | UC-02 | CA-06 |
| RF-13, RF-14, RF-15 | F1, F2, F5 | UC-03 | CA-07 |
| RNF-01 | F3 | UC-01, UC-02 | CA-01 |
| RNF-02 | F3 | UC-01, UC-02 | CA-02, CA-09 |
| RNF-06 | F4 | UC-03 | CA-07 |
| RNF-09 | F4 | | CA-08 |

Requisitos sem critério de aceitação nesta versão estão com status Proposto ou Pendente.

---

## 11. Pendências

| ID | Pergunta | A quem perguntar |
|---|---|---|
| P-01 | **Resolvida na versão 0.2.** O escopo do grupo é implementar os blocos 2 e 3 do diagrama e integrar com os demais. A lista de responsabilidades (F1) fala em "conversar com" os times de mercado, negociação, logística, frete e transportadoras, e o diagrama (F2) mostra esses módulos como serviços próprios | |
| P-02 | Qual evento altera o estoque (`negociacao_fechada`, `pedido_criado` ou outro) e quais campos ele traz? | Grupos de Negociação e Pedidos |
| P-03 | Estoque é a quantidade disponível de cada fornecimento? | Professor |
| P-04 | O serviço deve revalidar o JWT ou confiar no API Gateway? Qual o formato da resposta de token inválido? | Grupo de autenticação |
| P-05 | O que significa "origem"? Ela é atributo do produto (F1 cita "quantidade e origem de produtos") ou do fornecimento (F2 a coloca no bloco Fornecimentos)? | Professor |
| P-06 | Quais os atributos obrigatórios do produto e os valores possíveis de unidade e tipo de transporte? | Professor |
| P-07 | Quais perfis podem cadastrar, alterar e excluir produtos e categorias? Comprador e administrador acessam os nossos serviços? | Professor, grupo de autenticação |
| P-08 | Qual a serialização dos eventos, o envelope padrão e o uso do Schema Registry? | Turma |
| P-09 | A exclusão de produto é lógica ou física? O que acontece com os fornecimentos do produto? | Professor |
| P-10 | Categorias são uma lista fixa ou um cadastro? Existe hierarquia? | Professor |
| P-11 | Um fornecimento pode ser alterado (inclusive para repor quantidade) ou encerrado? Há eventos para isso? F1 cita "gestão de estoque" sem detalhar as operações | Professor |
| P-12 | Qual o contrato do evento `empresa_cadastrada`? | Grupo de Usuários/Acesso |
| P-13 | "Pedido de fornecimento entre fornecedor e grupo" corresponde ao `fornecimento_criado` ou é outro fluxo? | Professor |
| P-14 | O uso de Docker, logs centralizados (ELK/Loki) e monitoramento (Prometheus/Grafana) é obrigatório? | Professor, turma |
| P-15 | Qual o formato do preço (moeda e precisão)? | Professor |
| P-16 | O estoque pode ficar negativo? | Professor |
| P-17 | Os nomes de eventos do diagrama são tópicos ou tipos de evento? | Professor, turma |
| P-18 | Existem metas de desempenho? | Professor |
| P-19 | Quais módulos consomem os eventos de produto, `fornecimento_criado` e `estoque_atualizado`? | Demais grupos |
| P-20 | Um fornecedor pode ter mais de um fornecimento do mesmo produto? | Professor |
| P-21 | Preço e quantidade podem ser zero? | Professor |

---

## 12. Referências

- ISO/IEC/IEEE 29148:2018, Systems and software engineering, Life cycle processes, Requirements engineering. Base da estrutura deste documento.
- ISO/IEC 25010, modelo de qualidade de produto. Base das categorias dos requisitos não funcionais.
- Apache Kafka, documentação oficial: https://kafka.apache.org/documentation/
- KIP-679, Producer will enable the strongest delivery guarantee by default: https://cwiki.apache.org/confluence/display/KAFKA/KIP-679%3A+Producer+will+enable+the+strongest+delivery+guarantee+by+default
- Apache Kafka, notas de atualização (correção do KAFKA-13598): https://kafka.apache.org/31/getting-started/upgrade/
- RFC 6750, The OAuth 2.0 Authorization Framework: Bearer Token Usage: https://datatracker.ietf.org/doc/html/rfc6750
- RFC 9110, HTTP Semantics (códigos 400, 401, 403 e 422): https://datatracker.ietf.org/doc/html/rfc9110
- Gherkin Reference: https://cucumber.io/docs/gherkin/reference/

---

## Histórico de revisões

| Versão | Data | Descrição |
|---|---|---|
| 0.1 | 09/10/2026 | Rascunho inicial com base no enunciado, nos requisitos do professor e no diagrama de arquitetura |
| 0.2 | 09/10/2026 | Inclusão da lista de responsabilidades do grupo como fonte F1 e das orientações de Kafka como fonte F5. Origem de cada requisito passa a indicar a fonte exata. P-01 resolvida. P-05 e P-11 detalhadas |
