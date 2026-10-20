# Artefato: Modelo do Documento de Requisitos + Instruções de Preenchimento

**Integrantes:** Daniel Carvalho Coutinho · Gabriel Vicentte dos Santos Ferreira · Pedro Cardoso da Mata · Rafael de Castro


Este é o **artefato 2 de 4** da entrega. Contém:

- **Parte A** — o modelo (template) do documento de requisitos em Markdown, para copiar por funcionalidade/produto.
- **Parte B** — as instruções de preenchimento, com exemplos de requisitos bons e ruins.

O modelo foi desenhado para ser **fonte de verdade de uma LLM**. Cada seção existe para eliminar uma classe específica de ambiguidade que, quando ausente, derruba a conformidade.

---

# PARTE A — Modelo do documento de requisitos

> Copie tudo dentro do bloco abaixo para um novo arquivo por funcionalidade. Preencha os campos entre colchetes. Remova as instruções em itálico após preencher.

```markdown
---
title: "[Nome do Sistema ou Funcionalidade]"
version: "1.0"
status: "Rascunho | Em validação | Aprovado | Obsoleto"
date_created: "AAAA-MM-DD"
date_updated: "AAAA-MM-DD"
owner: "[Equipe ou responsável]"
llm_target: "[Modelo/ferramenta usada na geração]"
frozen: "false"   # vira "true" quando a versão é congelada para geração
---

# 1. Objetivo e Escopo

## 1.1 Problema de negócio
[O problema real a resolver, em 2 a 5 frases.]

## 1.2 Objetivo do produto
[O resultado que o software deve entregar e para quem.]

## 1.3 Incluído no escopo
- [Funcionalidade incluída]
- [Funcionalidade incluída]

## 1.4 Não incluído no escopo
- [Funcionalidade explicitamente excluída]
- [Funcionalidade explicitamente excluída]

## 1.5 Atores e partes interessadas
| ID | Ator | Papel | Necessidade principal |
|---|---|---|---|
| AT-01 | [Ex.: Cliente] | [Usuário final] | [Necessidade] |
| AT-02 | [Ex.: Administrador] | [Gestão] | [Necessidade] |

# 2. Glossário

| Termo | Definição |
|---|---|
| [Termo] | [Definição objetiva no contexto deste sistema] |

# 3. Regras de Negócio

| ID | Regra | Condição de aplicação | Exemplo | Prioridade | Veto? |
|---|---|---|---|---|---|
| RN-01 | [Regra objetiva do domínio] | [Quando se aplica] | [Exemplo concreto] | Alta | Não |
| RN-02 | [Regra objetiva do domínio] | [Quando se aplica] | [Exemplo concreto] | Média | Não |

> A coluna "Veto?" marca regras cuja violação invalida a conformidade
> (segurança, autorização, integridade, privacidade, regra financeira).

# 4. Requisitos Funcionais

| ID | Nome | Descrição | Prioridade | Dependências |
|---|---|---|---|---|
| RF-01 | [Nome] | O sistema deve [ação observável]. | Alta | [RN-01 ou Nenhuma] |
| RF-02 | [Nome] | O sistema deve [ação observável]. | Média | [Dependências] |

## 4.1 Critérios de Aceitação

> Cada critério recebe ID PRÓPRIO (RF-01/CA-01). A conformidade é medida
> por critério ponderado, não por requisito. Marque prioridade e veto por critério.

### RF-01 — [Nome do requisito]

- **RF-01/CA-01** — Prioridade: Alta — Veto: Não

```gherkin
Scenario: [Cenário principal]
Given [contexto inicial]
When [ação executada]
Then [resultado esperado]
And [resultado complementar]
```

- **RF-01/CA-02** — Prioridade: Alta — Veto: Sim (autorização)

```gherkin
Scenario: [Caso de erro / borda / segurança]
Given [contexto inicial]
When [ação não autorizada]
Then [erro ou bloqueio esperado, ex.: HTTP 403]
```

### RF-02 — [Nome do requisito]

- **RF-02/CA-01** — Prioridade: Média — Veto: Não

```gherkin
Scenario: [Nome do cenário]
Given [contexto inicial]
When [ação executada]
Then [resultado esperado]
```

# 5. Requisitos Não Funcionais

| ID | Categoria | Requisito | Métrica | Método de verificação | Veto? |
|---|---|---|---|---|---|
| RNF-01 | Desempenho | [Requisito] | [Ex.: p95 ≤ 2 s p/ 10k registros] | [Teste de carga] | Não |
| RNF-02 | Segurança | [Requisito] | [Ex.: acesso negado → HTTP 403] | [Teste automatizado] | Sim |
| RNF-03 | Usabilidade | [Requisito] | [Ex.: ≤ 5 campos obrigatórios] | [Inspeção/teste de UI] | Não |
| RNF-04 | Privacidade | [Requisito] | [Ex.: sem dado sensível em log] | [Inspeção de logs] | Sim |

# 6. Contratos de Entrada e Saída

## 6.1 [Nome da operação, endpoint ou tela]

### Finalidade
[O que a operação realiza.]

### Entrada
```json
{
  "campoObrigatorio": "valor de exemplo",
  "campoOpcional": "valor de exemplo"
}
```

### Regras de validação
- `campoObrigatorio` é obrigatório e deve possuir [formato/limite/tipo].
- `campoOpcional`, quando informado, deve possuir [regra].

### Saída de sucesso
```json
{ "id": "identificador", "status": "sucesso", "mensagem": "Operação concluída" }
```

### Saída de erro
```json
{ "status": "erro", "codigo": "CODIGO_DE_ERRO", "mensagem": "Descrição objetiva" }
```

### Códigos de erro
| Código | Condição | Comportamento esperado |
|---|---|---|
| CAMPO_OBRIGATORIO | Campo obrigatório ausente | Retornar erro; não persistir |
| FORMATO_INVALIDO | Formato inválido | Retornar erro indicando o campo |
| NAO_AUTORIZADO | Usuário sem permissão | Retornar erro de autorização (HTTP 403) |

# 7. Fluxos

## 7.1 Fluxo principal: [Nome]
1. [Ator] inicia [ação].
2. O sistema valida [dados/permissão].
3. O sistema aplica [regras de negócio].
4. O sistema persiste/processa [informação].
5. O sistema apresenta [resultado].

## 7.2 Fluxos alternativos e casos de borda
| ID | Situação | Comportamento esperado |
|---|---|---|
| CB-01 | [Dado inválido] | [Mensagem e ação esperada] |
| CB-02 | [Sem permissão] | [Bloquear e registrar, se aplicável] |
| CB-03 | [Registro inexistente] | [Erro controlado] |

# 8. Dados e Modelo de Domínio

## 8.1 Entidades
| Entidade | Campo | Tipo | Obrigatório | Regra |
|---|---|---|---|---|
| [Entidade] | id | UUID/String/Integer | Sim | Identificador único |
| [Entidade] | nome | String | Sim | Máx. 100 caracteres |
| [Entidade] | criadoEm | DateTime | Sim | Gerado pelo sistema |

## 8.2 Relacionamentos
- [Entidade A] possui [tipo de relação] com [Entidade B].
- [Regra de integridade/exclusão].

# 9. Limites e Guardrails

## Always (sempre fazer)
- [Comportamento obrigatório]

## Ask First (perguntar antes de decidir)
- [Decisão que não deve ser assumida]

## Never (nunca fazer)
- [Comportamento proibido / dado que não pode expor / ação fora do escopo]

# 10. Plano de Testes e Rastreabilidade

| Critério | Cenário | Tipo de teste | Nome do teste | Peso | Veto | Resultado esperado | Status |
|---|---|---|---|---:|---|---|---|
| RF-01/CA-01 | Cenário principal | Unitário/Integração/E2E | test_... | 3 | Não | [Resultado] | Não executado |
| RF-01/CA-02 | Acesso não autorizado | Integração | test_... | 3 | Sim | HTTP 403 | Não executado |
| RNF-01 | Desempenho | Carga | test_... | 2 | Não | p95 ≤ 2 s | Não executado |

## 10.1 Comandos de teste
```bash
[instalar dependências]
[executar testes]
[gerar relatório de cobertura]
```

## 10.2 Critério de aprovação
- 100% dos critérios de prioridade Alta possuem ≥ 1 teste.
- 100% dos critérios obrigatórios foram executados.
- Conformidade ponderada média (≥ 3 execuções) ≥ 85%.
- Nenhum critério de veto reprovado.

# 11. Decisões, Dúvidas e Mudanças

| ID | Data | Tipo | Descrição | Impacto | Responsável | Status |
|---|---|---|---|---|---|---|
| DEC-01 | AAAA-MM-DD | Decisão | [Decisão tomada] | [RF afetados] | [Nome] | Aprovada |
| DUV-01 | AAAA-MM-DD | Dúvida | [Pergunta ao cliente] | [Impacto] | [Nome] | Pendente |
| MUD-01 | AAAA-MM-DD | Mudança | [Mudança aprovada] | [RF afetados] | [Nome] | Implementada |
```

---

# PARTE B — Instruções de preenchimento

## B.1 Ordem recomendada de preenchimento

1. Problema de negócio e objetivo do produto.
2. Escopo e não escopo.
3. Atores e glossário.
4. Regras de negócio.
5. Requisitos funcionais.
6. Critérios de aceitação (um ID por critério).
7. Requisitos não funcionais.
8. Contratos de entrada e saída.
9. Fluxos e casos de borda.
10. Dados e modelo de domínio.
11. Guardrails.
12. Plano de testes e rastreabilidade.
13. Decisões, dúvidas e mudanças.

## B.2 Linguagem: use verbos observáveis, evite termos vagos

**Use:** cadastrar · consultar · criar · editar · excluir · calcular · validar · bloquear · notificar · registrar · retornar.

**Evite:** rápido · intuitivo · fácil · seguro · moderno · adequado · sempre que possível · preferencialmente.

Troque todo termo vago por número, condição e comportamento verificável.

| ❌ Vago | ✅ Verificável |
|---|---|
| Deve ser rápido | Responde em ≤ 2 s no p95 para 10.000 registros |
| Deve ser seguro | Acesso não autorizado retorna HTTP 403 e é registrado em auditoria |
| Deve ser fácil de usar | Cadastro concluído com ≤ 5 campos obrigatórios |

## B.3 Como escrever requisitos funcionais

Padrão: `O sistema deve [ação] [objeto] [condição], produzindo [resultado verificável].`

- ❌ **Ruim:** *O sistema deve permitir que o usuário gerencie despesas.* (Verbo vago "gerenciar"; sem objeto delimitado; não testável.)
- ✅ **Bom:** *RF-01: O sistema deve permitir que um usuário autenticado cadastre uma despesa contendo descrição, valor, data e categoria, associando-a exclusivamente à conta do usuário autenticado.*

## B.4 Como escrever regras de negócio

Uma regra de negócio descreve o **domínio**, não uma tela, endpoint ou botão.

- ❌ **Ruim:** *O botão de salvar deve ficar desabilitado.* (Descreve UI, não regra.)
- ✅ **Bom:**
  - *RN-01: Uma despesa só pode ser registrada com valor maior que zero.*
  - *RN-02: A soma das despesas do período considera apenas registros com status ativo.*
  - *RN-03: Um usuário não pode consultar despesas de outro usuário.* (marcar **Veto: Sim**)

## B.5 Como escrever requisitos não funcionais

Sempre com **métrica** + **método de verificação**.

- ✅ *RNF-01: A listagem de despesas responde em ≤ 2 s no p95 para 10.000 registros por usuário.* (verificação: teste de carga)
- ✅ *RNF-02: Senhas são armazenadas com hash criptográfico, nunca em texto puro.* (verificação: inspeção de repositório/BD — **Veto: Sim**)
- ✅ *RNF-03: Usuários não autorizados recebem HTTP 403 ao acessar recursos de outros usuários.* (**Veto: Sim**)

## B.6 Como escrever critérios de aceitação (o ponto mais importante para a conformidade)

- **Um ID por critério** (`RF-01/CA-01`). É a unidade de medição.
- Todo critério em **Given/When/Then**, com valores concretos (não "um valor qualquer" — use "R$ 35,50").
- Sempre inclua ao menos **um cenário de erro/borda** por requisito relevante.
- Marque **prioridade** (Alta/Média/Baixa → pesos 3/2/1) e **veto** por critério.

```gherkin
Scenario: Rejeição de despesa com valor inválido   # RF-01/CA-02, Alta, Veto: Não
Given que o usuário está autenticado
When envia uma despesa com valor igual a zero
Then o sistema rejeita a solicitação
And retorna o código de erro "VALOR_INVALIDO"
And não persiste a despesa
```

## B.7 Regra anti-inflação (leia antes de fechar o documento)

> Não fatie um requisito difícil em vários requisitos fáceis para inflar a conformidade. A métrica é ponderada por prioridade justamente para desincentivar isso, mas a **auditoria de granularidade** (Fase 4 do processo) é obrigatória: se dois "requisitos" só fazem sentido juntos, eles são um só.

## B.8 Como lidar com requisitos incertos

Não invente decisões. Registre a incerteza em **Ask First** (seção 9) e na tabela de dúvidas (seção 11).

```text
DUV-01: O usuário poderá editar uma despesa após o fechamento mensal?
Impacto: RF-03, RN-05 e fluxo de fechamento.
Status: Pendente de validação com o cliente.
```

Enquanto `DUV` estiver Pendente, o critério dependente **não entra** no cálculo de conformidade daquela versão — ele fica explicitamente fora do escopo congelado.
