# ESP-FRN-001 — Especificação de Requisitos: Serviço de Fornecimentos

## 0. Metadados

| Campo | Valor |
|---|---|
| Identificador | ESP-FRN-001 |
| Versão | 1.0 |
| Status | Rascunho |
| Serviço / Bounded context | Microsserviço 3, Fornecimentos (`fornecimentos-service`, Portal B2B Distribuído) |
| Autores (PO / Dev / QA) | Grupo de Fornecimento e Produtos: Daniel Carvalho Coutinho, Davi Coelho de Alvarenga, Gabriel Vicentte dos Santos Ferreira, Rafael de Castro Noleto. QA: Grupo de Teste |
| Data | 2026-10-26 |
| Documentos relacionados | Diagrama "Arquitetura do Portal B2B Distribuído" (professor); Kit de integração da Infraestrutura (`Printf-PedroCardoso/portal-b2b-kit-infra`, commit `630515c`); Documento de Requisitos do grupo v0.4; Contrato de Eventos v1.0; Proposta de DDL (`docs/banco/`); ESP-PRD-001 (Produtos) |

## 1. Diretivas para a LLM geradora

1. Implemente **exatamente** o que está especificado. Não adicione endpoints, campos, tópicos, perfis ou regras que não estejam neste documento.
2. **Ordem de precedência** quando houver conflito aparente: Catálogo de erros (§10) e Contratos (§7) > Critérios de aceitação (§8) > Regras de negócio (§9) > Requisitos funcionais (§8) > texto descritivo.
3. Nomes de campos, tópicos, códigos de erro, rotas e valores de enumeração são **literais**: use-os byte a byte, com a mesma grafia e caixa.
4. Quando algo não estiver definido, escolha o comportamento mais simples que **não viole** nenhum item deste documento e registre a decisão em um comentário `# DECISÃO:` no código.
5. Entregue código completo e executável. Proibido: `TODO`, `pass` como implementação, pseudocódigo, trechos omitidos ("...").
6. Formato da resposta: os arquivos da estrutura do §5, cada um com caminho relativo e conteúdo completo. Na resposta final, liste os caminhos relativos.

## 2. Contexto

### 2.1 Objetivo do serviço
Manter as ofertas (fornecimentos) que os fornecedores colocam no portal e controlar o estoque de cada oferta: reservar quando um pedido é criado, devolver quando o pedido é cancelado e dar baixa quando a venda é concluída.

### 2.2 Posição na arquitetura
O fornecedor cria a oferta pela API REST (via gateway), e o serviço publica `fornecimento_criado`, que alimenta o motor de matching de Mercado (passo 1 do fluxo principal). O serviço mantém uma cópia local dos produtos a partir de `produto_cadastrado`. Quando Pedidos cria um pedido (passo 7), o serviço reserva o estoque; quando o pedido é cancelado ou a venda é concluída, libera ou dá baixa. Cada mudança de estoque gera `estoque_atualizado`.

```text
produtos-service ──[produto_cadastrado]──┐
pedidos-service ───[pedido_criado]───────┼──► fornecimentos-service ──[fornecimento_criado]─────► mercado-service
pedidos-service ───[pedido_atualizado]───┘          │      ▲         ──[estoque_atualizado]──────► mercado-service
Front-end ─► Gateway ─REST───────────────────────────┘      │         ──[reserva_estoque_recusada]► pedidos-service
                                                            │         ──[fornecimentos.dlt]───────► (operação)
```

## 3. Escopo

### 3.1 Dentro do escopo
- Cadastro de fornecimento (oferta) por empresas com perfil `fornecedor`.
- Consulta e listagem paginada de fornecimentos, com filtro opcional por produto.
- Cópia local dos produtos a partir do evento `produto_cadastrado`.
- Reserva de estoque a partir de `pedido_criado`; liberação e baixa a partir de `pedido_atualizado`.
- Publicação de `fornecimento_criado`, `estoque_atualizado`, `reserva_estoque_recusada` e `fornecimentos.dlt`.
- Autenticação por JWT, autorização por perfil e propagação do `X-Correlation-Id`.
- Endpoints técnicos `/health`, `/health/ready` e `/metrics`.

### 3.2 Fora do escopo (não implementar)
- Alteração, reposição de quantidade e encerramento de fornecimento (aguardam a P-11 do Documento de Requisitos).
- Endpoint REST de baixa ou ajuste de estoque. O estoque muda só pelos eventos de pedido (ADR-022 do Relatório Técnico).
- Consumo de `empresa_cadastrada` (conteúdo não definido, P-12) e de eventos de alteração ou exclusão de produto (P-26).
- Comparação entre `fornecedorId`/`produtoId` do pedido e os dados do fornecimento.
- Emissão de tokens e cadastro de empresas (serviço `usuarios-service`).
- Novas tentativas (*retry*) com espera em falhas transitórias: responsabilidade do adaptador de consumo.
- Implementação concreta das portas: banco PostgreSQL, cliente Kafka, publicador de outbox.

## 4. Glossário

| Termo | Definição precisa |
|---|---|
| Fornecimento | Oferta de um produto por um fornecedor, identificada por `fornecimento_id`, com preço, quantidades e origem. |
| Quantidade disponível | Parte do estoque que pode ser reservada. Nunca negativa. |
| Quantidade reservada | Parte do estoque bloqueada por pedidos em andamento. Nunca negativa. |
| Reserva | Registro de quanto um pedido (`pedido_id`) bloqueou de um fornecimento, com uma situação (§6.2). |
| Produto de referência | Cópia local de um produto, criada a partir de `produto_cadastrado`. Um fornecimento só pode referenciar um produto de referência existente. |
| Valor decimal | Número com no máximo 2 casas decimais, entre 0 e 9999999999.99. Em JSON é **número** (não string). Internamente, toda aritmética e comparação usa `decimal.Decimal`, obtido com `Decimal(str(valor))`; proibido calcular com `float`. Na saída, o `Decimal` é convertido com `float()` e serializado como número JSON. |
| Instante | Data/hora em UTC no formato ISO-8601 com sufixo `Z` e sem frações de segundo (ex.: `"2026-10-26T14:00:00Z"`). |
| Agora | Valor retornado por `clock.now()` (porta Clock). O serviço nunca usa o relógio do sistema. |
| Texto preenchido | String que, depois de `strip()`, tem pelo menos 1 caractere. |
| Perfil | Valor do claim `perfil` do token. Um de: `comprador`, `fornecedor`, `transportadora`, `admin`. |
| Token | JWT assinado com HS256 e a chave `jwt_secret` recebida por `create_app`, enviado no cabeçalho `Authorization: Bearer <token>`. |
| Correlation id | Na API: valor do cabeçalho `X-Correlation-Id`, ou UUID4 novo se ausente ou não for texto preenchido. No consumo de eventos: o `correlationId` da mensagem recebida, ou UUID4 novo se ausente ou não for texto preenchido. |
| Status de cancelamento | Valor literal `"CANCELADO"` no `payload.status` de `pedido_atualizado`. |
| Status de venda concluída | Valor literal `"VENDA_CONCLUIDA"` no `payload.status` de `pedido_atualizado`. |

## 5. Restrições técnicas

| Item | Valor obrigatório |
|---|---|
| Linguagem / versão | Python 3.12 |
| Framework | FastAPI (com Pydantic v2, se usado) |
| Dependências permitidas | Biblioteca padrão do Python, `fastapi`, `pydantic`, `starlette`, `PyJWT` (importado como `jwt`). Nenhuma outra. |
| Persistência | Somente pela porta `RepositorioFornecimentos` (§5.1). Proibido guardar fornecimentos, reservas, produtos ou eventos processados em variáveis do módulo ou da aplicação. |
| Estrutura de arquivos | `app/__init__.py` e `app/main.py` obrigatórios; outros módulos dentro de `app/` são permitidos. |
| Ponto de entrada | `app.main.create_app(event_bus: EventBus, clock: Clock, repositorio: RepositorioFornecimentos, jwt_secret: str) -> fastapi.FastAPI` |
| Formato de data/hora | Instante (ver glossário). |
| Formato monetário | Valor decimal (ver glossário). |

### 5.1 Portas (interfaces de infraestrutura)

```python
from contextlib import AbstractContextManager
from datetime import datetime
from decimal import Decimal
from typing import Callable, Protocol


class EventBus(Protocol):
    def publish(self, topic: str, key: str, message: dict) -> None: ...
    def subscribe(self, topic: str, handler: Callable[[dict], None]) -> None: ...
    def disponivel(self) -> bool: ...


class Clock(Protocol):
    def now(self) -> datetime: ...  # datetime com timezone UTC


class RepositorioFornecimentos(Protocol):
    def transacao(self) -> AbstractContextManager[None]: ...
    def evento_processado(self, event_id: str) -> bool: ...
    def registrar_evento_processado(self, event_id: str) -> None: ...
    def salvar_produto_referencia(self, produto: dict) -> None: ...
    def obter_produto_referencia(self, produto_id: str) -> dict | None: ...
    def inserir_fornecimento(self, fornecimento: dict) -> None: ...
    def obter_fornecimento(self, fornecimento_id: str) -> dict | None: ...
    def listar_fornecimentos(self, produto_id: str | None, offset: int, limite: int) -> tuple[list[dict], int]: ...
    def aplicar_movimento(self, fornecimento_id: str, delta_disponivel: Decimal,
                          delta_reservada: Decimal, atualizado_em: datetime) -> dict | None: ...
    def obter_reserva(self, pedido_id: str, fornecimento_id: str) -> dict | None: ...
    def salvar_reserva(self, reserva: dict) -> None: ...
    def disponivel(self) -> bool: ...
```

Comportamento das portas:
- `create_app` deve chamar, durante a criação da aplicação, `event_bus.subscribe` para os tópicos `produto_cadastrado`, `pedido_criado` e `pedido_atualizado`, um handler para cada.
- Cada handler recebe a mensagem completa (envelope, §7.3) como `dict` e **nunca** propaga exceção.
- `transacao()`: tudo o que é feito no repositório dentro de `with repositorio.transacao():` é gravado de forma atômica; se uma exceção sair do bloco, nada é gravado. Toda alteração feita por um handler acontece dentro de uma única transação.
- `aplicar_movimento` soma `delta_disponivel` à quantidade disponível e `delta_reservada` à quantidade reservada do fornecimento, e grava `atualizado_em`, **de forma atômica e somente se os dois saldos resultantes forem ≥ 0**. Retorna o fornecimento atualizado, ou `None` sem alterar nada se o fornecimento não existir ou se algum saldo ficaria negativo. **Toda mudança de quantidade deve usar esse método**; é proibido ler o fornecimento, calcular o saldo e gravar o resultado. Em produção, o método equivale a `UPDATE ... WHERE quantidade_disponivel + delta >= 0 AND quantidade_reservada + delta >= 0` (ADR-006 do Relatório Técnico), o que garante a regra mesmo com duas instâncias do serviço.
- `salvar_produto_referencia` e `salvar_reserva` inserem ou substituem pelo identificador (`produto_id`; par `pedido_id` + `fornecimento_id`).
- `listar_fornecimentos` devolve `(itens, total)`: no máximo `limite` itens a partir de `offset`, na ordem de `criado_em` crescente e, em empate, `fornecimento_id` crescente; `total` é o número de fornecimentos que atendem ao filtro. `produto_id=None` significa sem filtro.
- Valores de preço e quantidade circulam entre o serviço e o repositório como `Decimal`.
- `publish` é síncrono e pode, no mesmo fluxo, chamar handlers inscritos; o serviço não pode entrar em deadlock nesse caso. Ordem dentro de uma escrita: validar → gravar (dentro da transação) → publicar **depois** que a transação terminar. Falhas lançadas por `publish` estão fora do escopo (o adaptador real usa *transactional outbox*, ADR-010).
- `clock.now()` sempre retorna `datetime` com fuso; se vier sem fuso, tratar como UTC.

## 6. Modelo de domínio

### 6.1 Entidades

#### Fornecimento
| Atributo | Tipo | Obrigatório | Restrições / origem |
|---|---|---|---|
| fornecimento_id | string | Sim | UUID4 gerado pelo serviço no cadastro. |
| fornecedor_id | string | Sim | Claim `empresaId` do token. |
| produto_id | string | Sim | Corpo da requisição; precisa existir como produto de referência. |
| unidade | string | Sim | Copiada do produto de referência no cadastro. |
| preco | valor decimal | Sim | Corpo da requisição; > 0. |
| quantidade_disponivel | valor decimal | Sim | Corpo da requisição no cadastro (> 0); depois, só muda por `aplicar_movimento`; ≥ 0. |
| quantidade_reservada | valor decimal | Sim | `0` no cadastro; só muda por `aplicar_movimento`; ≥ 0. |
| origem | string | Sim | Corpo da requisição, depois de `strip()`; 1 a 255 caracteres. |
| criado_por_usuario_id | string | Sim | Claim `sub` do token. |
| criado_em | instante | Sim | `clock.now()` no cadastro. |
| atualizado_em | instante | Sim | `clock.now()` no cadastro e a cada movimento. |

#### ProdutoReferencia
| Atributo | Tipo | Obrigatório | Restrições / origem |
|---|---|---|---|
| produto_id | string | Sim | `payload.produtoId` de `produto_cadastrado`. |
| nome | string | Sim | `payload.nome`. |
| unidade | string | Sim | `payload.unidade`. |
| tipo_transporte | string | Sim | `payload.tipoTransporte`. |
| ativo | booleano | Sim | `True` na criação. |
| versao_evento | instante | Sim | `timestamp` do envelope do evento aplicado. |

#### Reserva
| Atributo | Tipo | Obrigatório | Restrições / origem |
|---|---|---|---|
| pedido_id | string | Sim | `payload.pedidoId` do evento. |
| fornecimento_id | string | Sim | `payload.fornecimentoId` do evento. |
| quantidade | valor decimal | Sim | `payload.quantidade` de `pedido_criado`; `0` na situação `CANCELADA_SEM_RESERVA`. |
| situacao | enum | Sim | `RESERVADA`, `LIBERADA`, `BAIXADA` ou `CANCELADA_SEM_RESERVA`. |
| criado_em | instante | Sim | `clock.now()` na criação. |
| atualizado_em | instante | Sim | `clock.now()` a cada mudança de situação. |

### 6.2 Estados e transições

Estados da reserva de um par (`pedido_id`, `fornecimento_id`):

| Estado atual | Evento / comando | Condição | Próximo estado | Efeito no fornecimento e publicação |
|---|---|---|---|---|
| (inexistente) | `pedido_criado` válido | fornecimento existe e `quantidade_disponivel ≥ quantidade` | RESERVADA | disponível −q, reservada +q; publica `estoque_atualizado` com `RESERVA` |
| (inexistente) | `pedido_criado` válido | fornecimento existe e `quantidade_disponivel < quantidade` | (inexistente) | nenhum; publica `reserva_estoque_recusada` com `ESTOQUE_INSUFICIENTE` |
| (inexistente) | `pedido_criado` válido | fornecimento não existe | (inexistente) | nenhum; publica `reserva_estoque_recusada` com `FORNECIMENTO_INEXISTENTE` |
| (inexistente) | `pedido_atualizado` com `CANCELADO` | — | CANCELADA_SEM_RESERVA | nenhum; não publica |
| (inexistente) | `pedido_atualizado` com `VENDA_CONCLUIDA` | — | (inexistente) | nenhum; não publica |
| RESERVADA | `pedido_atualizado` com `CANCELADO` | — | LIBERADA | disponível +q, reservada −q; publica `estoque_atualizado` com `LIBERACAO` |
| RESERVADA | `pedido_atualizado` com `VENDA_CONCLUIDA` | — | BAIXADA | reservada −q; publica `estoque_atualizado` com `BAIXA` |
| qualquer existente | `pedido_criado` válido | — | (sem mudança) | nenhum; não publica |
| LIBERADA, BAIXADA, CANCELADA_SEM_RESERVA | `pedido_atualizado` | — | (sem mudança) | nenhum; não publica |
| qualquer | `pedido_atualizado` com outro `status` | — | (sem mudança) | nenhum; não publica |

LIBERADA, BAIXADA e CANCELADA_SEM_RESERVA são estados finais. O estado CANCELADA_SEM_RESERVA existe porque `pedido_criado` e `pedido_atualizado` são tópicos diferentes e o Kafka não garante a ordem entre eles: se o cancelamento chegar antes da criação, a reserva posterior não acontece.

## 7. Contratos de interface

### 7.1 Autenticação e contexto da requisição

Rotas públicas (sem token): `/health`, `/health/ready`, `/metrics`, `/docs`, `/openapi.json`. Todas as rotas `/api/v1/...` exigem `Authorization: Bearer <token>`.

Validação do token, nesta ordem:
1. Cabeçalho `Authorization` ausente, vazio, ou que não começa com `Bearer ` seguido de texto preenchido → `401 TOKEN_AUSENTE`.
2. Assinatura inválida com HS256 e `jwt_secret`, token malformado, ou claims ausentes ou inválidos: `sub` e `empresaId` texto preenchido, `perfil` um dos quatro perfis, `exp` inteiro, `type` igual a `"access"` → `401 TOKEN_INVALIDO`.
3. `exp` menor ou igual a `int(agora.timestamp())` → `401 TOKEN_EXPIRADO`. A expiração é verificada com `clock.now()` (decodificar com `options={"verify_exp": False}` e comparar manualmente).

Toda resposta inclui o cabeçalho `X-Correlation-Id` com o correlation id da requisição.

### 7.2 API REST

| ID | Método | Rota | Perfis | Sucesso | Erros possíveis (na ordem de verificação) |
|---|---|---|---|---|---|
| API-01 | GET | `/health` | público | 200 | — |
| API-02 | GET | `/health/ready` | público | 200 | 503 `DEPENDENCIA_INDISPONIVEL` |
| API-03 | GET | `/metrics` | público | 200 | — |
| API-04 | POST | `/api/v1/fornecimentos` | `fornecedor` | 201 | 401 `TOKEN_AUSENTE` → 401 `TOKEN_INVALIDO` → 401 `TOKEN_EXPIRADO` → 403 `PERFIL_NAO_PERMITIDO` → 422 `DADOS_INVALIDOS` → 422 `PRODUTO_INEXISTENTE` → 500 `ERRO_INTERNO` |
| API-05 | GET | `/api/v1/fornecimentos/{fornecimento_id}` | `comprador`, `fornecedor`, `admin` | 200 | 401 (como API-04) → 403 `PERFIL_NAO_PERMITIDO` → 404 `FORNECIMENTO_NAO_ENCONTRADO` |
| API-06 | GET | `/api/v1/fornecimentos` | `comprador`, `fornecedor`, `admin` | 200 | 401 (como API-04) → 403 `PERFIL_NAO_PERMITIDO` → 422 `PAGINACAO_INVALIDA` |

#### API-01 — Saúde
Resposta 200: `{"status": "UP", "service": "fornecimentos-service", "timestamp": "2026-10-26T14:00:00Z"}`

#### API-02 — Prontidão
Resposta 200 quando `repositorio.disponivel()` e `event_bus.disponivel()` retornam `True`: `{"status": "READY", "service": "fornecimentos-service", "timestamp": "2026-10-26T14:00:00Z"}`. Se qualquer um retornar `False` ou lançar exceção: `503 DEPENDENCIA_INDISPONIVEL`.

#### API-03 — Métricas
Igual à API-03 da ESP-PRD-001, com `service="fornecimentos-service"`:
```text
# HELP http_requests_total Total de requisicoes HTTP respondidas
# TYPE http_requests_total counter
http_requests_total{service="fornecimentos-service",status="201"} 1
```
A contagem inclui todas as respostas HTTP da aplicação, exceto as do próprio `/metrics`, ordenadas pelo código de status. O contador pertence à instância criada por `create_app`.

#### API-04 — Cadastrar fornecimento
Requisição:
```json
{"produto_id": "PROD-1", "preco": 5.5, "quantidade_disponivel": 15000, "origem": "Goiânia-GO"}
```
Resposta 201:
```json
{
  "fornecimento_id": "0e9d8c7b-6a5f-4e3d-9c2b-1a0f9e8d7c6b",
  "fornecedor_id": "EMP-34",
  "produto_id": "PROD-1",
  "unidade": "L",
  "preco": 5.5,
  "quantidade_disponivel": 15000.0,
  "quantidade_reservada": 0.0,
  "origem": "Goiânia-GO",
  "criado_por_usuario_id": "USR-7",
  "criado_em": "2026-10-26T14:00:00Z",
  "atualizado_em": "2026-10-26T14:00:00Z"
}
```

#### API-05 — Consultar fornecimento
Resposta 200: o fornecimento completo, no formato da resposta 201 da API-04.

#### API-06 — Listar fornecimentos
Parâmetros: `page` (inteiro ≥ 1, padrão 1), `size` (inteiro de 1 a 100, padrão 10), `produto_id` (opcional; se ausente ou não for texto preenchido, sem filtro).

Resposta 200: `{"itens": [<fornecimento>, ...], "page": 1, "size": 10, "total": 1}`, com cada item no formato da resposta 201 da API-04.

### 7.3 Eventos consumidos

| Tópico | Produtor | Chave | Ação | Em caso de mensagem inválida |
|---|---|---|---|---|
| `produto_cadastrado` | `produtos-service` | `produtoId` | RF-05 | Publicar em `fornecimentos.dlt` (RN-09) |
| `pedido_criado` | `pedidos-service` | `pedidoId` | RF-06 | Publicar em `fornecimentos.dlt` (RN-09) |
| `pedido_atualizado` | `pedidos-service` | `pedidoId` | RF-07 | Publicar em `fornecimentos.dlt` (RN-09) |

Envelope esperado em todas as mensagens (padrão do kit): `eventId`, `eventType`, `eventVersion`, `timestamp`, `source`, `correlationId`, `aggregateId`, `payload`. Campos extras no envelope ou no payload são ignorados.

Exemplo de `pedido_criado` recebido pelo handler:
```json
{
  "eventId": "a8098c1a-f86e-41da-bd1a-00112444be1f",
  "eventType": "pedido_criado",
  "eventVersion": "1.0",
  "timestamp": "2026-10-26T14:09:59Z",
  "source": "pedidos-service",
  "correlationId": "b7c6d5e4-f3a2-4b1c-9d0e-8f7a6b5c4d3e",
  "aggregateId": "PED-1",
  "payload": {
    "pedidoId": "PED-1",
    "negociacaoId": "NEG-7",
    "compradorId": "EMP-12",
    "fornecedorId": "EMP-34",
    "fornecimentoId": "FORN-1",
    "produtoId": "PROD-1",
    "quantidade": 30,
    "valorTotal": 165.0,
    "status": "CRIADO"
  }
}
```

Exemplo de `pedido_atualizado`:
```json
{
  "eventId": "f0e1d2c3-b4a5-4968-8776-655443322110",
  "eventType": "pedido_atualizado",
  "eventVersion": "1.0",
  "timestamp": "2026-10-26T18:00:00Z",
  "source": "pedidos-service",
  "correlationId": "b7c6d5e4-f3a2-4b1c-9d0e-8f7a6b5c4d3e",
  "aggregateId": "PED-1",
  "payload": {"pedidoId": "PED-1", "fornecimentoId": "FORN-1", "status": "CANCELADO"}
}
```

Exemplo de `produto_cadastrado`: o do §7.4 da ESP-PRD-001.

### 7.4 Eventos publicados

Envelope comum:

| Campo | Valor |
|---|---|
| eventId | UUID4 novo, único por mensagem publicada |
| eventType | igual ao nome do tópico |
| eventVersion | `"1.0"` (string) |
| timestamp | instante = `clock.now()` |
| source | `"fornecimentos-service"` |
| correlationId | correlation id (glossário) da requisição ou da mensagem consumida que originou a publicação |
| aggregateId | igual à chave de partição |
| payload | objeto específico do tópico |

| Tópico | Quando | Chave de partição | Payload |
|---|---|---|---|
| `fornecimento_criado` | Fornecimento cadastrado (RF-01) | `fornecimento_id` | `fornecimentoId`, `fornecedorId`, `produtoId`, `unidade`, `preco`, `quantidadeDisponivel`, `origem`, `criadoPor` (`empresaId`, `usuarioId`), `criadoEm` |
| `estoque_atualizado` | Reserva, liberação ou baixa (RF-06, RF-07) | `fornecimento_id` | `fornecimentoId`, `produtoId`, `fornecedorId`, `operacao` (`RESERVA`, `LIBERACAO` ou `BAIXA`), `quantidadeMovimentada`, `quantidadeDisponivel` e `quantidadeReservada` (saldos depois da operação), `pedidoId`, `atualizadoEm` |
| `reserva_estoque_recusada` | Reserva não feita (RF-06) | `pedido_id` | `pedidoId`, `fornecimentoId`, `quantidadeSolicitada`, `quantidadeDisponivel` (`null` se o fornecimento não existe), `motivo` (`ESTOQUE_INSUFICIENTE` ou `FORNECIMENTO_INEXISTENTE`), `recusadoEm` |
| `fornecimentos.dlt` | Mensagem consumida inválida ou com falha (RN-09) | `aggregateId` da mensagem original se for texto preenchido; senão `eventId` original se for texto preenchido; senão `"desconhecido"` | `originalEvent` (a mensagem recebida, intacta), `error` (texto não vazio com o motivo), `stackTrace` (`""` para mensagem inválida; o *traceback* para exceção), `failedAtAttempt` (`1`) |

Mapeamento do fornecimento (§6.1) para `fornecimento_criado`: `fornecimento_id` → `fornecimentoId`; `fornecedor_id` → `fornecedorId` e `criadoPor.empresaId`; `produto_id` → `produtoId`; `quantidade_disponivel` → `quantidadeDisponivel`; `criado_por_usuario_id` → `criadoPor.usuarioId`; `criado_em` → `criadoEm`; `unidade`, `preco` e `origem` com o mesmo nome. `quantidade_reservada` e `atualizado_em` não vão no evento.

Exemplo de `estoque_atualizado` (`event_bus.publish("estoque_atualizado", "FORN-1", mensagem)`):
```json
{
  "eventId": "c2b1a098-7f6e-4d5c-8b4a-39281706f5e4",
  "eventType": "estoque_atualizado",
  "eventVersion": "1.0",
  "timestamp": "2026-10-26T14:10:00Z",
  "source": "fornecimentos-service",
  "correlationId": "b7c6d5e4-f3a2-4b1c-9d0e-8f7a6b5c4d3e",
  "aggregateId": "FORN-1",
  "payload": {
    "fornecimentoId": "FORN-1",
    "produtoId": "PROD-1",
    "fornecedorId": "EMP-34",
    "operacao": "RESERVA",
    "quantidadeMovimentada": 30.0,
    "quantidadeDisponivel": 70.0,
    "quantidadeReservada": 30.0,
    "pedidoId": "PED-1",
    "atualizadoEm": "2026-10-26T14:10:00Z"
  }
}
```

Exemplo de `reserva_estoque_recusada` (chave `"PED-2"`):
```json
{
  "eventId": "e1f2a3b4-c5d6-4e7f-8a9b-0c1d2e3f4a5b",
  "eventType": "reserva_estoque_recusada",
  "eventVersion": "1.0",
  "timestamp": "2026-10-26T14:12:00Z",
  "source": "fornecimentos-service",
  "correlationId": "4d3c2b1a-0f9e-4d8c-b7a6-5f4e3d2c1b0a",
  "aggregateId": "PED-2",
  "payload": {
    "pedidoId": "PED-2",
    "fornecimentoId": "FORN-1",
    "quantidadeSolicitada": 80.0,
    "quantidadeDisponivel": 70.0,
    "motivo": "ESTOQUE_INSUFICIENTE",
    "recusadoEm": "2026-10-26T14:12:00Z"
  }
}
```

## 8. Requisitos funcionais

Nos critérios abaixo, "token de X" significa um token válido (§7.1) com `perfil` = X, `empresaId` = `"EMP-34"`, `sub` = `"USR-7"` e `exp` uma hora depois de agora, salvo indicação em contrário. O relógio está em `2026-10-26T14:00:00Z`. "Produto PROD-1 conhecido" significa que o handler de `produto_cadastrado` já recebeu uma mensagem válida com `produtoId` "PROD-1", `nome` "Leite integral", `unidade` "L" e `tipoTransporte` "REFRIGERADO". "Fornecimento FORN-1 com D/R" significa um fornecimento de `fornecimento_id` "FORN-1", `fornecedor_id` "EMP-34", `produto_id` "PROD-1", com quantidade disponível D e reservada R, já gravado no repositório. "Pedido válido" segue o exemplo do §7.3, variando só os campos indicados.

### RF-01 — Cadastrar fornecimento
- **Prioridade:** Must
- **Enunciado (EARS):** Quando uma empresa com perfil `fornecedor` enviar um fornecimento válido de um produto conhecido para a API-04, o serviço deve gravá-lo com quantidade reservada 0 e publicar `fornecimento_criado`.
- **Regras aplicáveis:** RN-01, RN-02, RN-03, RN-04, RN-10
- **Interface:** API-04, tópico `fornecimento_criado`

**Critérios de aceitação**
```gherkin
# CA-01
Cenário: Fornecedor cadastra oferta
  Dado o produto PROD-1 conhecido e um token de "fornecedor"
  Quando envia POST /api/v1/fornecimentos com produto_id "PROD-1", preco 5.5, quantidade_disponivel 15000 e origem "Goiânia-GO"
  Então a resposta é 201 com fornecimento_id UUID4, fornecedor_id "EMP-34", produto_id "PROD-1", unidade "L", preco 5.5, quantidade_disponivel 15000, quantidade_reservada 0, origem "Goiânia-GO", criado_por_usuario_id "USR-7", criado_em e atualizado_em "2026-10-26T14:00:00Z"
  E GET /api/v1/fornecimentos/{fornecimento_id} com um token de "comprador" retorna 200 com o mesmo corpo

# CA-02
Cenário: Perfis sem permissão de cadastro
  Dado o produto PROD-1 conhecido
  Quando tokens de "comprador", "transportadora" e "admin" enviam POST /api/v1/fornecimentos com um corpo válido
  Então as três respostas são 403 com codigo "PERFIL_NAO_PERMITIDO"
  E nenhum fornecimento é gravado e nenhuma mensagem é publicada

# CA-03
Cenário: Dados inválidos (partição de equivalência e valor-limite)
  Dado o produto PROD-1 conhecido e um token de "fornecedor"
  Quando envia POST /api/v1/fornecimentos com corpos que diferem do corpo do CA-01 só em:
    | caso                              | alteração                                 |
    | preço zero                        | "preco": 0                                |
    | preço negativo                    | "preco": -1                               |
    | preço como string                 | "preco": "5.50"                           |
    | preço com 3 casas                 | "preco": 5.555                            |
    | preço acima do máximo             | "preco": 10000000000                      |
    | preço booleano                    | "preco": true                             |
    | quantidade zero                   | "quantidade_disponivel": 0                |
    | quantidade com 3 casas            | "quantidade_disponivel": 1.234            |
    | origem só com espaços             | "origem": "   "                           |
    | origem com 256 caracteres         | "origem": 256 vezes "a"                   |
    | produto_id ausente                | sem a chave "produto_id"                  |
    | produto_id numérico               | "produto_id": 1                           |
  E também com o corpo ["x"] e com o texto {"produto_id": (JSON malformado)
  Então cada resposta é 422 com codigo "DADOS_INVALIDOS"
  E nenhum fornecimento é gravado e nenhuma mensagem é publicada

# CA-04
Cenário: Produto desconhecido
  Dado um token de "fornecedor" e nenhum produto conhecido com id "PROD-X"
  Quando envia POST /api/v1/fornecimentos com produto_id "PROD-X" e os demais campos do CA-01
  Então a resposta é 422 com codigo "PRODUTO_INEXISTENTE"
  E nenhuma mensagem é publicada

# CA-05
Cenário: Fornecedor vem do token e valores no limite são aceitos
  Dado o produto PROD-1 conhecido e um token de "fornecedor" com empresaId "EMP-34"
  Quando envia POST /api/v1/fornecimentos com produto_id "PROD-1", preco 9999999999.99, quantidade_disponivel 0.01, origem "  Anápolis-GO  " e fornecedor_id "EMP-99"
  Então a resposta é 201 com fornecedor_id "EMP-34", preco 9999999999.99, quantidade_disponivel 0.01 e origem "Anápolis-GO"

# CA-06
Cenário: Falha do repositório
  Dado o produto PROD-1 conhecido, um token de "fornecedor" e um repositório cujo inserir_fornecimento lança exceção
  Quando envia o corpo do CA-01
  Então a resposta é 500 com codigo "ERRO_INTERNO"
  E nenhuma mensagem é publicada
```

### RF-02 — Consultar fornecimento
- **Prioridade:** Must
- **Enunciado (EARS):** Quando uma empresa com perfil `comprador`, `fornecedor` ou `admin` consultar a API-05 com um `fornecimento_id` existente, o serviço deve retornar o fornecimento com os saldos atuais.
- **Regras aplicáveis:** RN-05, RN-06
- **Interface:** API-05

**Critérios de aceitação**
```gherkin
# CA-07
Cenário: Consulta mostra os saldos atuais
  Dado o fornecimento FORN-1 com 70/30
  Quando um token de "admin" consulta GET /api/v1/fornecimentos/FORN-1
  Então a resposta é 200 com quantidade_disponivel 70 e quantidade_reservada 30

# CA-08
Cenário: Fornecimento inexistente
  Quando um token de "comprador" consulta GET /api/v1/fornecimentos/FORN-X
  Então a resposta é 404 com codigo "FORNECIMENTO_NAO_ENCONTRADO"

# CA-09
Cenário: Transportadora não consulta ofertas
  Dado o fornecimento FORN-1 com 100/0
  Quando um token de "transportadora" consulta GET /api/v1/fornecimentos/FORN-1 e GET /api/v1/fornecimentos
  Então as duas respostas são 403 com codigo "PERFIL_NAO_PERMITIDO"
```

### RF-03 — Listar fornecimentos
- **Prioridade:** Must
- **Enunciado (EARS):** Quando uma empresa com perfil `comprador`, `fornecedor` ou `admin` consultar a API-06, o serviço deve retornar a página pedida, na ordem de cadastro, com o total de fornecimentos que atendem ao filtro.
- **Regras aplicáveis:** RN-05, RN-06
- **Interface:** API-06

**Critérios de aceitação**
```gherkin
# CA-10
Cenário: Paginação e filtro por produto
  Dado os produtos PROD-1 e PROD-2 conhecidos e 3 fornecimentos cadastrados nesta ordem: origem "A" (PROD-1) às 14:00:00Z, origem "B" (PROD-2) às 14:00:01Z e origem "C" (PROD-1) às 14:00:02Z
  Quando um token de "comprador" consulta GET /api/v1/fornecimentos?page=1&size=2
  Então a resposta é 200 com os itens de origem "A" e "B", page 1, size 2 e total 3
  Quando consulta GET /api/v1/fornecimentos?produto_id=PROD-1
  Então a resposta é 200 com os itens de origem "A" e "C" e total 2
  Quando consulta GET /api/v1/fornecimentos?page=9&size=2
  Então a resposta é 200 com itens [] e total 3

# CA-11
Cenário: Parâmetros de paginação inválidos
  Quando um token de "comprador" consulta GET /api/v1/fornecimentos com cada um dos parâmetros: size=101, size=0, page=0, page=abc
  Então cada resposta é 422 com codigo "PAGINACAO_INVALIDA"
  Quando consulta GET /api/v1/fornecimentos?size=100
  Então a resposta é 200
```

### RF-04 — Publicar fornecimento criado
- **Prioridade:** Must
- **Enunciado (EARS):** Quando um fornecimento for gravado com sucesso, o serviço deve publicar uma mensagem em `fornecimento_criado` com chave igual ao `fornecimento_id`.
- **Regras aplicáveis:** RN-04, RN-12
- **Interface:** tópico `fornecimento_criado`

**Critérios de aceitação**
```gherkin
# CA-12
Cenário: Evento publicado com envelope, chave e payload
  Dado o cabeçalho X-Correlation-Id "corr-001"
  Quando o CA-01 é executado
  Então exatamente 1 mensagem é publicada, no tópico "fornecimento_criado", com key igual ao fornecimento_id da resposta
  E a mensagem tem eventId UUID4, eventType "fornecimento_criado", eventVersion "1.0", timestamp "2026-10-26T14:00:00Z", source "fornecimentos-service", correlationId "corr-001" e aggregateId igual ao fornecimento_id
  E o payload é fornecimentoId igual ao fornecimento_id, fornecedorId "EMP-34", produtoId "PROD-1", unidade "L", preco 5.5, quantidadeDisponivel 15000, origem "Goiânia-GO", criadoPor {"empresaId": "EMP-34", "usuarioId": "USR-7"} e criadoEm "2026-10-26T14:00:00Z"

# CA-13
Cenário: Requisição recusada não publica
  Quando os cenários CA-02, CA-03, CA-04 e CA-31 a CA-34 são executados
  Então nenhuma mensagem é publicada
```

### RF-05 — Manter a referência local de produtos
- **Prioridade:** Must
- **Enunciado (EARS):** Quando uma mensagem válida de `produto_cadastrado` for recebida e o `produtoId` ainda não for conhecido, o serviço deve gravar o produto de referência.
- **Regras aplicáveis:** RN-07, RN-08, RN-09
- **Interface:** tópico `produto_cadastrado`

**Critérios de aceitação**
```gherkin
# CA-14
Cenário: Produto passa a ser aceito em ofertas
  Dado que PROD-9 não é conhecido
  Quando o handler recebe produto_cadastrado válido com produtoId "PROD-9", nome "Soja", unidade "TON" e tipoTransporte "GRANEL"
  Então POST /api/v1/fornecimentos com produto_id "PROD-9" e um token de "fornecedor" retorna 201 com unidade "TON"
  E o handler não publica nenhuma mensagem

# CA-15
Cenário: Produto repetido não sobrescreve
  Dado PROD-1 conhecido com unidade "L"
  Quando o handler recebe outra mensagem produto_cadastrado, com outro eventId, para "PROD-1" com unidade "KG"
  Então um novo fornecimento de PROD-1 é criado com unidade "L"

# CA-16
Cenário: Produto inválido vai para a DLT
  Quando o handler recebe produto_cadastrado com eventId "E-P1", aggregateId "PROD-8" e payload sem o campo unidade
  Então o handler não lança exceção
  E é publicada em "fornecimentos.dlt" uma mensagem com key "PROD-8", payload.originalEvent igual à mensagem recebida, payload.error não vazio, payload.stackTrace "" e payload.failedAtAttempt 1
  E POST /api/v1/fornecimentos com produto_id "PROD-8" retorna 422 com codigo "PRODUTO_INEXISTENTE"
```

### RF-06 — Reservar estoque a partir de pedido criado
- **Prioridade:** Must
- **Enunciado (EARS):** Quando uma mensagem válida de `pedido_criado` for recebida pela primeira vez para um par pedido e fornecimento, o serviço deve reservar a quantidade se houver saldo, ou publicar `reserva_estoque_recusada` se não houver.
- **Regras aplicáveis:** RN-08, RN-09, RN-11, RN-13, RN-14
- **Interface:** tópicos `pedido_criado`, `estoque_atualizado`, `reserva_estoque_recusada`

**Critérios de aceitação**
```gherkin
# CA-17
Cenário: Reserva com saldo suficiente
  Dado o fornecimento FORN-1 com 100/0 e o relógio em 2026-10-26T14:10:00Z
  Quando o handler recebe pedido_criado válido com pedidoId "PED-1", fornecimentoId "FORN-1", quantidade 30 e correlationId "corr-ped"
  Então GET /api/v1/fornecimentos/FORN-1 retorna quantidade_disponivel 70, quantidade_reservada 30 e atualizado_em "2026-10-26T14:10:00Z"
  E é publicada exatamente 1 mensagem, em "estoque_atualizado", com key "FORN-1", correlationId "corr-ped" e payload fornecimentoId "FORN-1", produtoId "PROD-1", fornecedorId "EMP-34", operacao "RESERVA", quantidadeMovimentada 30, quantidadeDisponivel 70, quantidadeReservada 30, pedidoId "PED-1" e atualizadoEm "2026-10-26T14:10:00Z"

# CA-18
Cenário: Mesmo evento entregue de novo (idempotência por eventId)
  Dado o estado final do CA-17
  Quando o handler recebe de novo a mesma mensagem do CA-17 (mesmo eventId)
  Então o fornecimento continua com 70/30
  E nenhuma mensagem é publicada

# CA-19
Cenário: Mesmo pedido com outro eventId (idempotência por reserva)
  Dado o estado final do CA-17
  Quando o handler recebe pedido_criado com outro eventId, pedidoId "PED-1", fornecimentoId "FORN-1" e quantidade 30
  Então o fornecimento continua com 70/30
  E nenhuma mensagem é publicada

# CA-20
Cenário: Estoque insuficiente
  Dado o fornecimento FORN-1 com 70/30
  Quando o handler recebe pedido_criado válido com pedidoId "PED-2", fornecimentoId "FORN-1" e quantidade 80
  Então o fornecimento continua com 70/30
  E é publicada exatamente 1 mensagem, em "reserva_estoque_recusada", com key "PED-2" e payload pedidoId "PED-2", fornecimentoId "FORN-1", quantidadeSolicitada 80, quantidadeDisponivel 70, motivo "ESTOQUE_INSUFICIENTE" e recusadoEm igual ao relógio

# CA-21
Cenário: Reserva de todo o saldo (valor-limite)
  Dado o fornecimento FORN-1 com 70/30
  Quando o handler recebe pedido_criado válido com pedidoId "PED-3", fornecimentoId "FORN-1" e quantidade 70
  Então o fornecimento fica com 0/100
  E é publicada 1 mensagem em "estoque_atualizado" com operacao "RESERVA" e quantidadeDisponivel 0

# CA-22
Cenário: Fornecimento inexistente
  Quando o handler recebe pedido_criado válido com pedidoId "PED-4" e fornecimentoId "FORN-X"
  Então é publicada exatamente 1 mensagem, em "reserva_estoque_recusada", com key "PED-4", motivo "FORNECIMENTO_INEXISTENTE" e quantidadeDisponivel null

# CA-23
Cenário: Pedido sem fornecimentoId vai para a DLT (exemplo do guia do kit)
  Dado o fornecimento FORN-1 com 100/0
  Quando o handler recebe pedido_criado com eventId "E-K1", aggregateId "PED-5" e payload sem o campo fornecimentoId
  Então o handler não lança exceção
  E o fornecimento continua com 100/0
  E é publicada exatamente 1 mensagem, em "fornecimentos.dlt", com key "PED-5" e payload.originalEvent igual à mensagem recebida

# CA-24
Cenário: Mensagens inválidas (partição de equivalência)
  Dado o fornecimento FORN-1 com 100/0
  Quando o handler recebe pedido_criado válido exceto por cada um dos defeitos: quantidade 0; quantidade -5; quantidade "30"; quantidade 1.234; quantidade true; pedidoId "  "; sem payload; payload que não é objeto; eventId ausente
  Então para cada mensagem o handler não lança exceção, o fornecimento continua com 100/0 e é publicada 1 mensagem em "fornecimentos.dlt"
  E quando o eventId e o aggregateId estão ausentes, a key da mensagem na DLT é "desconhecido"

# CA-25
Cenário: Mensagem repetida e inválida vai para a DLT nas duas vezes
  Quando o handler recebe duas vezes a mesma mensagem pedido_criado (mesmo eventId "E-DUP") com quantidade 0
  Então são publicadas 2 mensagens em "fornecimentos.dlt"

# CA-26
Cenário: Falha do repositório no handler
  Dado o fornecimento FORN-1 com 100/0 e um repositório cujo aplicar_movimento lança exceção
  Quando o handler recebe pedido_criado válido com pedidoId "PED-6", fornecimentoId "FORN-1" e quantidade 10
  Então o handler não lança exceção
  E nenhuma reserva é gravada, o eventId não é registrado como processado e não é publicada mensagem em "estoque_atualizado"
  E é publicada 1 mensagem em "fornecimentos.dlt" com payload.stackTrace não vazio
```

### RF-07 — Liberar ou dar baixa a partir de pedido atualizado
- **Prioridade:** Must
- **Enunciado (EARS):** Quando uma mensagem válida de `pedido_atualizado` for recebida pela primeira vez, o serviço deve liberar a reserva se o status for `CANCELADO`, dar baixa se for `VENDA_CONCLUIDA`, e ignorar qualquer outro status, conforme o §6.2.
- **Regras aplicáveis:** RN-08, RN-09, RN-11, RN-15, RN-16
- **Interface:** tópicos `pedido_atualizado`, `estoque_atualizado`

**Critérios de aceitação**
```gherkin
# CA-27
Cenário: Cancelamento libera a reserva
  Dado o estado final do CA-17 (FORN-1 com 70/30, reserva de PED-1 RESERVADA)
  Quando o handler recebe pedido_atualizado válido com pedidoId "PED-1", fornecimentoId "FORN-1" e status "CANCELADO"
  Então o fornecimento fica com 100/0
  E é publicada 1 mensagem em "estoque_atualizado" com key "FORN-1", operacao "LIBERACAO", quantidadeMovimentada 30, quantidadeDisponivel 100, quantidadeReservada 0 e pedidoId "PED-1"
  Quando o handler recebe outro pedido_atualizado (outro eventId) para PED-1 com status "VENDA_CONCLUIDA"
  Então o fornecimento continua com 100/0 e nenhuma mensagem é publicada

# CA-28
Cenário: Venda concluída dá baixa
  Dado o estado final do CA-17
  Quando o handler recebe pedido_atualizado válido com pedidoId "PED-1", fornecimentoId "FORN-1" e status "VENDA_CONCLUIDA"
  Então o fornecimento fica com 70/0
  E é publicada 1 mensagem em "estoque_atualizado" com operacao "BAIXA", quantidadeMovimentada 30, quantidadeDisponivel 70 e quantidadeReservada 0

# CA-29
Cenário: Cancelamento chega antes da criação do pedido
  Dado o fornecimento FORN-1 com 100/0
  Quando o handler recebe pedido_atualizado válido com pedidoId "PED-7", fornecimentoId "FORN-1" e status "CANCELADO"
  E depois recebe pedido_criado válido com pedidoId "PED-7", fornecimentoId "FORN-1" e quantidade 40
  Então o fornecimento continua com 100/0
  E nenhuma mensagem é publicada

# CA-30
Cenário: Status desconhecido e mensagem inválida
  Dado o estado final do CA-17
  Quando o handler recebe pedido_atualizado válido para PED-1 com status "FRETE_SELECIONADO"
  Então o fornecimento continua com 70/30 e nenhuma mensagem é publicada
  Quando o handler recebe pedido_atualizado com aggregateId "PED-1" e payload sem o campo status
  Então o handler não lança exceção e é publicada 1 mensagem em "fornecimentos.dlt" com key "PED-1"
```

### RF-08 — Autenticar e autorizar requisições
- **Prioridade:** Must
- **Enunciado (EARS):** Se uma requisição a uma rota `/api/v1/...` não tiver token válido e não expirado, então o serviço deve recusá-la com 401 e o código correspondente (§7.1), sem executar a operação.
- **Regras aplicáveis:** RN-01, RN-04, RN-05
- **Interface:** API-04, API-05, API-06

**Critérios de aceitação**
```gherkin
# CA-31
Cenário: Token ausente
  Quando POST /api/v1/fornecimentos é enviado sem Authorization, com "Authorization: Basic abc" e com "Authorization: Bearer "
  Então as três respostas são 401 com codigo "TOKEN_AUSENTE"

# CA-32
Cenário: Token com assinatura de outra chave
  Dado um token de "fornecedor" assinado com a chave "outra-chave"
  Quando envia POST /api/v1/fornecimentos com o corpo do CA-01
  Então a resposta é 401 com codigo "TOKEN_INVALIDO"

# CA-33
Cenário: Claims inválidos
  Dado tokens assinados com a chave correta, cada um com um problema: sem empresaId; perfil "gerente"; type "refresh"; sub ""
  Quando cada um consulta GET /api/v1/fornecimentos
  Então cada resposta é 401 com codigo "TOKEN_INVALIDO"

# CA-34
Cenário: Token expirado no limite
  Dado um token de "comprador" com exp igual a 2026-10-26T14:00:00Z e o relógio em 2026-10-26T14:00:00Z
  Quando consulta GET /api/v1/fornecimentos
  Então a resposta é 401 com codigo "TOKEN_EXPIRADO"
  Dado o mesmo token e o relógio em 2026-10-26T13:59:59Z
  Quando consulta GET /api/v1/fornecimentos
  Então a resposta é 200
```

### RF-09 — Propagar o identificador de correlação
- **Prioridade:** Should
- **Enunciado (EARS):** O serviço deve devolver o correlation id no cabeçalho `X-Correlation-Id` de toda resposta, no campo `correlationId` de todo erro, e repassá-lo no `correlationId` de todo evento publicado, inclusive os publicados por handlers.
- **Regras aplicáveis:** RN-12
- **Interface:** todas

**Critérios de aceitação**
```gherkin
# CA-35
Cenário: Correlation id na API
  Quando GET /api/v1/fornecimentos/FORN-X é enviado com um token de "comprador" e X-Correlation-Id "corr-404"
  Então a resposta é 404, tem o cabeçalho X-Correlation-Id "corr-404" e o corpo tem correlationId "corr-404"
  Quando GET /health é enviado sem X-Correlation-Id
  Então a resposta tem o cabeçalho X-Correlation-Id com um UUID4 novo

# CA-36
Cenário: Correlation id ausente no evento consumido
  Dado o fornecimento FORN-1 com 100/0
  Quando o handler recebe pedido_criado válido para PED-8 com quantidade 10 e sem o campo correlationId
  Então a mensagem publicada em "estoque_atualizado" tem correlationId UUID4
```

### RF-10 — Saúde, prontidão e métricas
- **Prioridade:** Must
- **Enunciado (EARS):** O serviço deve responder às API-01, API-02 e API-03 sem autenticação, conforme o §7.2.
- **Regras aplicáveis:** —
- **Interface:** API-01, API-02, API-03

**Critérios de aceitação**
```gherkin
# CA-37
Cenário: Saúde e prontidão
  Quando GET /health é enviado sem token
  Então a resposta é 200 com status "UP", service "fornecimentos-service" e timestamp "2026-10-26T14:00:00Z"
  Quando GET /health/ready é enviado com repositório e barramento disponíveis
  Então a resposta é 200 com status "READY"

# CA-38
Cenário: Dependência indisponível
  Dado um repositório cujo disponivel() retorna False
  Quando GET /health/ready é enviado
  Então a resposta é 503 com codigo "DEPENDENCIA_INDISPONIVEL"

# CA-39
Cenário: Métricas
  Dado uma aplicação nova e o produto PROD-1 conhecido
  Quando são feitas 1 requisição do CA-01 (201) e 2 do CA-08 (404)
  Então GET /metrics contém as linhas http_requests_total{service="fornecimentos-service",status="201"} 1 e http_requests_total{service="fornecimentos-service",status="404"} 2
```

## 9. Regras de negócio

| ID | Regra | Exemplo concreto |
|---|---|---|
| RN-01 | Apenas o perfil `fornecedor` cadastra fornecimentos. `comprador`, `transportadora` e `admin` → 403 `PERFIL_NAO_PERMITIDO`. | Token de comprador em POST → 403. |
| RN-02 | Corpo do cadastro: objeto JSON; `produto_id` string texto preenchido; `preco` número JSON (não booleano, não string) > 0, ≤ 9999999999.99 e com no máximo 2 casas decimais; `quantidade_disponivel` número JSON > 0, ≤ 9999999999.99 e com no máximo 2 casas decimais; `origem` string com 1 a 255 caracteres depois de `strip()`. Violação, campo ausente, tipo errado, corpo não-objeto ou JSON malformado → 422 `DADOS_INVALIDOS`. Campos desconhecidos são ignorados. Casas decimais são contadas em `Decimal(str(valor))`. | `"preco": 5.555` → 422; `"preco": 0.07` → aceito. |
| RN-03 | O `produto_id` precisa existir como produto de referência; senão → 422 `PRODUTO_INEXISTENTE`. A `unidade` do fornecimento é copiada do produto de referência. | PROD-X desconhecido → 422. |
| RN-04 | Requisição recusada (qualquer 4xx ou 5xx) não grava nada e não publica evento. | 403 → nenhuma mensagem. |
| RN-05 | Consulta e listagem: perfis `comprador`, `fornecedor` e `admin`; `transportadora` → 403 `PERFIL_NAO_PERMITIDO`. `fornecimento_id` inexistente → 404 `FORNECIMENTO_NAO_ENCONTRADO`. | Transportadora em GET → 403. |
| RN-06 | Paginação: `page` inteiro ≥ 1 (padrão 1); `size` inteiro de 1 a 100 (padrão 10); fora disso → 422 `PAGINACAO_INVALIDA`. `offset = (page − 1) × size`. | `size=101` → 422. |
| RN-07 | `produto_cadastrado` válido exige `payload.produtoId`, `payload.nome`, `payload.unidade` e `payload.tipoTransporte` como texto preenchido e `timestamp` como instante válido. Se o `produtoId` já for conhecido, a mensagem é ignorada (não sobrescreve, não publica). | 2ª mensagem para PROD-1 com outra unidade → unidade mantida. |
| RN-08 | Idempotência por `eventId`: depois que uma mensagem válida é processada, o `eventId` é registrado na mesma transação das alterações. Mensagem válida com `eventId` já registrado é ignorada sem publicar. A validação (RN-09) vem **antes** da verificação de `eventId`. | Mesmo `pedido_criado` duas vezes → 1 reserva. |
| RN-09 | Mensagem consumida é inválida se: não for objeto; faltar `eventId` como texto preenchido; faltar `payload` ou ele não for objeto; faltar campo obrigatório do payload ou ele tiver tipo ou valor inválido (RN-07, RN-13, RN-15). Mensagem inválida não altera estado, não registra `eventId` e é publicada em `fornecimentos.dlt` (formato do §7.4, `stackTrace` `""`). Exceção lançada pelo repositório durante o processamento: a transação é desfeita, o `eventId` não é registrado e a mensagem é publicada em `fornecimentos.dlt` com o *traceback* em `stackTrace`. O handler nunca propaga exceção. | Quantidade 0 → DLT. |
| RN-10 | `fornecimento_id` (UUID4), `fornecedor_id` (claim `empresaId`), `criado_por_usuario_id` (claim `sub`), `criado_em` e `atualizado_em` (`clock.now()`) são definidos pelo serviço; valores enviados no corpo para esses campos são ignorados. `quantidade_reservada` começa em 0. | Corpo com `fornecedor_id` "EMP-99" e token de "EMP-34" → gravado "EMP-34". |
| RN-11 | Toda mudança de quantidade usa `aplicar_movimento` (§5.1). Nenhuma quantidade fica negativa. | Reservar 80 com 70 disponível → `aplicar_movimento` retorna `None`. |
| RN-12 | Nenhum evento, resposta ou log contém o token. Eventos identificam quem agiu só por `empresaId` e `usuarioId`. O correlation id é repassado conforme o glossário. | — |
| RN-13 | `pedido_criado` válido exige `payload.pedidoId`, `payload.fornecimentoId`, `payload.produtoId`, `payload.fornecedorId` e `payload.status` como texto preenchido, e `payload.quantidade` como número JSON (não booleano) > 0 com no máximo 2 casas decimais. Os demais campos são ignorados. | Sem `fornecimentoId` → DLT. |
| RN-14 | Reserva (§6.2): se já existe reserva para o par (`pedidoId`, `fornecimentoId`), em qualquer situação, nada muda e nada é publicado. Se não existe: com `aplicar_movimento(-q, +q)` bem-sucedido, grava a reserva `RESERVADA` e publica `estoque_atualizado` (`RESERVA`); se o fornecimento não existe ou o saldo é insuficiente, não grava reserva e publica `reserva_estoque_recusada`. | FORN-1 100/0, pedido de 30 → 70/30. |
| RN-15 | `pedido_atualizado` válido exige `payload.pedidoId`, `payload.fornecimentoId` e `payload.status` como texto preenchido. | Sem `status` → DLT. |
| RN-16 | Liberação e baixa (§6.2): com reserva `RESERVADA` de quantidade q, `CANCELADO` aplica `(+q, −q)` e muda para `LIBERADA`; `VENDA_CONCLUIDA` aplica `(0, −q)` e muda para `BAIXADA`; as duas publicam `estoque_atualizado`. Sem reserva, `CANCELADO` grava reserva `CANCELADA_SEM_RESERVA` com quantidade 0. Nos demais casos, nada muda e nada é publicado. Em todos os casos válidos, o `eventId` é registrado. | PED-1 RESERVADA 30 + CANCELADO → 100/0. |

## 10. Catálogo de erros

Formato único de erro (RFC 7807, exigido pelo kit de infraestrutura), com `Content-Type: application/problem+json`:
```json
{
  "type": "https://portal-b2b.corp/erros/fornecimento-nao-encontrado",
  "title": "Fornecimento Não Encontrado",
  "status": 404,
  "detail": "Fornecimento FORN-X não cadastrado.",
  "instance": "/api/v1/fornecimentos/FORN-X",
  "codigo": "FORNECIMENTO_NAO_ENCONTRADO",
  "correlationId": "corr-404",
  "timestamp": "2026-10-26T14:00:00Z"
}
```
`type` é `https://portal-b2b.corp/erros/` seguido do `codigo` em minúsculas com `_` trocado por `-`. `title` é o da tabela abaixo. `detail` é texto livre, não vazio, em português. `instance` é o caminho da requisição, sem parâmetros de consulta. `timestamp` é `clock.now()`.

| Código | HTTP | Title | Quando ocorre |
|---|---|---|---|
| TOKEN_AUSENTE | 401 | Não Autenticado | §7.1, item 1. |
| TOKEN_INVALIDO | 401 | Token Inválido | §7.1, item 2. |
| TOKEN_EXPIRADO | 401 | Token Expirado | §7.1, item 3. |
| PERFIL_NAO_PERMITIDO | 403 | Acesso Negado | RN-01, RN-05. |
| FORNECIMENTO_NAO_ENCONTRADO | 404 | Fornecimento Não Encontrado | RN-05. |
| ROTA_NAO_ENCONTRADA | 404 | Rota Não Encontrada | Rota inexistente. |
| METODO_NAO_PERMITIDO | 405 | Método Não Permitido | Método não aceito pela rota. |
| DADOS_INVALIDOS | 422 | Dados Inválidos | RN-02. |
| PRODUTO_INEXISTENTE | 422 | Produto Inexistente | RN-03. |
| PAGINACAO_INVALIDA | 422 | Paginação Inválida | RN-06. |
| ERRO_INTERNO | 500 | Erro Interno | Exceção não prevista na API, inclusive do repositório. O `detail` não expõe a mensagem da exceção. |
| DEPENDENCIA_INDISPONIVEL | 503 | Dependência Indisponível | API-02 com dependência indisponível. |

Respostas fora do catálogo: nenhuma. A documentação automática do framework (`/docs`, `/openapi.json`) permanece habilitada e não faz parte da avaliação.

**Ordem de verificação:** quando mais de um erro se aplica, retorna-se o primeiro da lista. A validação do corpo e dos parâmetros **não** pode ocorrer antes das verificações 1 a 5 (leia o corpo bruto e valide manualmente):
1. ROTA_NAO_ENCONTRADA / METODO_NAO_PERMITIDO
2. TOKEN_AUSENTE
3. TOKEN_INVALIDO
4. TOKEN_EXPIRADO
5. PERFIL_NAO_PERMITIDO
6. DADOS_INVALIDOS / PAGINACAO_INVALIDA
7. PRODUTO_INEXISTENTE / FORNECIMENTO_NAO_ENCONTRADO
8. ERRO_INTERNO

## 11. Requisitos não funcionais

| ID | Característica (ISO/IEC 25010) | Requisito | Métrica e limiar | Verificação |
|---|---|---|---|---|
| RNF-01 | Interoperabilidade | Formato único de erro. | 100% das respostas 4xx e 5xx no formato do §10, com os 8 campos preenchidos. | CA-40 |
| RNF-02 | Adequação funcional — exatidão | Aritmética decimal exata com `Decimal`. | Fornecimento com 0.3 disponível e três reservas de 0.1: as três aceitas e saldo final 0. Preço 0.07 aceito e devolvido como 0.07. | CA-41 |
| RNF-03 | Confiabilidade — integridade sob concorrência | Saldo nunca negativo com pedidos simultâneos. | 20 mensagens `pedido_criado` de 1 unidade, entregues por 20 threads ao mesmo tempo, para um fornecimento com 10: exatamente 10 reservas e 10 recusas; saldo final 0/10. | CA-42 |
| RNF-04 | Eficiência de desempenho | Processamento em processo. | 300 mensagens `pedido_criado` de 1 unidade processadas em sequência em menos de 3 s; 500 requisições GET /api/v1/fornecimentos?size=100 em menos de 5 s. A meta da plataforma (kit, seção 10.2) é verificada pelo Grupo de Teste com k6. | CA-43 |
| RNF-05 | Manutenibilidade — modularidade | Sem estado de negócio fora do repositório. | Duas aplicações com o mesmo repositório veem os mesmos fornecimentos; com repositórios diferentes, não. | CA-44 |
| RNF-06 | Portabilidade | Somente dependências permitidas (§5). | Nenhum `import` fora da biblioteca padrão, `fastapi`, `pydantic`, `starlette`, `jwt` ou `app`. | CA-45 |
| RNF-07 | Confiabilidade — ordenação | Envelope e chave de partição corretos. | 100% das mensagens com `key` conforme o §7.4, `aggregateId == key`, `eventId` UUID4 único, `eventType` igual ao tópico, `eventVersion` "1.0", `source` "fornecimentos-service" e `timestamp` igual ao relógio. | CA-46 |
| RNF-08 | Segurança — confidencialidade | Token nunca sai do serviço. | 0 ocorrências da string do token nas mensagens publicadas e nos logs do CA-01. | CA-47 |

```gherkin
# CA-40
Cenário: Formato de erro, inclusive para rota e método fora do contrato
  Quando GET /api/v1/inexistente é enviado com um token de "comprador"
  Então a resposta é 404 com codigo "ROTA_NAO_ENCONTRADA"
  Quando DELETE /api/v1/fornecimentos/FORN-1 é enviado com um token de "fornecedor"
  Então a resposta é 405 com codigo "METODO_NAO_PERMITIDO"
  E para cada resposta 4xx e 5xx produzida por este e pelos demais cenários de erro deste documento
  Então o Content-Type é "application/problem+json" e o corpo tem type, title, status, detail, instance, codigo, correlationId e timestamp, todos não vazios, status igual ao código HTTP e type igual a "https://portal-b2b.corp/erros/" seguido do codigo em minúsculas com "_" trocado por "-"

# CA-41
Cenário: Exatidão decimal (falha com float)
  Dado o produto PROD-1 conhecido e um fornecimento criado com quantidade_disponivel 0.3 e preco 0.07
  Então a resposta do cadastro tem preco 0.07
  Quando o handler recebe três pedido_criado válidos para esse fornecimento, de pedidos diferentes, cada um com quantidade 0.1
  Então são publicadas 3 mensagens em "estoque_atualizado" com operacao "RESERVA"
  E o fornecimento fica com quantidade_disponivel 0 e quantidade_reservada 0.3

# CA-42
Cenário: Concorrência
  Dado o fornecimento FORN-1 com 10/0
  Quando 20 threads entregam ao mesmo tempo 20 mensagens pedido_criado válidas, de PED-C01 a PED-C20, cada uma com quantidade 1 para FORN-1
  Então são publicadas exatamente 10 mensagens em "estoque_atualizado" e 10 em "reserva_estoque_recusada"
  E o fornecimento fica com 0/10

# CA-43
Cenário: Desempenho
  Dado o fornecimento FORN-1 com 1000/0
  Quando 300 mensagens pedido_criado válidas de quantidade 1, de pedidos diferentes, são entregues em sequência
  Então o tempo total é inferior a 3 segundos e o fornecimento fica com 700/300
  E 500 requisições GET /api/v1/fornecimentos?size=100 em sequência, com 100 fornecimentos gravados, terminam em menos de 5 segundos, todas com 200

# CA-44
Cenário: Estado somente no repositório
  Dado duas aplicações criadas por create_app com o mesmo repositório
  Quando um fornecimento é cadastrado pela primeira
  Então a segunda retorna 200 para GET /api/v1/fornecimentos/{fornecimento_id}
  Dado duas aplicações criadas com repositórios diferentes
  Quando um fornecimento é cadastrado pela primeira
  Então a segunda retorna 404

# CA-45
Cenário: Dependências
  Ao inspecionar todos os arquivos .py do pacote app
  Então só há imports da biblioteca padrão, fastapi, pydantic, starlette, jwt ou do próprio app

# CA-46
Cenário: Envelope e chave de partição
  Quando os cenários CA-12, CA-17, CA-20 e CA-23 são executados
  Então toda mensagem publicada tem key conforme o §7.4, aggregateId igual à key, eventId UUID4 distinto das demais, eventType igual ao tópico, eventVersion "1.0", source "fornecimentos-service" e timestamp igual ao relógio

# CA-47
Cenário: Token não vaza
  Quando o CA-01 é executado capturando os logs
  Então a string do token não aparece em nenhuma mensagem publicada nem em nenhum registro de log
```

## 12. Matriz de rastreabilidade

| Requisito | Regras | Interfaces | Critérios de aceitação |
|---|---|---|---|
| RF-01 | RN-01, RN-02, RN-03, RN-04, RN-10 | API-04, `fornecimento_criado` | CA-01 a CA-06 |
| RF-02 | RN-05, RN-06 | API-05 | CA-07 a CA-09 |
| RF-03 | RN-05, RN-06 | API-06 | CA-10, CA-11 |
| RF-04 | RN-04, RN-12 | `fornecimento_criado` | CA-12, CA-13 |
| RF-05 | RN-07, RN-08, RN-09 | `produto_cadastrado`, `fornecimentos.dlt` | CA-14 a CA-16 |
| RF-06 | RN-08, RN-09, RN-11, RN-13, RN-14 | `pedido_criado`, `estoque_atualizado`, `reserva_estoque_recusada`, `fornecimentos.dlt` | CA-17 a CA-26 |
| RF-07 | RN-08, RN-09, RN-11, RN-15, RN-16 | `pedido_atualizado`, `estoque_atualizado`, `fornecimentos.dlt` | CA-27 a CA-30 |
| RF-08 | RN-01, RN-04, RN-05 | API-04 a API-06 | CA-31 a CA-34 |
| RF-09 | RN-12 | todas | CA-35, CA-36 |
| RF-10 | — | API-01 a API-03 | CA-37 a CA-39 |
| RNF-01 a RNF-08 | — | todas | CA-40 a CA-47 |

Exceções justificadas à regra de um cenário de erro por RF: nenhuma. Atributos da entidade Fornecimento (§6.1) e campos da resposta da API-04 são idênticos. O payload de `fornecimento_criado` usa nomes em camelCase e não leva `quantidade_reservada` nem `atualizado_em` (mapeamento no §7.4). As entidades ProdutoReferencia e Reserva não são expostas pela API; são observáveis pelos efeitos descritos nos CAs.

## 13. Premissas, decisões e questões em aberto

| ID | Tipo | Descrição | Decisão |
|---|---|---|---|
| Q-01 | Decisão | Onde o token é validado; nome do claim da empresa (P-33). | No serviço, com HS256 e `jwt_secret`; claim `empresaId`, como no código do kit. |
| Q-02 | Decisão | Persistência em memória (como no exemplo ESP-NEG-001) ou banco. | Porta `RepositorioFornecimentos` (§5.1). O Grupo de Teste injeta uma implementação em memória; em produção, o adaptador usa o schema `fornecimentos` do PostgreSQL com o DDL proposto em `docs/banco/`. |
| Q-03 | Decisão | Como garantir que reservas simultâneas não deixem o saldo negativo, inclusive entre duas instâncias do serviço. | `aplicar_movimento` condicional e atômico (§5.1), equivalente ao `UPDATE` condicional testado em PostgreSQL 16 (teste T11 da proposta de DDL). |
| Q-04 | Decisão | Valores dos status de cancelamento e venda concluída em `pedido_atualizado` (P-02). | `"CANCELADO"` e `"VENDA_CONCLUIDA"`. Se o grupo de Pedidos definir outros valores, esta ESP muda de versão. |
| Q-05 | Decisão | `pedido_criado` sem `fornecimentoId`, como no exemplo do guia do kit (P-02). | Mensagem inválida → DLT (RN-13). O pedido ao grupo de Pedidos está no Contrato de Eventos. |
| Q-06 | Decisão | Como avisar Pedidos quando falta estoque (P-16). | Tópico `reserva_estoque_recusada`. A criação do tópico no cluster foi pedida ao grupo de Infraestrutura (issue #12). |
| Q-07 | Decisão | Cancelamento que chega antes da criação do pedido (tópicos diferentes não garantem ordem). | Reserva `CANCELADA_SEM_RESERVA`; a criação posterior é ignorada (§6.2, CA-29). |
| Q-08 | Decisão | Venda concluída sem reserva. | Ignorada e não registrada como reserva. Na prática não ocorre, porque a venda é concluída muito depois da criação do pedido. |
| Q-09 | Decisão | Comparar `fornecedorId` e `produtoId` do pedido com os do fornecimento. | Não comparar na versão 1.0 (§3.2). |
| Q-10 | Decisão | Quem consulta ofertas (P-07). | `comprador`, `fornecedor` e `admin`; `transportadora` não. Só `fornecedor` cadastra (o Grupo de Teste testa comprador criando fornecimento → 403, kit seção 10.2). |
| Q-11 | Decisão | Valores monetários em JSON: string (exemplo do Grupo de Teste) ou número (kit e Contrato de Eventos). | Número JSON, convertido para `Decimal` com `Decimal(str(valor))`. Mantém o padrão do kit usado pelos outros grupos e evita erro de arredondamento nas contas (CA-41). |
| Q-12 | Decisão | Novas tentativas com espera (1, 2 e 4 s) antes da DLT, previstas no kit. | Responsabilidade do adaptador de consumo. O handler envia à DLT na primeira falha (`failedAtAttempt` 1). |
| Q-13 | Decisão | Falha de `publish`. | Fora do escopo; o adaptador real usa *transactional outbox* (ADR-010). |
| Q-14 | Premissa | Momento em que o pedido é criado: o professor fala na entrada do leilão; o kit, depois de `negociacao_fechada` (P-29). | O serviço reserva quando receber `pedido_criado`, seja qual for o momento escolhido pelos grupos. A decisão não muda esta ESP. |

### 13.1 Casos de borda obrigatórios

| Caso de borda | Decisão |
|---|---|
| String vazia ou só com espaços em campos obrigatórios | Inválida. Na API → 422 `DADOS_INVALIDOS`; em mensagem consumida → DLT. Strings válidas da API são gravadas depois de `strip()`. |
| Cabeçalho opcional presente porém vazio | `X-Correlation-Id` vazio ou só com espaços equivale a ausente. `Authorization` vazio → `TOKEN_AUSENTE`. |
| Mensagem duplicada **e** inválida (qual regra vence: duplicidade ou validação?) | Validação vence: vai para a DLT todas as vezes (RN-08, CA-25). |
| Campo de chave/ID com tipo inesperado (ex.: número no lugar de string) | Na API → 422 `DADOS_INVALIDOS`. Em mensagem consumida → DLT. Na chave da DLT, `aggregateId` e `eventId` só são usados se forem texto preenchido; senão `"desconhecido"`. |
| Data/hora sem fuso horário | `clock.now()` sem fuso é tratado como UTC. `timestamp` de `produto_cadastrado` sem fuso é tratado como UTC; ilegível → DLT. |
| Falha da porta de publicação / banco | Banco na API → 500 `ERRO_INTERNO`, sem publicar. Banco no handler → transação desfeita e DLT com *traceback* (RN-09). Publicação → fora do escopo (Q-13). |
| Rotas e métodos fora do contrato | 404 `ROTA_NAO_ENCONTRADA` e 405 `METODO_NAO_PERMITIDO` no formato do §10. |

## 14. Checklist de prontidão (Definition of Ready) — preenchido pelo QA

- [ ] Nenhum `{{ }}` restante; comentários de orientação removidos.
- [ ] Todo RF tem enunciado EARS, prioridade e CAs de sucesso e erro quando aplicáveis; exceções justificadas na matriz.
- [ ] Todo CA usa valores concretos e resultado observável.
- [ ] Todo código de erro citado em CA existe no §10 e vice-versa.
- [ ] Ordem de verificação de erros definida para cada endpoint.
- [ ] Campos de entidade, projeções de resposta e campos derivados estão mapeados; exemplos JSON respeitam os contratos.
- [ ] Todo tópico citado tem produtor/consumidor, chave e exemplo.
- [ ] Toda dependência externa está modelada como porta (§5.1).
- [ ] Todo RNF tem métrica, limiar e forma de verificação.
- [ ] Matriz de rastreabilidade completa (nenhum RF sem CA, nenhum CA órfão).
- [ ] Não há palavras vagas sem quantificação ("rápido", "adequado", "etc.", "deve tratar erros").
- [ ] Seção 13 sem questões abertas e tabela 13.1 (casos de borda) toda decidida.
- [ ] Comentários `# DECISÃO:` da última geração (se houver) analisados e incorporados como regra.

## 15. Histórico de versões

| Versão | Data | Autor | Mudança |
|---|---|---|---|
| 1.0 | 2026-10-26 | Grupo de Fornecimento e Produtos | Criação a partir do modelo ERS-LLM v1.2 do Grupo de Teste, do Documento de Requisitos v0.4, do Contrato de Eventos v1.0, da proposta de DDL e do kit de infraestrutura. |
