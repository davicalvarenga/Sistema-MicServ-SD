# Contrato de Eventos

**Grupo:** Fornecimento e Produtos (`produtos-service` e `fornecimentos-service`)
**Versão:** 2.6 (proposta para revisão dos grupos que integram com a gente)
**Data:** 26/11/2026 (versão 1.0: 26/10/2026)

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
| Datas | ISO-8601 em UTC com milissegundos (ex.: `2026-10-26T14:00:00.123Z`), no `timestamp` do envelope e nos campos de instante do `payload`. Os consumidores comparam esses instantes para descartar eventos antigos: sem a fração, duas mudanças no mesmo segundo empatam e a segunda se perde. Os schemas aceitam o instante com ou sem fração | Kit; teste com o `mercado-service` (26/11/2026) |
| `correlationId` | Texto não vazio, **não necessariamente UUID**: o gateway do kit repassa o `X-Correlation-Id` do cliente e, se ele não vier, usa o `$request_id` do Nginx (32 caracteres hexadecimais) | Kit, `gateway/nginx.conf` |
| Identificação de quem agiu | Objeto com `empresaId` e `usuarioId`. **Nenhum evento leva token de acesso** | RNF-09 |
| Campos desconhecidos | Os nossos consumidores ignoram campos que não conhecem. Os nossos eventos só aceitam os campos definidos no schema | Grupo |
| Evolução | Adicionar campo opcional mantém a `eventVersion`. Remover, renomear ou mudar o tipo de um campo exige nova `eventVersion` e aviso aos consumidores. É o que mantém a compatibilidade `BACKWARD` configurada no Schema Registry do kit | Kit, grupo |
| Idempotência | Os consumidores usam o `eventId` para ignorar eventos repetidos (tabela `processed_events`) | Kit, RNF-06 |

**Por que os schemas não usam `multipleOf: 0.01`:** testamos e, em ponto flutuante, `0.07 / 0.01` dá `7.000000000000001`. Com essa regra, preços válidos como 0,07, 1,15 e 1.234.567,89 seriam rejeitados. A precisão de 2 casas é validada no código do serviço.

---

## 2. Eventos que publicamos

### 2.1 `produto_cadastrado`

- **Produtor:** `produtos-service`. **Chave:** `produtoId`. **Consumidores (kit):** `fornecimentos-service`, `demanda-service`, `mercado-service`. Também consome: `pedidos-service` (issue #1). O grupo de Logística/Transporte não consome este evento: recebe o tipo de transporte pelo `pedido_criado`, que o grupo de Pedidos preenche a partir do produto. Se o grupo de Pedidos não puder incluir o campo, o plano B da Logística é consumir `produto_cadastrado` e `produto_atualizado` e guardar uma cópia local (resposta da Logística, 10/11/2026).
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

- **Produtor:** `produtos-service`. **Chave:** `produtoId`. **Consumidores:** `fornecimentos-service` (cópia local) consome os dois. `mercado-service` (ESP-MRC-001, INT-MRC-05) e `pedidos-service` (issue #1) consomem só o `produto_atualizado`; o Mercado declarou que não consome o `produto_excluido`. `demanda-service`, se quiser manter cópia.
- **Quando:** a empresa que cadastrou o produto o altera ou exclui. Só é permitido enquanto o produto não tem movimentação, isto é, nenhum fornecimento (resposta do professor). Mudança de especificação de produto com movimentação é um produto novo.
- **Tópicos:** o kit ainda não tem esses tópicos (P-26). O Redpanda do kit, em modo `dev-container`, os cria na primeira publicação com 1 partição; a criação com 3 partições foi pedida à Infraestrutura.


- `produto_atualizado` leva o estado completo do produto depois da alteração (mesmos campos do cadastro, com `atualizadoPor` e `atualizadoEm`). Schema: [`produto_atualizado.schema.json`](contratos/schemas/produto_atualizado.schema.json)
- `produto_excluido` leva `produtoId`, `excluidoPor` e `excluidoEm`. Schema: [`produto_excluido.schema.json`](contratos/schemas/produto_excluido.schema.json)

Como cada tópico só garante ordem dentro dele mesmo, quem consome deve comparar o `timestamp` do evento com o do último evento aplicado ao produto e descartar eventos mais antigos.

### 2.3 `fornecimento_criado`

- **Produtor:** `fornecimentos-service`. **Chave:** `fornecimentoId`. **Consumidor (kit):** `mercado-service`. Também consomem: `pedidos-service` (issue #1) e o nosso `produtos-service` (seção 3.3.1). A Negociação/Leilão não consome os nossos eventos: recebe os dados da oferta pelos eventos do Mercado (decisão D39 da ESP-NEG-001).
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
| `grupoId` | texto ou nulo | Grupo econômico do fornecedor, do claim `group_id` do token. Nulo quando o token não traz o grupo. Pedido na análise do grupo de Autenticação para uma trava de auto-negociação por grupo econômico (issue #35). Na v1, nenhum consumidor usa o campo: o Mercado o aceita e ignora (DG-54 da ESP-MRC-001), e a Negociação/Leilão não consome este evento. Fica disponível para uso futuro. Opcional: consumidores antigos podem ignorar |

Exemplo: [`exemplos/fornecimento_criado.json`](contratos/exemplos/fornecimento_criado.json)

Preço e quantidade podem ser zero (resposta do professor). A oferta com disponível zero não aparece para os compradores na API, mas o evento sai normalmente.

Na versão 1.0 deste contrato, `origem` era texto livre. A mudança para objeto é incompatível, mas nenhum grupo consumia o evento ainda.

### 2.3.1 `fornecimento_atualizado`

- **Produtor:** `fornecimentos-service`. **Chave:** `fornecimentoId`. **Consumidor:** `mercado-service` (ESP-MRC-001, INT-MRC-05).
- **Quando:** o fornecedor muda o preço, repõe quantidade ou encerra a oferta (`PATCH /api/v1/fornecimentos/{id}`). O novo preço vale para todo o estoque da oferta, como explicou o professor.
- **Conteúdo:** os mesmos campos do `fornecimento_criado`, com o estado depois da alteração, trocando `criadoPor`/`criadoEm` por `atualizadoPor`/`atualizadoEm`. Schema: [`fornecimento_atualizado.schema.json`](contratos/schemas/fornecimento_atualizado.schema.json); exemplo: [`exemplos/fornecimento_atualizado.json`](contratos/exemplos/fornecimento_atualizado.json).
- **Tópico:** não existe no kit (P-37). Pedido à Infraestrutura.

### 2.4 `estoque_atualizado`

- **Produtor:** `fornecimentos-service`. **Chave:** `fornecimentoId`. **Consumidores:** `mercado-service` (kit) e `pedidos-service` (confirma a reserva pelo `RESERVA` com o `pedidoId`; issue #1).
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
    "pedidoId": "4f1c2b3a-9d8e-4c7b-a6f5-1e2d3c4b5a69",
    "atualizadoEm": "2026-10-26T14:10:00.000Z"
  }
}
```

### 2.5 `reserva_estoque_recusada`

O kit não tem tópico para avisar Pedidos quando a reserva falha (P-16). O grupo propôs este evento, e o grupo de Pedidos o aceitou em 19/11/2026 (issue #1): ao recebê-lo, o `pedidos-service` cancela o pedido com o motivo recebido. O tópico ainda precisa ser criado no kit (issue #12). O evento usa a chave `pedidoId`, para que o `pedidos-service` o processe na ordem dos outros eventos do mesmo pedido.

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

**Resposta do grupo de Pedidos (19/11/2026, issue #1):** o `pedido_criado` da ESP-PED-001 v2.1 leva `fornecimentoId` e nasce com `compradorId` nulo. Um leilão conjunto gera um pedido por oferta. Validamos os exemplos de `pedido_criado` e `pedido_atualizado` publicados por eles (`docs/pedidos/contratos/`, commit `8091833`) contra os nossos schemas, e todos passam.

### 3.2 `pedido_atualizado` (do `pedidos-service`)

Precisamos de `pedidoId`, `fornecimentoId` e `status`. Schema: [`pedido_atualizado.schema.json`](contratos/schemas/pedido_atualizado.schema.json)

| `status` | O que o `fornecimentos-service` faz |
|---|---|
| `CANCELADO` | Devolve a quantidade reservada para a disponível e publica `estoque_atualizado` com `LIBERACAO`. Se ainda não houver reserva, registra o cancelamento para que um `pedido_criado` posterior não reserve |
| `VENDA_CONCLUIDA` | Retira a quantidade reservada do estoque e publica `estoque_atualizado` com `BAIXA` |
| Qualquer outro | Registra no log e ignora |

Os valores `CANCELADO` e `VENDA_CONCLUIDA` foram confirmados pelo grupo de Pedidos em 19/11/2026 (issue #1). Segundo eles, a venda é concluída no fechamento da negociação, e não na entrega, e cada pedido recebe `VENDA_CONCLUIDA` uma única vez. Os outros status que eles publicam (por exemplo, `ENTREGUE`) caem na linha "Qualquer outro".

**Repetições e ordem de chegada:**
- Evento republicado com o mesmo `eventId` é ignorado (`processed_events`).
- A baixa e a liberação só acontecem com a reserva na situação `RESERVADA`, que muda para `BAIXADA` ou `LIBERADA`. Um segundo `VENDA_CONCLUIDA` ou `CANCELADO` do mesmo pedido e fornecimento, mesmo com outro `eventId`, não altera o estoque (ESP-FRN-001, RN-16).
- `pedido_criado` e `pedido_atualizado` estão em tópicos diferentes, então um `CANCELADO` pode chegar antes do `pedido_criado`. Nesse caso, o cancelamento fica registrado, e o `pedido_criado` que chegar depois não reserva.

### 3.3 `produto_cadastrado` (do nosso `produtos-service`)

O `fornecimentos-service` grava o produto na tabela local `produto_referencia` (ADR-011), com `nome`, `unidade` e `tipoTransporte`. Também consome `produto_atualizado` (atualiza a cópia se o evento for mais novo que o último aplicado) e `produto_excluido` (desativa a cópia; o cadastro de oferta desse produto passa a ser recusado).

### 3.3.1 `fornecimento_criado` (do nosso `fornecimentos-service`)

O `produtos-service` consome `fornecimento_criado` e marca o produto como movimentado. A partir daí, o produto não pode mais ser alterado nem excluído. Mensagem inválida vai para `produtos.dlt`.

### 3.4 `empresa_cadastrada` (do serviço de Autenticação)

Conteúdo definido pelo grupo de Autenticação, que mudou o formato três vezes (issue #28):

| Data | Formato | Fonte |
|---|---|---|
| 10/11/2026 | Envelope do kit com `payload` em `camelCase` (resposta na issue #2) | Resposta; o código não seguiu |
| 18/11/2026, manhã | Corpo direto, em `snake_case`, sem envelope | Commit `3cc4cce` |
| 18/11/2026, 09h27 (horário de Brasília) | Formato atual, descrito abaixo | PR #25 do grupo, commit `b0dfaa7`, `src/IdentityService/Modules/M14Eventos/EventOutbox.cs` |

Formato atual ([`Matheus-Allvz/Identity-Service`](https://github.com/Matheus-Allvz/Identity-Service), commit `b0dfaa7`):

- **Envelope do kit:** `eventId`, `eventType` (`empresa_cadastrada`), `eventVersion` (`1.0`), `timestamp`, `source` (`identity-service`), `correlationId`, `aggregateId` (o `tenantId`) e `payload`.
- **`payload`:** os campos da tabela abaixo em `camelCase` e, de novo, em `snake_case` (`event_id`, `tenant_id`, `group_id`, `legal_name`, `branch_type`, `geo_lat`, `geo_lng`, `created_at`; `cnpj`, `status` e `scopes` têm o mesmo nome nos dois).
- **Raiz da mensagem:** todos os campos do `payload` também são copiados para fora do envelope, nos dois formatos de nome.
- **Chave:** o `tenantId`, UUID com hífens.
- **Cabeçalhos do Kafka:** `event_id`, `tenant_id`, `group_id`, `initiator_user_id`, `actor_user_id` (só quando um operador age em nome do usuário), `acting_scope`, `correlation_id` e `context_jws` (assinatura RS256 que pode ser conferida com o JWKS).

| Campo do `payload` (`camelCase`) | Descrição |
|---|---|
| `tenantId`, `groupId` | Empresa e grupo econômico (UUID) |
| `cnpj`, `legalName` | Dados cadastrais |
| `branchType` | `HQ` (matriz) ou `BRANCH` (filial) |
| `geoLat`, `geoLng` | Localização |
| `status` | Situação da empresa (`ACTIVE` no cadastro) |
| `scopes` | Escopos habilitados: `BUYER`, `SUPPLIER`, `CARRIER`, `TENANT_ADMIN` |
| `createdAt` | Data e hora do cadastro |

Pontos a confirmar com o grupo de Autenticação (issue #28):
- **Campos repetidos:** os mesmos dados aparecem em três lugares e com dois formatos de nome. Recomendamos ler só o `payload` em `camelCase`, que é o padrão do kit e dos nossos eventos.
- **Formato da data:** `timestamp` e `createdAt` saem no formato padrão do .NET, por exemplo `2026-11-18T12:00:00.0000000+00:00`, e não no formato terminado em `Z` dos demais eventos do kit (por exemplo `2026-11-18T12:00:00Z`). Um consumidor que compare o texto ou use um parser estrito pode recusar a mensagem.

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
| Mercado, Negociação/Leilão e Pedidos | Respondido em 19/11/2026 (issue #1, ESP-PED-001 v2.1): `fornecimentoId` em `pedido_criado` e `pedido_atualizado`, status `CANCELADO` e `VENDA_CONCLUIDA`, aceite de `reserva_estoque_recusada`, e cópia de `tipoTransporte`, `pesoUnitarioKg` e `origem` com cálculo do `pesoKg` para a Logística |
| Infraestrutura | Criar, com 3 partições, os tópicos `produto_atualizado`, `produto_excluido`, `fornecimento_atualizado` e `reserva_estoque_recusada`, ou combinar alternativa. Incluir o `fornecimentos-service` como consumidor de `pedido_criado`, `pedido_atualizado`, `produto_atualizado` e `produto_excluido`, e o `produtos-service` como consumidor de `fornecimento_criado`, no `CONTRACTS.md` |
| Autenticação | Respondido em 09/11 e 10/11/2026 (issue #2) e em 18/11/2026 (issues #28, #29 e #31): conteúdo de `empresa_cadastrada`, no envelope do kit desde o commit `b0dfaa7` (seção 3.4). Escopos de cadastro de produto (`SUPPLIER` e `BUYER`) corrigidos por eles em 19/11/2026 (issue #27). Em aberto: padrão único dos campos de erro (P-34) e administrador da plataforma (P-07) |
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
| 2.2 | 18/11/2026 | Campo opcional `grupoId` no `fornecimento_criado`, pedido na análise do grupo de Autenticação (issue #35). Mudança compatível |
| 2.3 | 18/11/2026 | `empresa_cadastrada` (seção 3.4) atualizado para o formato publicado pelo grupo de Autenticação a partir do commit `b0dfaa7`: envelope do kit, `payload` em `camelCase` com cópia em `snake_case` e cópia dos campos na raiz. Não muda nenhum evento nosso (issue #28) |
| 2.4 | 19/11/2026 | Resposta do grupo de Pedidos (issue #1): `CANCELADO`, `VENDA_CONCLUIDA` e `reserva_estoque_recusada` deixam de ser proposta; regras de repetição e de ordem de chegada do `pedido_atualizado` explicitadas; `pedidoId` dos exemplos em UUID, como o `pedidos-service` gera, e `compradorId` nulo no exemplo de `pedido_criado`. Nenhum schema muda |
| 2.5 | 23/11/2026 | Consumidores atualizados a partir das especificações do grupo de Mercado, Negociação/Leilão e Pedidos: `pedidos-service` consome `produto_cadastrado`, `produto_atualizado`, `fornecimento_criado`, `estoque_atualizado` e `reserva_estoque_recusada`; `mercado-service` confirmado em `fornecimento_atualizado` e `produto_atualizado`; a Negociação/Leilão não consome os nossos eventos. Uso do `grupoId` na v1: nenhum (DG-54 do Mercado). Nenhum schema muda |
| 2.6 | 26/11/2026 | Instantes dos eventos com milissegundos (seção 1). No teste no kit com o `mercado-service`, a liberação de uma reserva, a reposição e a mudança de preço publicadas no mesmo segundo chegaram com o mesmo instante, e o Mercado, que só aplica instante maior que o último, ficou com o estoque antigo (100 em vez de 120). Corrigido nos dois serviços (ESP-PRD-001 2.4, ESP-FRN-001 2.3). Nenhum schema muda |
