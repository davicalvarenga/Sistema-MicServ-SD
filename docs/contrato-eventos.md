# Contrato de Eventos

**Grupo:** Fornecimento e Produtos (`produtos-service` e `fornecimentos-service`)
**Versão:** 2.1 (proposta para revisão dos grupos que integram com a gente)
**Data:** 18/11/2026 (versão 1.0: 26/10/2026)

Este documento define o conteúdo dos eventos que o grupo publica e o que o grupo precisa receber dos eventos que consome. Ele complementa o catálogo do kit de infraestrutura (`CONTRACTS.md`, commit `630515c`), que define tópicos, chaves e envelope, mas não o `payload`.

Cada evento tem um JSON Schema em [`contratos/schemas/`](contratos/schemas/) e um exemplo válido em [`contratos/exemplos/`](contratos/exemplos/). Os grupos podem usar os schemas para validar automaticamente o que publicam e o que recebem.

---

## 1. Regras gerais

| Regra | Detalhe | Origem |
|---|---|---|
| Envelope | Todo evento tem `eventId` (UUID), `eventType` (nome do tópico), `eventVersion` (`"1.0"`), `timestamp` (ISO-8601 em UTC), `source` (serviço produtor), `correlationId` (texto), `aggregateId` (chave da mensagem) e `payload` | Kit, `CONTRACTS.md` |
| Chave da mensagem | É sempre o `aggregateId` | Kit, CT-E02 |
| Nomes de campos | `camelCase` no `payload`, como no envelope e no exemplo de `pedido_criado` do kit | Grupo |
| Quantidades e preços | Números JSON com até 2 casas decimais (`NUMERIC(12,2)` no banco). Quem recebe deve converter para decimal antes de fazer contas | Kit, banco |
| Datas | ISO-8601 em UTC (ex.: `2026-10-26T14:00:00Z`) | Kit |
| `correlationId` | Texto não vazio, **não necessariamente UUID**: o gateway do kit repassa o `X-Correlation-Id` do cliente e, se ele não vier, usa o `$request_id` do Nginx (32 caracteres hexadecimais) | Kit, `gateway/nginx.conf` |
| Identificação de quem agiu | Objeto com `empresaId` e `usuarioId`. **Nenhum evento leva token de acesso** | RNF-09 |
| Campos desconhecidos | Os nossos consumidores ignoram campos que não conhecem. Os nossos eventos só aceitam os campos definidos no schema | Grupo |
| Evolução | Adicionar campo opcional mantém a `eventVersion`. Remover, renomear ou mudar o tipo de um campo exige nova `eventVersion` e aviso aos consumidores. É o que mantém a compatibilidade `BACKWARD` configurada no Schema Registry do kit | Kit, grupo |
| Idempotência | Os consumidores usam o `eventId` para ignorar eventos repetidos (tabela `processed_events`) | Kit, RNF-06 |

**Por que os schemas não usam `multipleOf: 0.01`:** testamos e, em ponto flutuante, `0.07 / 0.01` dá `7.000000000000001`. Com essa regra, preços válidos como 0,07, 1,15 e 1.234.567,89 seriam rejeitados. A precisão de 2 casas é validada no código do serviço.

---

## 2. Eventos que publicamos

### 2.1 `produto_cadastrado`

- **Produtor:** `produtos-service`. **Chave:** `produtoId`. **Consumidores (kit):** `fornecimentos-service`, `demanda-service`, `mercado-service`. O grupo de Logística/Transporte não consome este evento: recebe o tipo de transporte pelo `pedido_criado`, que o grupo de Pedidos preenche a partir do produto. Se o grupo de Pedidos não puder incluir o campo, o plano B da Logística é consumir `produto_cadastrado` e `produto_atualizado` e guardar uma cópia local (resposta da Logística, 10/11/2026).
- **Quando:** depois que o produto é gravado com sucesso (RF-06).
- **Schema:** [`produto_cadastrado.schema.json`](contratos/schemas/produto_cadastrado.schema.json)

| Campo | Tipo | Descrição |
|---|---|---|
| `produtoId` | texto | Identificador do produto |
| `nome` | texto | Nome do produto |
| `categoria` | texto | Um valor da lista fixa: `GRAOS`, `INSUMOS`, `SUBPRODUTOS`, `LATICINIOS`, `CARNES`, `HORTIFRUTI`, `BEBIDAS` ou `OUTROS` (o professor definiu lista fixa; o conteúdo é do grupo, P-10) |
| `unidade` | texto | Unidade de medida: `KG`, `TON`, `UN`, `CX` ou `L` (lista do kit, confirmada pela Logística; P-06 resolvida) |
| `tipoTransporte` | texto | Como o produto precisa ser transportado: `GRANEL`, `REFRIGERADO`, `CARGA_SECA` ou `PERIGOSO` (lista do kit, confirmada pela Logística; P-06 resolvida) |
| `pesoUnitarioKg` | número ou `null` | Peso de uma unidade em kg, até 3 casas decimais. Opcional no cadastro: `null` quando não informado. Pedido pela Logística para calcular o peso da carga quando a unidade é `UN`, `CX` ou `L` |
| `cadastradoPor` | objeto | `empresaId` e `usuarioId` de quem cadastrou |
| `cadastradoEm` | data e hora | Momento do cadastro |

```json
{
  "eventId": "3f0c2a8e-6a1b-4f4e-9a7d-1c2b3d4e5f60",
  "eventType": "produto_cadastrado",
  "eventVersion": "1.0",
  "timestamp": "2026-10-26T14:00:00.000Z",
  "source": "produtos-service",
  "correlationId": "d3b07384-d113-4f9e-8c65-27a36c8d76e4",
  "aggregateId": "prod-1",
  "payload": {
    "produtoId": "prod-1",
    "nome": "Leite integral",
    "categoria": "LATICINIOS",
    "unidade": "L",
    "tipoTransporte": "REFRIGERADO",
    "pesoUnitarioKg": null,
    "cadastradoPor": { "empresaId": "emp-34", "usuarioId": "usr-7" },
    "cadastradoEm": "2026-10-26T14:00:00.000Z"
  }
}
```

### 2.2 `produto_atualizado` e `produto_excluido`

- **Produtor:** `produtos-service`. **Chave:** `produtoId`. **Consumidores:** `fornecimentos-service` (cópia local); `demanda-service` e `mercado-service`, se quiserem manter cópias.
- **Quando:** a empresa que cadastrou o produto o altera ou exclui. Só é permitido enquanto o produto não tem movimentação, isto é, nenhum fornecimento (resposta do professor). Mudança de especificação de produto com movimentação é um produto novo.
- **Tópicos:** o kit ainda não tem esses tópicos (P-26). O Redpanda do kit, em modo `dev-container`, os cria na primeira publicação com 1 partição; a criação com 3 partições foi pedida à Infraestrutura.


- `produto_atualizado` leva o estado completo do produto depois da alteração (mesmos campos do cadastro, com `atualizadoPor` e `atualizadoEm`). Schema: [`produto_atualizado.schema.json`](contratos/schemas/produto_atualizado.schema.json)
- `produto_excluido` leva `produtoId`, `excluidoPor` e `excluidoEm`. Schema: [`produto_excluido.schema.json`](contratos/schemas/produto_excluido.schema.json)

Como cada tópico só garante ordem dentro dele mesmo, quem consome deve comparar o `timestamp` do evento com o do último evento aplicado ao produto e descartar eventos mais antigos.

### 2.3 `fornecimento_criado`

- **Produtor:** `fornecimentos-service`. **Chave:** `fornecimentoId`. **Consumidor (kit):** `mercado-service`.
- **Quando:** depois que o fornecedor cria uma oferta (RF-12).
- **Schema:** [`fornecimento_criado.schema.json`](contratos/schemas/fornecimento_criado.schema.json)

| Campo | Tipo | Descrição |
|---|---|---|
| `fornecimentoId` | texto | Identificador da oferta |
| `fornecedorId` | texto | Empresa fornecedora. Vem do token, nunca do corpo da requisição (RN-10) |
| `produtoId` | texto | Produto ofertado |
| `unidade` | texto | Unidade do produto, para interpretar quantidade e preço |
| `preco` | número | Preço por unidade em reais (BRL), maior ou igual a zero, com até 2 casas decimais (P-15) |
| `quantidadeDisponivel` | número | Quantidade ofertada, maior ou igual a zero |
| `origem` | objeto | Ponto de coleta: `cidade` (texto) e `uf` (sigla de uma das 27 unidades da federação). Formato pedido pela Logística, igual ao campo `origem` que ela propôs para o `pedido_criado` (P-05) |
| `criadoPor` | objeto | `empresaId` e `usuarioId` de quem criou |
| `criadoEm` | data e hora | Momento da criação |

Exemplo: [`exemplos/fornecimento_criado.json`](contratos/exemplos/fornecimento_criado.json)

Preço e quantidade podem ser zero (resposta do professor). A oferta com disponível zero não aparece para os compradores na API, mas o evento sai normalmente.

Na versão 1.0 deste contrato, `origem` era texto livre. A mudança para objeto é incompatível, mas nenhum grupo consumia o evento ainda.

### 2.3.1 `fornecimento_atualizado`

- **Produtor:** `fornecimentos-service`. **Chave:** `fornecimentoId`. **Consumidor proposto:** `mercado-service`.
- **Quando:** o fornecedor muda o preço, repõe quantidade ou encerra a oferta (`PATCH /api/v1/fornecimentos/{id}`). O novo preço vale para todo o estoque da oferta, como explicou o professor.
- **Conteúdo:** os mesmos campos do `fornecimento_criado`, com o estado depois da alteração, trocando `criadoPor`/`criadoEm` por `atualizadoPor`/`atualizadoEm`. Schema: [`fornecimento_atualizado.schema.json`](contratos/schemas/fornecimento_atualizado.schema.json); exemplo: [`exemplos/fornecimento_atualizado.json`](contratos/exemplos/fornecimento_atualizado.json).
- **Tópico:** não existe no kit (P-37). Pedido à Infraestrutura.

### 2.4 `estoque_atualizado`

- **Produtor:** `fornecimentos-service`. **Chave:** `fornecimentoId`. **Consumidor (kit):** `mercado-service`.
- **Quando:** sempre que o estoque de um fornecimento muda (RF-15).
- **Schema:** [`estoque_atualizado.schema.json`](contratos/schemas/estoque_atualizado.schema.json)

| Campo | Tipo | Descrição |
|---|---|---|
| `fornecimentoId`, `produtoId`, `fornecedorId` | texto | Identificação da oferta |
| `operacao` | `RESERVA`, `LIBERACAO`, `BAIXA`, `REPOSICAO` ou `ENCERRAMENTO` | `RESERVA`: pedido criado. `LIBERACAO`: pedido cancelado. `BAIXA`: venda concluída. `REPOSICAO`: o fornecedor repôs quantidade. `ENCERRAMENTO`: o fornecedor encerrou a oferta e o disponível foi zerado; a quantidade reservada continua |
| `quantidadeMovimentada` | número | Quanto a operação movimentou |
| `quantidadeDisponivel` | número | Saldo disponível **depois** da operação, nunca negativo |
| `quantidadeReservada` | número | Saldo reservado **depois** da operação |
| `pedidoId` | texto ou nulo | Pedido que causou a mudança; nulo em `REPOSICAO` e `ENCERRAMENTO` |
| `atualizadoEm` | data e hora | Momento da mudança |

O evento traz o saldo completo, e não só a diferença. Assim, quem consome não precisa somar movimentos e não fica com saldo errado se perder um evento.

```json
{
  "eventId": "c2b1a098-7f6e-4d5c-8b4a-39281706f5e4",
  "eventType": "estoque_atualizado",
  "eventVersion": "1.0",
  "timestamp": "2026-10-26T14:10:00.000Z",
  "source": "fornecimentos-service",
  "correlationId": "b7c6d5e4-f3a2-4b1c-9d0e-8f7a6b5c4d3e",
  "aggregateId": "forn-55",
  "payload": {
    "fornecimentoId": "forn-55",
    "produtoId": "prod-1",
    "fornecedorId": "emp-34",
    "operacao": "RESERVA",
    "quantidadeMovimentada": 3000,
    "quantidadeDisponivel": 12000,
    "quantidadeReservada": 3000,
    "pedidoId": "ped-998811",
    "atualizadoEm": "2026-10-26T14:10:00.000Z"
  }
}
```

### 2.5 `reserva_estoque_recusada` (proposta)

O kit não tem tópico para avisar Pedidos quando a reserva falha (P-16). A proposta é este evento, com chave `pedidoId`, para que o `pedidos-service` o processe na ordem dos outros eventos do mesmo pedido.

| Campo | Tipo | Descrição |
|---|---|---|
| `pedidoId`, `fornecimentoId` | texto | Pedido e oferta envolvidos |
| `quantidadeSolicitada` | número | Quanto o pedido pediu |
| `quantidadeDisponivel` | número ou nulo | Quanto havia disponível. Nulo se o fornecimento não existe |
| `motivo` | `ESTOQUE_INSUFICIENTE` ou `FORNECIMENTO_INEXISTENTE` | Causa da recusa |
| `recusadoEm` | data e hora | Momento da recusa |

Schema: [`reserva_estoque_recusada.schema.json`](contratos/schemas/reserva_estoque_recusada.schema.json)

---

## 3. Eventos que consumimos

### 3.1 `pedido_criado` (do `pedidos-service`)

O schema [`pedido_criado.schema.json`](contratos/schemas/pedido_criado.schema.json) lista só os campos que a reserva usa. Outros campos são aceitos e ignorados.

| Campo | Obrigatório para nós | Situação no exemplo do guia do kit |
|---|---|---|
| `pedidoId` | Sim | Presente |
| `fornecimentoId` | **Sim** | **Ausente.** Sem ele não sabemos de qual oferta reservar quando o fornecedor tem mais de uma do mesmo produto (P-02, P-20) |
| `produtoId` | Sim | Presente |
| `fornecedorId` | Sim | Presente |
| `quantidade` | Sim | Presente |
| `status` | Sim | Presente |
| `negociacaoId`, `compradorId`, `valorTotal` | Não | Presentes. O `compradorId` pode vir `null` ou ausente: segundo o professor, o pedido é criado na abertura do leilão e o comprador só é definido quando ele fecha |

Validamos o exemplo do guia do kit contra este schema, e ele é rejeitado justamente por faltar `fornecimentoId`.

### 3.2 `pedido_atualizado` (do `pedidos-service`)

Precisamos de `pedidoId`, `fornecimentoId` e `status`. Schema: [`pedido_atualizado.schema.json`](contratos/schemas/pedido_atualizado.schema.json)

| `status` | O que o `fornecimentos-service` faz |
|---|---|
| `CANCELADO` (proposta, a confirmar com o grupo de Pedidos) | Devolve a quantidade reservada para a disponível e publica `estoque_atualizado` com `LIBERACAO`. Se ainda não houver reserva, registra o cancelamento para que um `pedido_criado` posterior não reserve |
| `VENDA_CONCLUIDA` (proposta, a confirmar com o grupo de Pedidos) | Retira a quantidade reservada do estoque e publica `estoque_atualizado` com `BAIXA` |
| Qualquer outro | Registra no log e ignora |

Os valores `CANCELADO` e `VENDA_CONCLUIDA` são a proposta do grupo, usada na ESP-FRN-001. Se o grupo de Pedidos definir outros, o contrato e a ESP mudam de versão.

A Logística também usa `CANCELADO` e sugeriu ao grupo de Pedidos publicar `VENDA_CONCLUIDA` quando receber o evento `entrega_concluida` da Logística, se a venda for concluída na entrega. Isso fecha o momento da baixa de estoque, que ainda depende do grupo de Pedidos.

### 3.3 `produto_cadastrado` (do nosso `produtos-service`)

O `fornecimentos-service` grava o produto na tabela local `produto_referencia` (ADR-011), com `nome`, `unidade` e `tipoTransporte`. Também consome `produto_atualizado` (atualiza a cópia se o evento for mais novo que o último aplicado) e `produto_excluido` (desativa a cópia; o cadastro de oferta desse produto passa a ser recusado).

### 3.3.1 `fornecimento_criado` (do nosso `fornecimentos-service`)

O `produtos-service` consome `fornecimento_criado` e marca o produto como movimentado. A partir daí, o produto não pode mais ser alterado nem excluído. Mensagem inválida vai para `produtos.dlt`.

### 3.4 `empresa_cadastrada` (do serviço de Autenticação)

Conteúdo definido pelo grupo de Autenticação. Em 10/11/2026 (issue #2), o grupo respondeu que o `payload` passaria para `camelCase`. O código publicado não seguiu essa resposta, e em 18/11/2026 o grupo confirmou no próprio repositório que o formato oficial é outro (issue #28; [`Matheus-Allvz/Identity-Service`](https://github.com/Matheus-Allvz/Identity-Service), commit `3cc4cce`, `Docs/Alinhamento-Ecossistema-B2B.md`, seção 3.5):

- **Corpo:** o objeto da empresa direto na mensagem, em `snake_case`, **sem** o envelope do kit (`eventType`, `eventVersion`, `payload` etc.).
- **Chave:** o `tenant_id`, UUID com hífens.
- **Cabeçalhos do Kafka:** `event_id`, `tenant_id`, `group_id`, `initiator_user_id`, `actor_user_id` (só quando um operador age em nome do usuário), `acting_scope`, `correlation_id` e `context_jws` (assinatura RS256 que pode ser conferida com o JWKS).

| Campo do corpo | Descrição |
|---|---|
| `event_id` | Identificador do evento (UUID) |
| `tenant_id`, `group_id` | Empresa e grupo econômico (UUID) |
| `cnpj`, `legal_name` | Dados cadastrais |
| `branch_type` | `HQ` (matriz) ou `BRANCH` (filial) |
| `geo_lat`, `geo_lng` | Localização |
| `status` | Situação da empresa (`ACTIVE` no cadastro) |
| `scopes` | Escopos habilitados: `BUYER`, `SUPPLIER`, `CARRIER`, `TENANT_ADMIN` |
| `created_at` | Data e hora do cadastro (ISO 8601) |

Quem consome com a biblioteca comum do kit, que espera o envelope, precisa ler o corpo direto e tirar `eventId` e `correlationId` dos cabeçalhos. O grupo de Autenticação recomenda isso no mesmo documento.

O `fornecimentos-service` não consome este evento na versão 1.1 da ESP-FRN-001, porque o escopo ativo já vem no token (`active_scope`). O campo `empresaId` dos nossos eventos recebe o valor do claim `tenant_id`.

---

## 4. Tópicos de falha

Depois de 3 tentativas com espera de 1, 2 e 4 segundos, a mensagem vai para `produtos.dlt` ou `fornecimentos.dlt`. O envelope segue o padrão do kit, com `eventType` igual ao nome do tópico de falha e o `payload` abaixo (formato da biblioteca comum do kit, `services/common/consumer.py`):

| Campo | Descrição |
|---|---|
| `originalEvent` | Evento original, completo |
| `error` | Mensagem do erro |
| `stackTrace` | Pilha de chamadas do erro |
| `failedAtAttempt` | Número da tentativa em que falhou |

---

## 5. O que pedimos a cada grupo

| Grupo | Pedido |
|---|---|
| Mercado, Negociação/Leilão e Pedidos | Incluir `fornecimentoId` em `pedido_criado` e `pedido_atualizado`. Informar os valores de `status` de cancelamento e de venda concluída. Avaliar a proposta de `reserva_estoque_recusada`. Para a Logística: copiar `tipoTransporte` do produto e `origem` do fornecimento para o `pedido_criado`, e calcular `pesoKg` (`quantidade` em `KG`; `quantidade × 1000` em `TON`; `quantidade × pesoUnitarioKg` nas demais unidades, quando o peso unitário estiver informado) |
| Infraestrutura | Criar, com 3 partições, os tópicos `produto_atualizado`, `produto_excluido`, `fornecimento_atualizado` e `reserva_estoque_recusada`, ou combinar alternativa. Incluir o `fornecimentos-service` como consumidor de `pedido_criado`, `pedido_atualizado`, `produto_atualizado` e `produto_excluido`, e o `produtos-service` como consumidor de `fornecimento_criado`, no `CONTRACTS.md` |
| Autenticação | Respondido em 09/11 e 10/11/2026 (issue #2) e em 18/11/2026 (issues #27, #28, #29 e #31): conteúdo de `empresa_cadastrada`, em `snake_case` sem envelope; cadastro de produto só por `SUPPLIER`. Em aberto: padrão único dos campos de erro (P-34) e administrador da plataforma (P-07) |
| Compra e Demanda, Mercado | Revisar os campos de `produto_cadastrado`, `produto_atualizado`, `produto_excluido`, `fornecimento_criado`, `fornecimento_atualizado` e `estoque_atualizado`. A categoria passou a ser lista fixa |
| Logística/Transporte | Respondido em 10/11/2026: listas confirmadas (P-06), tipo de transporte pelo `pedido_criado` (P-27), origem em cidade e UF (P-05) e peso unitário opcional atendidos na versão 1.1 |

---

## 6. Histórico

| Versão | Data | Mudança |
|---|---|---|
| 1.0 | 26/10/2026 | Primeira proposta |
| 1.1 | 10/11/2026 | `pesoUnitarioKg` em `produto_cadastrado` e `produto_atualizado`; `origem` de `fornecimento_criado` como objeto com `cidade` e `uf`; listas de unidade e tipo de transporte confirmadas. Motivo: resposta do grupo de Logística/Transporte |
| 1.2 | 10/11/2026 | `empresa_cadastrada` em camelCase (`tenantId`, `groupId`, `legalName`, `branchType`, `geoLat`, `geoLng`), conforme a resposta do grupo de Autenticação na issue #2 |
| 1.3 | 12/11/2026 | `compradorId` do `pedido_criado` pode ser `null`, porque o pedido passa a ser criado na abertura do leilão (resposta do professor) |
| 2.0 | 16/11/2026 | Respostas do professor em aula: categoria em lista fixa; `produto_atualizado` e `produto_excluido` passam a ser publicados; `fornecimento_atualizado` novo; operações `REPOSICAO` e `ENCERRAMENTO` no `estoque_atualizado`; preço e quantidade podem ser zero; `produtos-service` passa a consumir `fornecimento_criado`. **Mudança incompatível:** `categoria` fora da lista é recusada |
| 2.1 | 18/11/2026 | `empresa_cadastrada` (seção 3.4) corrigido para o formato que o grupo de Autenticação publica: corpo em `snake_case` sem envelope, metadados nos cabeçalhos do Kafka, campos `event_id` e `created_at`. Não muda nenhum evento nosso (issue #28) |
