# ESP-PRD-001 — Especificação de Requisitos: Serviço de Produtos

## 0. Metadados

| Campo | Valor |
|---|---|
| Identificador | ESP-PRD-001 |
| Versão | 1.5 |
| Status | Rascunho |
| Serviço / Bounded context | Microsserviço 2, Produtos (`produtos-service`, Portal B2B Distribuído) |
| Autores (PO / Dev / QA) | Grupo de Fornecimento e Produtos: Daniel Carvalho Coutinho, Davi Coelho de Alvarenga, Gabriel Vicentte dos Santos Ferreira, Rafael de Castro Noleto. QA: Grupo de Teste |
| Data | 2026-10-26 |
| Documentos relacionados | Diagrama "Arquitetura do Portal B2B Distribuído" (professor); Kit de integração da Infraestrutura (`Printf-PedroCardoso/portal-b2b-kit-infra`, commit `630515c`); Documento de Requisitos do grupo v0.4; Contrato de Eventos v1.0; ESP-FRN-001 (Fornecimentos); resposta do grupo de Autenticação nas issues #2 e #13 (2026-11-09); resposta do grupo de Logística/Transporte sobre P-06 e P-27 (2026-11-10) |

## 1. Diretivas para a LLM geradora

1. Implemente **exatamente** o que está especificado. Não adicione endpoints, campos, tópicos, perfis ou regras que não estejam neste documento.
2. **Ordem de precedência** quando houver conflito aparente: Catálogo de erros (§10) e Contratos (§7) > Critérios de aceitação (§8) > Regras de negócio (§9) > Requisitos funcionais (§8) > texto descritivo.
3. Nomes de campos, tópicos, códigos de erro, rotas e valores de enumeração são **literais**: use-os byte a byte, com a mesma grafia e caixa.
4. Quando algo não estiver definido, escolha o comportamento mais simples que **não viole** nenhum item deste documento e registre a decisão em um comentário `# DECISÃO:` no código.
5. Entregue código completo e executável. Proibido: `TODO`, `pass` como implementação, pseudocódigo, trechos omitidos ("...").
6. Formato da resposta: os arquivos da estrutura do §5, cada um com caminho relativo e conteúdo completo. Na resposta final, liste os caminhos relativos.

## 2. Contexto

### 2.1 Objetivo do serviço
Manter o catálogo de produtos do portal: empresas fornecedoras e compradoras cadastram produtos, e os demais serviços são avisados de cada produto novo por evento.

### 2.2 Posição na arquitetura
O front-end chama este serviço pelo gateway Nginx (REST, prefixo `/api/v1/produtos`). Cada produto cadastrado gera o evento `produto_cadastrado`, consumido por Fornecimentos (para validar ofertas), Demanda e Mercado. O serviço participa do passo 1 do fluxo principal ("Fornecedor publica fornecimento"), porque a oferta referencia um produto do catálogo. Este serviço não consome eventos.

```text
Front-end ─► Gateway ─REST─► produtos-service ──[produto_cadastrado]──► fornecimentos-service
                                                                    ├─► demanda-service
                                                                    └─► mercado-service
```

## 3. Escopo

### 3.1 Dentro do escopo
- Cadastro de produto por empresas com perfil `SUPPLIER` ou `BUYER`.
- Consulta de produto por identificador.
- Listagem paginada de produtos, com filtro opcional por categoria.
- Publicação do evento `produto_cadastrado`.
- Autenticação por JWT e autorização por perfil.
- Propagação do identificador de correlação (`X-Correlation-Id`).
- Endpoints técnicos `/health`, `/health/ready` e `/metrics`.

### 3.2 Fora do escopo (não implementar)
- Alteração e exclusão de produto, e os eventos correspondentes (aguardam as pendências P-07, P-09 e P-26 do Documento de Requisitos).
- Cadastro, edição ou listagem de categorias como entidade própria. A categoria é um texto do produto.
- Campo de descrição do produto.
- Emissão de tokens, cadastro de empresas e de usuários (serviço `usuarios-service`).
- Implementação concreta das portas: banco PostgreSQL, cliente Kafka, publicador de outbox. São fornecidas por quem chama `create_app`.
- Consumo de qualquer tópico.
- Cache, rate limit (feito no gateway), CORS e TLS.

## 4. Glossário

| Termo | Definição precisa |
|---|---|
| Produto | Item do catálogo identificado por `produto_id`, com `nome`, `categoria`, `unidade`, `tipo_transporte` e, opcionalmente, `peso_unitario_kg`. |
| Categoria | Texto livre de 2 a 64 caracteres, sem tabela própria. Comparação exata, com diferença entre maiúsculas e minúsculas. |
| Unidade | Unidade de medida em que o produto é negociado. Um de: `KG`, `TON`, `UN`, `CX`, `L`. |
| Tipo de transporte | Como o produto precisa ser transportado. Um de: `GRANEL`, `REFRIGERADO`, `CARGA_SECA`, `PERIGOSO`. |
| Peso unitário | Peso de uma unidade do produto, em quilogramas. Opcional. Usado pela Logística/Transporte para calcular o peso da carga quando a unidade é `UN`, `CX` ou `L`. |
| Valor de peso | Número JSON (não booleano, não string) maior que 0, menor ou igual a 999999999.999 e com no máximo 3 casas decimais, contadas em `Decimal(str(valor))`. Na resposta e no evento, é número JSON. |
| Escopo ativo | Valor do claim `active_scope` do token: o perfil em que o usuário está atuando. Um de: `SUPPLIER` (fornecedor), `BUYER` (comprador), `CARRIER` (transportadora), `TENANT_ADMIN` (administrador da empresa). Comparação exata, em maiúsculas. Uma empresa pode ter vários escopos; o usuário escolhe o ativo no serviço de Autenticação. |
| Token | JWT assinado com RS256 pelo serviço de Autenticação, enviado no cabeçalho `Authorization: Bearer <token>`. A chave pública de cada `kid` vem da porta `ChavesPublicas` (§5.1). |
| Instante | Data/hora em UTC no formato ISO-8601 com sufixo `Z` e sem frações de segundo (ex.: `"2026-10-26T14:00:00Z"`). |
| Agora | Valor retornado por `clock.now()` (porta Clock). O serviço nunca usa o relógio do sistema. |
| Texto preenchido | String que, depois de remover espaços das pontas (`strip()`), tem pelo menos 1 caractere. |
| Correlation id | Valor do cabeçalho `X-Correlation-Id` da requisição, ou um UUID4 novo se o cabeçalho estiver ausente ou não for texto preenchido. |

## 5. Restrições técnicas

| Item | Valor obrigatório |
|---|---|
| Linguagem / versão | Python 3.12 |
| Framework | FastAPI (com Pydantic v2, se usado) |
| Dependências permitidas | Biblioteca padrão do Python, `fastapi`, `pydantic`, `starlette`, `PyJWT` (importado como `jwt`) e `cryptography` (exigida pelo PyJWT para RS256). Nenhuma outra. |
| Persistência | Somente pela porta `ProdutoRepositorio` (§5.1). Proibido guardar produtos em variáveis do módulo ou da aplicação. |
| Estrutura de arquivos | `app/__init__.py` e `app/main.py` obrigatórios; outros módulos dentro de `app/` são permitidos. |
| Ponto de entrada | `app.main.create_app(event_bus: EventBus, clock: Clock, repositorio: ProdutoRepositorio, chaves_publicas: ChavesPublicas, emissor: str = "identity-service", audiencia: str = "b2b-platform") -> fastapi.FastAPI`. `emissor` e `audiencia` são opcionais e definem o `iss` e o `aud` esperados no token (§7.1) |
| Formato de data/hora | Instante (ver glossário). |
| Formato monetário | Não se aplica (o serviço não tem valores monetários). |

### 5.1 Portas (interfaces de infraestrutura)

```python
from datetime import datetime
from typing import Callable, Protocol


class EventBus(Protocol):
    def publish(self, topic: str, key: str, message: dict) -> None: ...
    def subscribe(self, topic: str, handler: Callable[[dict], None]) -> None: ...
    def disponivel(self) -> bool: ...


class Clock(Protocol):
    def now(self) -> datetime: ...  # datetime com timezone UTC


class ChavesPublicas(Protocol):
    def obter(self, kid: str) -> object | None: ...  # chave pública RSA do kid, ou None se desconhecido


class ProdutoRepositorio(Protocol):
    def inserir(self, produto: dict) -> None: ...
    def obter(self, produto_id: str) -> dict | None: ...
    def listar(self, categoria: str | None, offset: int, limite: int) -> tuple[list[dict], int]: ...
    def disponivel(self) -> bool: ...
```

- `inserir` recebe o produto com exatamente os atributos do §6.1. `obter` e `listar` devolvem dicionários com os mesmos atributos.
- `listar` devolve `(itens, total)`: `itens` com no máximo `limite` produtos a partir da posição `offset`, na ordem de `cadastrado_em` crescente e, em empate, `produto_id` crescente; `total` é o número de produtos que atendem ao filtro. `categoria=None` significa sem filtro.
- `disponivel()` informa se a dependência responde. É usado apenas pelo `/health/ready`.
- O serviço não chama `subscribe` (não consome tópicos).
- As implementações concretas das portas são fornecidas por quem chama `create_app`; o serviço não as implementa.
- `publish` é síncrono. Ordem dentro de uma escrita: validar → `repositorio.inserir` → `event_bus.publish`. Se `inserir` lançar exceção, nada é publicado e a resposta é `500 ERRO_INTERNO`. Falhas lançadas por `publish` estão fora do escopo (o adaptador real grava o evento numa tabela de outbox e o publica depois, ADR-010 do Relatório Técnico).
- `clock.now()` sempre retorna `datetime` com fuso; se vier sem fuso, tratar como UTC.
- `chaves_publicas.obter(kid)` devolve a chave pública RSA (objeto aceito por `jwt.decode`) do `kid` informado no cabeçalho do token, ou `None` se o `kid` for desconhecido. Em produção, o adaptador usa `jwt.PyJWKClient` com o endpoint `/.well-known/jwks.json` do serviço de Autenticação e cache de 1 hora; nos testes, uma chave gerada pelo próprio teste. O serviço nunca faz requisição HTTP para obter chaves.

## 6. Modelo de domínio

### 6.1 Entidades

#### Produto
| Atributo | Tipo | Obrigatório | Restrições / origem |
|---|---|---|---|
| produto_id | string | Sim | UUID4 gerado pelo serviço no cadastro. |
| nome | string | Sim | Corpo da requisição, depois de `strip()`; 2 a 255 caracteres. |
| categoria | string | Sim | Corpo da requisição, depois de `strip()`; 2 a 64 caracteres. |
| unidade | enum | Sim | Corpo da requisição; um de `KG`, `TON`, `UN`, `CX`, `L`. |
| tipo_transporte | enum | Sim | Corpo da requisição; um de `GRANEL`, `REFRIGERADO`, `CARGA_SECA`, `PERIGOSO`. |
| peso_unitario_kg | valor de peso ou `null` | Sim (pode ser `null`) | Corpo da requisição; ausente ou `null` → `null`. |
| cadastrado_por_empresa_id | string | Sim | Claim `tenant_id` do token. |
| cadastrado_por_usuario_id | string | Sim | Claim `sub` do token. |
| cadastrado_em | instante | Sim | `clock.now()` no momento do cadastro. |

### 6.2 Estados e transições

Não se aplica na versão 1.0: o produto não tem estados, e alteração e exclusão estão fora do escopo (§3.2).

## 7. Contratos de interface

### 7.1 Autenticação e contexto da requisição

Rotas públicas (sem token): `/health`, `/health/ready`, `/metrics`, `/docs`, `/openapi.json`. Todas as rotas `/api/v1/...` exigem o cabeçalho `Authorization: Bearer <token>`.

Validação do token, nesta ordem (o primeiro problema encontrado define a resposta):
1. Cabeçalho `Authorization` ausente, vazio, ou que não começa com `Bearer ` seguido de texto preenchido → `401 TOKEN_AUSENTE`.
2. Token malformado; cabeçalho do token sem `kid` ou com `alg` diferente de `"RS256"`; `chaves_publicas.obter(kid)` devolvendo `None`; assinatura inválida para essa chave; `iss` ausente ou diferente de `emissor`; `aud` ausente ou que não contém `audiencia` (`aud` pode ser texto ou lista); ou claims inválidos: `sub` precisa ser texto preenchido, `active_scope`, quando presente e não nulo, precisa ser um dos quatro escopos do glossário, `tenant_id`, quando presente e não nulo, precisa ser string, e `exp` precisa ser inteiro → `401 TOKEN_INVALIDO`. Se `chaves_publicas.obter(kid)` lançar exceção (serviço de chaves indisponível) → `503 DEPENDENCIA_INDISPONIVEL`, e não 401, para que a tela não encerre a sessão do usuário por uma falha da plataforma. Decodificar sempre com `algorithms=["RS256"]`, nunca aceitando o algoritmo declarado pelo próprio token. Claims extras (`group_id`, `roles`, `permissions`) são ignorados.
3. `exp` (segundos desde a época Unix, UTC) menor ou igual a `int(agora.timestamp())` → `401 TOKEN_EXPIRADO`. A verificação de expiração usa `clock.now()`, nunca o relógio do sistema (decodificar com `options={"verify_exp": False}` e comparar manualmente).
4. `tenant_id` ausente, nulo ou que não é texto preenchido, ou `active_scope` ausente ou nulo → `403 CONTEXTO_NAO_SELECIONADO`. É o token devolvido pelo login antes da escolha de empresa e escopo (`switch-context` do serviço de Autenticação): ele é válido, mas ainda não diz em nome de qual empresa e perfil o usuário age.

Toda resposta, de sucesso ou de erro, inclui o cabeçalho `X-Correlation-Id` com o correlation id da requisição.

### 7.2 API REST

| ID | Método | Rota | Perfis | Sucesso | Erros possíveis (na ordem de verificação) |
|---|---|---|---|---|---|
| API-01 | GET | `/health` | público | 200 | — |
| API-02 | GET | `/health/ready` | público | 200 | 503 `DEPENDENCIA_INDISPONIVEL` |
| API-03 | GET | `/metrics` | público | 200 | — |
| API-04 | POST | `/api/v1/produtos` | `SUPPLIER`, `BUYER` | 201 | 401 `TOKEN_AUSENTE` → 401 `TOKEN_INVALIDO` ou 503 `DEPENDENCIA_INDISPONIVEL` → 401 `TOKEN_EXPIRADO` → 403 `CONTEXTO_NAO_SELECIONADO` → 403 `PERFIL_NAO_PERMITIDO` → 422 `DADOS_INVALIDOS` → 500 `ERRO_INTERNO` |
| API-05 | GET | `/api/v1/produtos/{produto_id}` | todos | 200 | 401, 503 e 403 `CONTEXTO_NAO_SELECIONADO` (como API-04) → 404 `PRODUTO_NAO_ENCONTRADO` |
| API-06 | GET | `/api/v1/produtos` | todos | 200 | 401, 503 e 403 `CONTEXTO_NAO_SELECIONADO` (como API-04) → 422 `PAGINACAO_INVALIDA` |

#### API-01 — Saúde
Resposta 200:
```json
{"status": "UP", "service": "produtos-service", "timestamp": "2026-10-26T14:00:00Z"}
```

#### API-02 — Prontidão
Resposta 200 quando `repositorio.disponivel()` e `event_bus.disponivel()` retornam `True`:
```json
{"status": "READY", "service": "produtos-service", "timestamp": "2026-10-26T14:00:00Z"}
```
Se qualquer um retornar `False` ou lançar exceção: `503 DEPENDENCIA_INDISPONIVEL` (formato do §10).

#### API-03 — Métricas
Resposta 200 com `Content-Type: text/plain; version=0.0.4` e uma linha por código de status já respondido pela aplicação, no formato Prometheus:
```text
# HELP http_requests_total Total de requisicoes HTTP respondidas
# TYPE http_requests_total counter
http_requests_total{service="produtos-service",status="201"} 2
http_requests_total{service="produtos-service",status="404"} 1
```
A contagem inclui todas as respostas da aplicação, exceto as do próprio `/metrics`. As linhas são ordenadas pelo código de status crescente. O contador pertence à instância criada por `create_app`.

#### API-04 — Cadastrar produto
Requisição:
```json
{"nome": "Leite integral", "categoria": "LATICINIOS", "unidade": "L", "tipo_transporte": "REFRIGERADO"}
```
`peso_unitario_kg` é opcional e, neste exemplo, não foi enviado.

Resposta 201:
```json
{
  "produto_id": "6f1d2c3b-4a59-4e6f-8a7b-9c0d1e2f3a4b",
  "nome": "Leite integral",
  "categoria": "LATICINIOS",
  "unidade": "L",
  "tipo_transporte": "REFRIGERADO",
  "peso_unitario_kg": null,
  "cadastrado_por_empresa_id": "EMP-34",
  "cadastrado_por_usuario_id": "USR-7",
  "cadastrado_em": "2026-10-26T14:00:00Z"
}
```

#### API-05 — Consultar produto
Resposta 200: o produto completo, no mesmo formato da resposta 201 da API-04.

#### API-06 — Listar produtos
Parâmetros de consulta: `page` (inteiro ≥ 1, padrão 1), `size` (inteiro de 1 a 100, padrão 10), `categoria` (opcional; se ausente ou não for texto preenchido, sem filtro; se presente, comparado depois de `strip()`).

Resposta 200:
```json
{
  "itens": [
    {
      "produto_id": "6f1d2c3b-4a59-4e6f-8a7b-9c0d1e2f3a4b",
      "nome": "Leite integral",
      "categoria": "LATICINIOS",
      "unidade": "L",
      "tipo_transporte": "REFRIGERADO",
      "peso_unitario_kg": null,
      "cadastrado_por_empresa_id": "EMP-34",
      "cadastrado_por_usuario_id": "USR-7",
      "cadastrado_em": "2026-10-26T14:00:00Z"
    }
  ],
  "page": 1,
  "size": 10,
  "total": 1
}
```

### 7.3 Eventos consumidos

Nenhum.

### 7.4 Eventos publicados

Envelope comum (padrão do kit de infraestrutura, `CONTRACTS.md`):

| Campo | Valor |
|---|---|
| eventId | UUID4 novo, único por mensagem publicada |
| eventType | igual ao nome do tópico |
| eventVersion | `"1.0"` (string) |
| timestamp | instante = `clock.now()` |
| source | `"produtos-service"` |
| correlationId | correlation id da requisição que originou o evento |
| aggregateId | igual à chave de partição |
| payload | objeto específico do tópico |

| Tópico | Quando | Chave de partição | Payload |
|---|---|---|---|
| `produto_cadastrado` | Produto cadastrado (RF-01) | `produto_id` | `produtoId`, `nome`, `categoria`, `unidade`, `tipoTransporte`, `pesoUnitarioKg`, `cadastradoPor` (`empresaId`, `usuarioId`), `cadastradoEm` |

Mapeamento entre o produto (§6.1) e o payload: `produto_id` → `produtoId`; `tipo_transporte` → `tipoTransporte`; `peso_unitario_kg` → `pesoUnitarioKg` (`null` quando não informado); `cadastrado_por_empresa_id` → `cadastradoPor.empresaId`; `cadastrado_por_usuario_id` → `cadastradoPor.usuarioId`; `cadastrado_em` → `cadastradoEm`; `nome`, `categoria` e `unidade` com o mesmo nome.

Exemplo (`event_bus.publish("produto_cadastrado", "6f1d2c3b-4a59-4e6f-8a7b-9c0d1e2f3a4b", mensagem)`):
```json
{
  "eventId": "3f0c2a8e-6a1b-4f4e-9a7d-1c2b3d4e5f60",
  "eventType": "produto_cadastrado",
  "eventVersion": "1.0",
  "timestamp": "2026-10-26T14:00:00Z",
  "source": "produtos-service",
  "correlationId": "d3b07384-d113-4f9e-8c65-27a36c8d76e4",
  "aggregateId": "6f1d2c3b-4a59-4e6f-8a7b-9c0d1e2f3a4b",
  "payload": {
    "produtoId": "6f1d2c3b-4a59-4e6f-8a7b-9c0d1e2f3a4b",
    "nome": "Leite integral",
    "categoria": "LATICINIOS",
    "unidade": "L",
    "tipoTransporte": "REFRIGERADO",
    "pesoUnitarioKg": null,
    "cadastradoPor": {"empresaId": "EMP-34", "usuarioId": "USR-7"},
    "cadastradoEm": "2026-10-26T14:00:00Z"
  }
}
```

## 8. Requisitos funcionais

Nos critérios abaixo, "token de X" significa um token válido (§7.1) com `active_scope` = X, `iss` = `"identity-service"`, `aud` = `"b2b-platform"`, `tenant_id` = `"EMP-34"`, `sub` = `"USR-7"` e `exp` uma hora depois de agora, salvo indicação em contrário. O relógio está em `2026-10-26T14:00:00Z`.

### RF-01 — Cadastrar produto
- **Prioridade:** Must
- **Enunciado (EARS):** Quando uma empresa com perfil `SUPPLIER` ou `BUYER` enviar um produto válido para a API-04, o serviço deve gravá-lo e publicar `produto_cadastrado`.
- **Regras aplicáveis:** RN-01, RN-02, RN-03, RN-04, RN-08
- **Interface:** API-04, tópico `produto_cadastrado`

**Critérios de aceitação**
```gherkin
# CA-01
Cenário: Fornecedor cadastra produto
  Dado um token de "SUPPLIER"
  Quando envia POST /api/v1/produtos com nome "Leite integral", categoria "LATICINIOS", unidade "L" e tipo_transporte "REFRIGERADO"
  Então a resposta é 201 com produto_id UUID4, nome "Leite integral", categoria "LATICINIOS", unidade "L", tipo_transporte "REFRIGERADO", peso_unitario_kg null, cadastrado_por_empresa_id "EMP-34", cadastrado_por_usuario_id "USR-7" e cadastrado_em "2026-10-26T14:00:00Z"
  E GET /api/v1/produtos/{produto_id} retorna 200 com o mesmo corpo

# CA-02
Cenário: Comprador também cadastra produto
  Dado um token de "BUYER"
  Quando envia POST /api/v1/produtos com nome "Soja em grãos", categoria "GRAOS", unidade "TON" e tipo_transporte "GRANEL"
  Então a resposta é 201

# CA-03
Cenário: Perfis sem permissão de cadastro
  Dado um token de "CARRIER" e, separadamente, um token de "TENANT_ADMIN"
  Quando cada um envia POST /api/v1/produtos com um corpo válido
  Então as duas respostas são 403 com codigo "PERFIL_NAO_PERMITIDO"
  E nenhum produto é gravado e nenhuma mensagem é publicada

# CA-04
Cenário: Dados inválidos (partição de equivalência)
  Dado um token de "SUPPLIER"
  Quando envia POST /api/v1/produtos com cada um dos corpos:
    | caso                         | corpo                                                                                   |
    | nome com 1 caractere         | {"nome": "L", "categoria": "LATICINIOS", "unidade": "L", "tipo_transporte": "REFRIGERADO"} |
    | nome só com espaços          | {"nome": "   ", "categoria": "LATICINIOS", "unidade": "L", "tipo_transporte": "REFRIGERADO"} |
    | categoria ausente            | {"nome": "Leite", "unidade": "L", "tipo_transporte": "REFRIGERADO"}                     |
    | unidade fora da lista        | {"nome": "Leite", "categoria": "LATICINIOS", "unidade": "litro", "tipo_transporte": "REFRIGERADO"} |
    | tipo_transporte fora da lista| {"nome": "Leite", "categoria": "LATICINIOS", "unidade": "L", "tipo_transporte": "AEREO"} |
    | nome numérico                | {"nome": 123, "categoria": "LATICINIOS", "unidade": "L", "tipo_transporte": "REFRIGERADO"} |
    | peso zero                    | o corpo válido do CA-01 com "peso_unitario_kg": 0                                       |
    | peso negativo                | o corpo válido do CA-01 com "peso_unitario_kg": -1                                      |
    | peso como texto              | o corpo válido do CA-01 com "peso_unitario_kg": "1.5"                                   |
    | peso booleano                | o corpo válido do CA-01 com "peso_unitario_kg": true                                    |
    | peso com 4 casas decimais    | o corpo válido do CA-01 com "peso_unitario_kg": 1.0005                                  |
    | peso acima do máximo         | o corpo válido do CA-01 com "peso_unitario_kg": 1000000000                              |
    | corpo não é objeto           | ["Leite"]                                                                               |
    | JSON malformado              | {"nome": "Leite",                                                                        |
  Então cada resposta é 422 com codigo "DADOS_INVALIDOS"
  E nenhum produto é gravado e nenhuma mensagem é publicada

# CA-05
Cenário: Espaços nas pontas são removidos e campos extras são ignorados
  Dado um token de "SUPPLIER" com tenant_id "EMP-34"
  Quando envia POST /api/v1/produtos com nome "  Leite integral  ", categoria " LATICINIOS ", unidade "L", tipo_transporte "REFRIGERADO" e cadastrado_por_empresa_id "EMP-99"
  Então a resposta é 201 com nome "Leite integral", categoria "LATICINIOS" e cadastrado_por_empresa_id "EMP-34"

# CA-06
Cenário: Falha do repositório
  Dado um token de "SUPPLIER" e um repositório cujo inserir lança exceção
  Quando envia POST /api/v1/produtos com um corpo válido
  Então a resposta é 500 com codigo "ERRO_INTERNO"
  E nenhuma mensagem é publicada

# CA-28
Cenário: Peso unitário opcional (valor-limite)
  Dado um token de "SUPPLIER"
  Quando envia POST /api/v1/produtos com nome "Caixa de leite", categoria "LATICINIOS", unidade "CX", tipo_transporte "REFRIGERADO" e peso_unitario_kg 12.35
  Então a resposta é 201 com peso_unitario_kg 12.35
  E GET /api/v1/produtos/{produto_id} retorna 200 com o mesmo corpo
  E o payload da mensagem publicada tem pesoUnitarioKg 12.35
  Quando envia o mesmo corpo com peso_unitario_kg null
  Então a resposta é 201 com peso_unitario_kg null e o payload publicado tem pesoUnitarioKg null
  Quando envia o mesmo corpo com peso_unitario_kg 0.001, e depois com 999999999.999
  Então as duas respostas são 201, com peso_unitario_kg igual ao valor enviado
```

### RF-02 — Consultar produto
- **Prioridade:** Must
- **Enunciado (EARS):** Quando um usuário autenticado consultar a API-05 com um `produto_id` existente, o serviço deve retornar o produto.
- **Regras aplicáveis:** RN-05
- **Interface:** API-05

**Critérios de aceitação**
```gherkin
# CA-07
Cenário: Consulta de produto existente por qualquer perfil
  Dado o produto do CA-01 cadastrado
  Quando um token de "CARRIER" consulta GET /api/v1/produtos/{produto_id}
  Então a resposta é 200 com o mesmo corpo da resposta 201 do CA-01

# CA-08
Cenário: Produto inexistente
  Dado um token de "BUYER"
  Quando consulta GET /api/v1/produtos/PROD-INEXISTENTE
  Então a resposta é 404 com codigo "PRODUTO_NAO_ENCONTRADO"
```

### RF-03 — Listar produtos
- **Prioridade:** Must
- **Enunciado (EARS):** Quando um usuário autenticado consultar a API-06, o serviço deve retornar a página pedida, na ordem de cadastro, com o total de produtos que atendem ao filtro.
- **Regras aplicáveis:** RN-05, RN-06
- **Interface:** API-06

**Critérios de aceitação**
```gherkin
# CA-09
Cenário: Paginação e filtro por categoria
  Dado 3 produtos cadastrados nesta ordem: "Leite" (LATICINIOS) às 14:00:00Z, "Queijo" (LATICINIOS) às 14:00:01Z e "Soja" (GRAOS) às 14:00:02Z
  Quando um token de "BUYER" consulta GET /api/v1/produtos?page=1&size=2
  Então a resposta é 200 com itens "Leite" e "Queijo", page 1, size 2 e total 3
  Quando consulta GET /api/v1/produtos?page=2&size=2
  Então a resposta é 200 com o item "Soja" e total 3
  Quando consulta GET /api/v1/produtos?categoria=LATICINIOS
  Então a resposta é 200 com itens "Leite" e "Queijo", page 1, size 10 e total 2

# CA-10
Cenário: Página além do fim
  Dado os 3 produtos do CA-09
  Quando consulta GET /api/v1/produtos?page=5&size=2
  Então a resposta é 200 com itens [] e total 3

# CA-11
Cenário: Parâmetros de paginação inválidos (valor-limite)
  Dado um token de "BUYER"
  Quando consulta GET /api/v1/produtos com cada um dos parâmetros: size=101, size=0, page=0, page=abc, size=1.5
  Então cada resposta é 422 com codigo "PAGINACAO_INVALIDA"
  Quando consulta GET /api/v1/produtos?size=100
  Então a resposta é 200
```

### RF-04 — Publicar evento de produto cadastrado
- **Prioridade:** Must
- **Enunciado (EARS):** Quando um produto for gravado com sucesso, o serviço deve publicar uma mensagem em `produto_cadastrado` com chave igual ao `produto_id`.
- **Regras aplicáveis:** RN-03, RN-04, RN-07
- **Interface:** tópico `produto_cadastrado`

**Critérios de aceitação**
```gherkin
# CA-12
Cenário: Evento publicado com envelope e chave
  Dado um token de "SUPPLIER" e o cabeçalho X-Correlation-Id "corr-001"
  Quando o CA-01 é executado
  Então exatamente 1 mensagem é publicada, no tópico "produto_cadastrado", com key igual ao produto_id da resposta
  E a mensagem tem eventId UUID4, eventType "produto_cadastrado", eventVersion "1.0", timestamp "2026-10-26T14:00:00Z", source "produtos-service", correlationId "corr-001" e aggregateId igual ao produto_id
  E o payload tem produtoId, nome "Leite integral", categoria "LATICINIOS", unidade "L", tipoTransporte "REFRIGERADO", pesoUnitarioKg null, cadastradoPor {"empresaId": "EMP-34", "usuarioId": "USR-7"} e cadastradoEm "2026-10-26T14:00:00Z"

# CA-13
Cenário: Requisição recusada não publica
  Quando os cenários CA-03, CA-04 e CA-14 a CA-17 são executados
  Então nenhuma mensagem é publicada
```

### RF-05 — Autenticar e autorizar requisições
- **Prioridade:** Must
- **Enunciado (EARS):** Se uma requisição a uma rota `/api/v1/...` não tiver token válido e não expirado, então o serviço deve recusá-la com 401 e o código correspondente (§7.1), sem executar a operação.
- **Regras aplicáveis:** RN-01, RN-04
- **Interface:** API-04, API-05, API-06

**Critérios de aceitação**
```gherkin
# CA-14
Cenário: Token ausente
  Quando POST /api/v1/produtos é enviado sem o cabeçalho Authorization, e depois com "Authorization: Basic abc", e depois com "Authorization: Bearer "
  Então as três respostas são 401 com codigo "TOKEN_AUSENTE"

# CA-15
Cenário: Token com assinatura de outra chave
  Dado um token de "SUPPLIER" assinado com uma chave RSA diferente da que chaves_publicas devolve para o kid do token
  Quando envia POST /api/v1/produtos com um corpo válido
  Então a resposta é 401 com codigo "TOKEN_INVALIDO"

# CA-16
Cenário: Claims inválidos
  Dado tokens, cada um com um problema: active_scope "GERENTE"; active_scope "supplier" (minúsculas); sub ""; assinado com HS256 em vez de RS256; kid desconhecido (chaves_publicas.obter devolve None)
  Quando cada um consulta GET /api/v1/produtos
  Então cada resposta é 401 com codigo "TOKEN_INVALIDO"

# CA-17
Cenário: Token expirado no limite (valor-limite)
  Dado um token de "SUPPLIER" com exp igual a 2026-10-26T14:00:00Z e o relógio em 2026-10-26T14:00:00Z
  Quando consulta GET /api/v1/produtos
  Então a resposta é 401 com codigo "TOKEN_EXPIRADO"
  Dado o mesmo token e o relógio em 2026-10-26T13:59:59Z
  Quando consulta GET /api/v1/produtos
  Então a resposta é 200

# CA-29
Cenário: Emissor e audiência do token
  Dado tokens de "SUPPLIER", cada um com um problema: iss "falsificador"; aud "outro-sistema"; sem iss; sem aud
  Quando cada um consulta GET /api/v1/produtos
  Então cada resposta é 401 com codigo "TOKEN_INVALIDO"
  Dado um token de "SUPPLIER" com aud ["b2b-platform", "outro-sistema"]
  Quando consulta GET /api/v1/produtos
  Então a resposta é 200

# CA-30
Cenário: Token sem empresa ou sem escopo selecionado
  Dado tokens válidos, cada um sem contexto: sem tenant_id e sem active_scope (token do login); tenant_id ""; sem active_scope
  Quando cada um envia POST /api/v1/produtos com um corpo válido
  Então cada resposta é 403 com codigo "CONTEXTO_NAO_SELECIONADO"
  E nenhum produto é gravado e nenhuma mensagem é publicada
  Dado um token sem tenant_id e sem active_scope, com exp igual a 2026-10-26T14:00:00Z
  Quando consulta GET /api/v1/produtos
  Então a resposta é 401 com codigo "TOKEN_EXPIRADO"

# CA-31
Cenário: Serviço de chaves indisponível
  Dado uma porta chaves_publicas cuja obter lança exceção
  Quando envia POST /api/v1/produtos com um corpo válido
  Então a resposta é 503 com codigo "DEPENDENCIA_INDISPONIVEL"
  E nenhum produto é gravado e nenhuma mensagem é publicada
```

### RF-06 — Propagar o identificador de correlação
- **Prioridade:** Should
- **Enunciado (EARS):** O serviço deve devolver o correlation id da requisição no cabeçalho `X-Correlation-Id` de toda resposta, no campo `correlationId` de todo erro e no `correlationId` de todo evento publicado.
- **Regras aplicáveis:** RN-07
- **Interface:** todas

**Critérios de aceitação**
```gherkin
# CA-18
Cenário: Correlation id informado
  Quando GET /api/v1/produtos/PROD-INEXISTENTE é enviado com um token de "BUYER" e X-Correlation-Id "corr-404"
  Então a resposta é 404, tem o cabeçalho X-Correlation-Id "corr-404" e o corpo tem correlationId "corr-404"

# CA-19
Cenário: Correlation id ausente ou vazio
  Quando GET /health é enviado sem X-Correlation-Id, e depois com X-Correlation-Id "   "
  Então cada resposta tem o cabeçalho X-Correlation-Id com um UUID4 novo
```

### RF-07 — Saúde, prontidão e métricas
- **Prioridade:** Must
- **Enunciado (EARS):** O serviço deve responder às API-01, API-02 e API-03 sem autenticação, conforme o §7.2.
- **Regras aplicáveis:** —
- **Interface:** API-01, API-02, API-03

**Critérios de aceitação**
```gherkin
# CA-20
Cenário: Saúde e prontidão com dependências disponíveis
  Quando GET /health é enviado sem token
  Então a resposta é 200 com status "UP", service "produtos-service" e timestamp "2026-10-26T14:00:00Z"
  Quando GET /health/ready é enviado com repositório e barramento disponíveis
  Então a resposta é 200 com status "READY"

# CA-21
Cenário: Dependência indisponível
  Dado um barramento cujo disponivel() retorna False
  Quando GET /health/ready é enviado
  Então a resposta é 503 com codigo "DEPENDENCIA_INDISPONIVEL"
  E GET /health continua respondendo 200

# CA-22
Cenário: Métricas por código de status
  Dado uma aplicação nova
  Quando são feitas 2 requisições do CA-01 (201) e 1 do CA-08 (404)
  Então GET /metrics responde 200 contendo as linhas http_requests_total{service="produtos-service",status="201"} 2 e http_requests_total{service="produtos-service",status="404"} 1
```

## 9. Regras de negócio

| ID | Regra | Exemplo concreto |
|---|---|---|
| RN-01 | Apenas os perfis `SUPPLIER` e `BUYER` cadastram produtos. `CARRIER` e `TENANT_ADMIN` → 403 `PERFIL_NAO_PERMITIDO`. Todos os perfis consultam e listam. | `CARRIER` em POST → 403; `CARRIER` em GET → 200. |
| RN-02 | Corpo do cadastro: precisa ser objeto JSON; `nome` string com 2 a 255 caracteres depois de `strip()`; `categoria` string com 2 a 64 caracteres depois de `strip()`; `unidade` ∈ {`KG`, `TON`, `UN`, `CX`, `L`}; `tipo_transporte` ∈ {`GRANEL`, `REFRIGERADO`, `CARGA_SECA`, `PERIGOSO`}. Qualquer violação, campo ausente, tipo errado, corpo não-objeto ou JSON malformado → 422 `DADOS_INVALIDOS`. Campos desconhecidos são ignorados. | `"unidade": "litro"` → 422; `"nome": "  Leite  "` → gravado como `"Leite"`. |
| RN-03 | `produto_id` (UUID4), `cadastrado_por_empresa_id` (claim `tenant_id`), `cadastrado_por_usuario_id` (claim `sub`) e `cadastrado_em` (`clock.now()`) são definidos pelo serviço. Valores enviados no corpo para esses campos são ignorados. | Corpo com `cadastrado_por_empresa_id` "EMP-99" e token de "EMP-34" → gravado "EMP-34". |
| RN-04 | Requisição recusada (qualquer 4xx ou 5xx) não grava nada e não publica evento. | 422 → nenhuma mensagem. |
| RN-05 | Um `produto_id` inexistente → 404 `PRODUTO_NAO_ENCONTRADO`. | `PROD-INEXISTENTE` → 404. |
| RN-06 | Paginação: `page` inteiro ≥ 1 (padrão 1); `size` inteiro de 1 a 100 (padrão 10). Fora disso, ou não inteiro → 422 `PAGINACAO_INVALIDA`. `offset = (page − 1) × size`. Página além do fim → 200 com `itens` vazio. | `size=101` → 422; `size=100` → 200. |
| RN-07 | Nenhum evento, resposta ou log contém o token de acesso. Eventos identificam quem agiu só por `empresaId` e `usuarioId`. | Payload sem campo de token. |
| RN-08 | `peso_unitario_kg` é opcional para todas as unidades. Ausente ou `null` → gravado como `null`. Se informado, precisa ser valor de peso (glossário); caso contrário → 422 `DADOS_INVALIDOS`. O serviço não confere o peso com a unidade: para `KG` e `TON` a Logística converte a quantidade diretamente. | `"peso_unitario_kg": 12.35` → aceito; `"peso_unitario_kg": 0` → 422. |

## 10. Catálogo de erros

Formato único de erro (RFC 7807, exigido pelo kit de infraestrutura; a RFC 9457, citada pelo grupo de Autenticação, substitui a 7807 com o mesmo formato), com `Content-Type: application/problem+json`:
```json
{
  "type": "https://portal-b2b.corp/erros/produto-nao-encontrado",
  "title": "Produto Não Encontrado",
  "status": 404,
  "detail": "Produto PROD-INEXISTENTE não cadastrado.",
  "instance": "/api/v1/produtos/PROD-INEXISTENTE",
  "codigo": "PRODUTO_NAO_ENCONTRADO",
  "correlationId": "corr-404",
  "timestamp": "2026-10-26T14:00:00Z"
}
```
`type` é `https://portal-b2b.corp/erros/` seguido do `codigo` em minúsculas com `_` trocado por `-`. `title` é o da tabela abaixo. `detail` é texto livre, não vazio, em português. `instance` é o caminho da requisição, sem parâmetros de consulta. `timestamp` é `clock.now()`. `codigo` é a extensão usada pelos testes para comparação literal (a RFC 7807 permite membros de extensão).

| Código | HTTP | Title | Quando ocorre |
|---|---|---|---|
| TOKEN_AUSENTE | 401 | Não Autenticado | §7.1, item 1. |
| TOKEN_INVALIDO | 401 | Token Inválido | §7.1, item 2. |
| TOKEN_EXPIRADO | 401 | Token Expirado | §7.1, item 3. |
| CONTEXTO_NAO_SELECIONADO | 403 | Contexto Não Selecionado | §7.1, item 4. |
| PERFIL_NAO_PERMITIDO | 403 | Acesso Negado | RN-01. |
| PRODUTO_NAO_ENCONTRADO | 404 | Produto Não Encontrado | RN-05. |
| ROTA_NAO_ENCONTRADA | 404 | Rota Não Encontrada | Rota inexistente. |
| METODO_NAO_PERMITIDO | 405 | Método Não Permitido | Método não aceito pela rota. |
| DADOS_INVALIDOS | 422 | Dados Inválidos | RN-02, RN-08. |
| PAGINACAO_INVALIDA | 422 | Paginação Inválida | RN-06. |
| ERRO_INTERNO | 500 | Erro Interno | Exceção não prevista, inclusive do repositório. O `detail` não expõe a mensagem da exceção. |
| DEPENDENCIA_INDISPONIVEL | 503 | Dependência Indisponível | API-02 com dependência indisponível; §7.1, item 2 (serviço de chaves indisponível). |

Respostas fora do catálogo: nenhuma. Rota inexistente e método não permitido também usam este formato. A documentação automática do framework (`/docs`, `/openapi.json`) permanece habilitada e não faz parte da avaliação.

**Ordem de verificação:** quando mais de um erro se aplica, retorna-se o primeiro da lista. A validação do corpo e dos parâmetros **não** pode ocorrer antes das verificações 1 a 5 (não use validação automática de corpo ou de parâmetros do framework que responda antes delas; leia o corpo bruto e valide manualmente):
1. ROTA_NAO_ENCONTRADA / METODO_NAO_PERMITIDO
2. TOKEN_AUSENTE
3. TOKEN_INVALIDO / DEPENDENCIA_INDISPONIVEL (serviço de chaves)
4. TOKEN_EXPIRADO
5. CONTEXTO_NAO_SELECIONADO
6. PERFIL_NAO_PERMITIDO
7. DADOS_INVALIDOS / PAGINACAO_INVALIDA
8. PRODUTO_NAO_ENCONTRADO
9. ERRO_INTERNO

## 11. Requisitos não funcionais

| ID | Característica (ISO/IEC 25010) | Requisito | Métrica e limiar | Verificação |
|---|---|---|---|---|
| RNF-01 | Interoperabilidade | Formato único de erro. | 100% das respostas 4xx e 5xx no formato do §10, com `Content-Type` `application/problem+json` e todos os 8 campos preenchidos. | CA-23 |
| RNF-02 | Eficiência de desempenho | Leitura do catálogo em processo. | 500 requisições GET /api/v1/produtos?size=100 sequenciais, com 100 produtos cadastrados, em menos de 5 s no cliente de teste em processo. A meta da plataforma (p95 ≤ 500 ms com 200 requisições simultâneas, kit seção 10.2) é verificada pelo Grupo de Teste com k6 no ambiente integrado. | CA-24 |
| RNF-03 | Manutenibilidade — modularidade | Sem estado de negócio fora do repositório. | Duas aplicações criadas por `create_app` com o **mesmo** repositório veem os mesmos produtos; com repositórios diferentes, não compartilham produtos. | CA-25 |
| RNF-04 | Portabilidade | Somente dependências permitidas (§5). | Nenhum `import` fora da biblioteca padrão, `fastapi`, `pydantic`, `starlette`, `jwt` ou do próprio pacote `app`. | CA-26 |
| RNF-05 | Segurança — confidencialidade | Token nunca sai do serviço. | 0 ocorrências da string do token nas mensagens publicadas e nos registros de log produzidos durante o CA-01. | CA-27 |

```gherkin
# CA-23
Cenário: Formato de erro, inclusive para rota e método fora do contrato
  Quando GET /api/v1/inexistente é enviado com um token de "BUYER"
  Então a resposta é 404 com codigo "ROTA_NAO_ENCONTRADA"
  Quando DELETE /api/v1/produtos/PROD-1 é enviado com um token de "SUPPLIER"
  Então a resposta é 405 com codigo "METODO_NAO_PERMITIDO"
  E para cada resposta 4xx e 5xx produzida por este e pelos demais cenários de erro deste documento
  Então o Content-Type é "application/problem+json"
  E o corpo tem type, title, status, detail, instance, codigo, correlationId e timestamp, todos não vazios, status igual ao código HTTP e type igual a "https://portal-b2b.corp/erros/" seguido do codigo em minúsculas com "_" trocado por "-"

# CA-24
Cenário: Desempenho de leitura
  Dado 100 produtos cadastrados
  Quando 500 requisições GET /api/v1/produtos?size=100 são enviadas em sequência com um token de "BUYER"
  Então todas retornam 200 e o tempo total é inferior a 5 segundos

# CA-25
Cenário: Estado somente no repositório
  Dado duas aplicações criadas por create_app com o mesmo repositório
  Quando um produto é cadastrado pela primeira
  Então a segunda retorna 200 para GET /api/v1/produtos/{produto_id}
  Dado duas aplicações criadas com repositórios diferentes
  Quando um produto é cadastrado pela primeira
  Então a segunda retorna 404

# CA-26
Cenário: Dependências
  Ao inspecionar todos os arquivos .py do pacote app
  Então só há imports da biblioteca padrão, fastapi, pydantic, starlette, jwt ou do próprio app

# CA-27
Cenário: Token não vaza
  Quando o CA-01 é executado capturando os logs
  Então a string do token não aparece em nenhuma mensagem publicada nem em nenhum registro de log
```

## 12. Matriz de rastreabilidade

| Requisito | Regras | Interfaces | Critérios de aceitação |
|---|---|---|---|
| RF-01 | RN-01, RN-02, RN-03, RN-04, RN-08 | API-04, `produto_cadastrado` | CA-01 a CA-06, CA-28 |
| RF-02 | RN-05 | API-05 | CA-07, CA-08 |
| RF-03 | RN-05, RN-06 | API-06 | CA-09 a CA-11 |
| RF-04 | RN-03, RN-04, RN-07, RN-08 | `produto_cadastrado` | CA-12, CA-13, CA-28 |
| RF-05 | RN-01, RN-04 | API-04 a API-06 | CA-14 a CA-17, CA-29 a CA-31 |
| RF-06 | RN-07 | todas | CA-18, CA-19 |
| RF-07 | — | API-01 a API-03 | CA-20 a CA-22 |
| RNF-01 a RNF-05 | — | todas | CA-23 a CA-27 |

Exceções justificadas à regra de um cenário de erro por RF: nenhuma. Atributos da entidade (§6.1) e campos da resposta da API-04 são idênticos. O payload do evento usa nomes em camelCase, com o mapeamento do §7.4.

## 13. Premissas, decisões e questões em aberto

| ID | Tipo | Descrição | Decisão |
|---|---|---|---|
| Q-01 | Decisão | Validação do token e nomes dos claims (P-04, P-33). | No serviço, com RS256 e a chave pública do `kid` obtida pela porta `ChavesPublicas` (JWKS do serviço de Autenticação). Claims `sub`, `tenant_id` e `active_scope`, como definido pelo grupo de Autenticação na issue #2 (2026-11-09). Substitui o HS256 com chave compartilhada do kit, que permitia a qualquer serviço emitir tokens. Versão 1.4: `iss` (`identity-service`) e `aud` (`b2b-platform`) conferidos, token sem contexto → 403 `CONTEXTO_NAO_SELECIONADO` e serviço de chaves indisponível → 503, alinhado ao grupo de Logística, que leu o código do Identity-Service (F12 do Documento de Requisitos). |
| Q-02 | Decisão | Nomes dos campos de erro: o grupo de Autenticação usa `code` e `correlation_id` (RFC 9457); o kit usa `correlationId`; esta ESP usa `codigo` e `correlationId`. | Mantidos `codigo` e `correlationId` até a turma definir um padrão único (pergunta feita na issue #2). Se mudar, esta ESP muda de versão. |
| Q-03 | Decisão | O comprador pode cadastrar produto? O professor disse que sim (aula 2, 1:17 a 1:49); o guia do kit restringe o comprador (P-30). | `BUYER` cadastra (RN-01). Confirmado pelo professor em 2026-11-12: fornecedor e comprador cadastram produto. |
| Q-04 | Decisão | Permissões do `TENANT_ADMIN` (P-07). | Na versão 1.0, `TENANT_ADMIN` consulta e lista, mas não cadastra. |
| Q-05 | Decisão | Listas de unidade e de tipo de transporte (P-06). | As sugeridas pelo boilerplate do kit, confirmadas pelo grupo de Logística/Transporte em 2026-11-10 (são as que ele usa na cotação e no cadastro de veículos). |
| Q-06 | Decisão | Alteração e exclusão de produto (P-07, P-09, P-26). | Fora do escopo da versão 1.0 (§3.2). |
| Q-07 | Decisão | Formato de erro: o exemplo do Grupo de Teste usa `{"erro": {...}}`, e o kit exige RFC 7807. | RFC 7807 com o membro de extensão `codigo` (§10), que permite comparação literal nos testes. |
| Q-08 | Decisão | Persistência em memória (como no exemplo ESP-NEG-001) ou banco. | Porta `ProdutoRepositorio` (§5.1). O Grupo de Teste injeta uma implementação em memória; em produção, o adaptador usa o schema `produtos` do PostgreSQL. Atende ao requisito de serviços sem estado em memória do kit. |
| Q-09 | Decisão | Falha de `publish`. | Fora do escopo; o adaptador real grava o evento numa tabela de outbox e o publica depois (Relatório Técnico, ADR-010). |
| Q-10 | Premissa | O gateway encaminha as requisições `/api/v1/produtos` ao serviço sem alterar o cabeçalho `Authorization`. | Confirmado pela configuração do gateway do kit. |
| Q-11 | Decisão | Peso da carga quando a unidade não é de massa. A Logística pediu um campo opcional de peso unitário (2026-11-10). | Campo opcional `peso_unitario_kg` (RN-08), com até 3 casas decimais (precisão de 1 grama). O cálculo do peso da carga (`pesoKg` do `pedido_criado`) é do grupo de Pedidos. |

### 13.1 Casos de borda obrigatórios

| Caso de borda | Decisão |
|---|---|
| String vazia ou só com espaços em campos obrigatórios | Inválida (texto preenchido, glossário). Strings válidas são gravadas depois de `strip()`. |
| Cabeçalho opcional presente porém vazio | `X-Correlation-Id` vazio ou só com espaços equivale a ausente (gera UUID4). `Authorization` vazio → `TOKEN_AUSENTE`. |
| Mensagem duplicada **e** inválida (qual regra vence: duplicidade ou validação?) | Não se aplica: o serviço não consome mensagens. |
| Campo de chave/ID com tipo inesperado (ex.: número no lugar de string) | No corpo da API-04, qualquer campo com tipo diferente de string → 422 `DADOS_INVALIDOS`. No caminho da API-05, o `produto_id` é sempre string; valor inexistente → 404. |
| Data/hora sem fuso horário | `clock.now()` sem fuso é tratado como UTC. |
| Falha da porta de publicação / banco | Banco: `500 ERRO_INTERNO`, sem publicar. Publicação: fora do escopo (Q-09). |
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
| 1.0 | 2026-10-26 | Grupo de Fornecimento e Produtos | Criação a partir do modelo ERS-LLM v1.2 do Grupo de Teste, do Documento de Requisitos v0.4 e do kit de infraestrutura. |
| 1.1 | 2026-11-10 | Grupo de Fornecimento e Produtos | Token RS256 validado com a porta `ChavesPublicas` (JWKS do serviço de Autenticação) no lugar de HS256 e `jwt_secret`; claims `tenant_id` e `active_scope`; escopos `SUPPLIER`, `BUYER`, `CARRIER` e `TENANT_ADMIN`; novos casos de token inválido (HS256, kid desconhecido, escopo em minúsculas). Motivo: definições do grupo de Autenticação nas issues #2 e #13. |
| 1.2 | 2026-11-10 | Grupo de Fornecimento e Produtos | Campo opcional `peso_unitario_kg` no produto e `pesoUnitarioKg` no evento (RN-08, CA-04, CA-28, Q-11). Listas de unidade e de tipo de transporte confirmadas (Q-05). Motivo: resposta do grupo de Logística/Transporte sobre P-06 e P-27. |
| 1.3 | 2026-11-11 | Grupo de Fornecimento e Produtos | Texto sobre a falha de `publish` ajustado ao outbox implementado no adaptador (ADR-010): o evento é gravado numa tabela e publicado depois. Sem mudança de comportamento nem de critérios de aceitação. |
| 1.4 | 2026-11-12 | Grupo de Fornecimento e Produtos | Token: `iss` e `aud` conferidos (parâmetros opcionais `emissor` e `audiencia` em `create_app`); token sem empresa ou escopo → 403 `CONTEXTO_NAO_SELECIONADO` (§7.1, item 4); serviço de chaves indisponível → 503 `DEPENDENCIA_INDISPONIVEL`. CA-29 a CA-31 novos; o caso "sem tenant_id" saiu do critério de token inválido e passou ao CA-30. Motivo: formato do token do Identity-Service relatado pelo grupo de Logística (F12). |
| 1.5 | 2026-11-12 | Grupo de Fornecimento e Produtos | Q-03 confirmada pelo professor (comprador cadastra produto). Só texto, sem mudança de comportamento nem de critérios. |
