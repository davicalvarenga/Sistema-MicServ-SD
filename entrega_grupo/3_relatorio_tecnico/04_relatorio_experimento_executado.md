---
title: "Relatório Técnico do Experimento — Conformidade de Software Gerado por LLM"
version: "1.0"
date: "2026-09-19"
status: "Concluído"
---

# Relatório Técnico do Experimento

**Integrantes:**
- Daniel Carvalho Coutinho
- Gabriel Vicentte dos Santos Ferreira
- Pedro Cardoso da Mata
- Rafael de Castro

---

## 1. Hipótese

> Um documento de requisitos estruturado pelo processo proposto, quando usado como contexto para uma LLM, permite gerar software com conformidade ponderada **≥ 85%** em relação aos critérios de aceitação, **e superior** à conformidade obtida a partir de uma especificação não estruturada equivalente.

- **H₀:** o documento estruturado não atinge 85% **ou** não supera a especificação livre.
- **H₁:** o documento estruturado atinge ≥ 85% **e** supera a especificação livre.

## 2. Desenho experimental

Desenho comparativo de dois braços, avaliados pela **mesma suíte de testes congelada**, escrita **antes** da geração de código (test-first):

| Braço | Entrada da LLM |
|---|---|
| **Controle** | Prompt em prosa livre ("faça uma API de controle de despesas com cadastro, login, despesas e total") |
| **Tratamento** | Documento de requisitos estruturado v1.0 congelado + prompt base padronizado |

- **Funcionalidade avaliada:** API de controle de despesas pessoais.
- **Métrica:** conformidade ponderada = Σ(critérios aprovados × peso) / Σ(critérios × peso) × 100. Pesos: Alta = 3, Média = 2.
- **Regra de veto:** falha em critério de segurança/autorização/privacidade invalida a alegação de conformidade, independentemente do percentual.
- **Ambiente:** Python 3.12, FastAPI, pytest. Persistência em memória. Suíte idêntica nos dois braços.
- **Escopo congelado:** 8 critérios de aceitação (soma de pesos = 22).

## 3. Suíte de critérios (congelada)

| Critério | Descrição | Peso | Veto |
|---|---|---:|:--:|
| RF-01/CA-01 | Usuário autenticado cadastra despesa válida | 3 | Não |
| RF-01/CA-02 | Valor ≤ 0 é rejeitado e não persistido | 3 | Não |
| RF-01/CA-03 | Requisição sem token retorna 401/403 | 3 | **Sim** |
| RF-02/CA-01 | Listagem retorna apenas despesas do próprio usuário | 3 | Não |
| RF-02/CA-02 | Isolamento entre usuários (anti-IDOR) | 3 | **Sim** |
| RF-03/CA-01 | Total soma apenas despesas do usuário | 2 | Não |
| RNF-01/CA-01 | Senha nunca exposta em respostas | 3 | **Sim** |
| RNF-02/CA-01 | E-mail sem formato válido é rejeitado | 2 | Não |

## 4. Resultados (dados reais da execução)

### 4.1 Braço controle (prosa livre)

| Critério | Peso | Veto | Resultado |
|---|---:|:--:|---|
| RF-01/CA-01 | 3 | Não | ✅ Aprovado |
| RF-01/CA-02 | 3 | Não | ❌ Reprovado (aceita valor zero) |
| RF-01/CA-03 | 3 | Sim | ❌ **Reprovado (veto)** — endpoint sem autenticação |
| RF-02/CA-01 | 3 | Não | ✅ Aprovado |
| RF-02/CA-02 | 3 | Sim | ❌ **Reprovado (veto)** — vazamento entre usuários (IDOR) |
| RF-03/CA-01 | 2 | Não | ✅ Aprovado |
| RNF-01/CA-01 | 3 | Sim | ❌ **Reprovado (veto)** — senha retornada no cadastro |
| RNF-02/CA-01 | 2 | Não | ❌ Reprovado (não valida e-mail) |

**Conformidade ponderada = 8 / 22 × 100 = 36,4%.**
**Vetos reprovados: 3** (autorização, IDOR, privacidade) → alegação de conformidade **inválida**.

### 4.2 Braço tratamento (documento estruturado)

| Critério | Peso | Veto | Resultado |
|---|---:|:--:|---|
| RF-01/CA-01 | 3 | Não | ✅ Aprovado |
| RF-01/CA-02 | 3 | Não | ✅ Aprovado |
| RF-01/CA-03 | 3 | Sim | ✅ Aprovado |
| RF-02/CA-01 | 3 | Não | ✅ Aprovado |
| RF-02/CA-02 | 3 | Sim | ✅ Aprovado |
| RF-03/CA-01 | 2 | Não | ✅ Aprovado |
| RNF-01/CA-01 | 3 | Sim | ✅ Aprovado |
| RNF-02/CA-01 | 2 | Não | ✅ Aprovado |

**Conformidade ponderada = 22 / 22 × 100 = 100,0%.**
**Vetos reprovados: 0** → alegação de conformidade **válida**.

### 4.3 Comparação

| Braço | Conformidade | Vetos reprovados | Meta ≥ 85% |
|---|---:|:--:|:--:|
| Controle (prosa livre) | 36,4% | 3 | ❌ Não |
| Tratamento (estruturado) | **100,0%** | 0 | ✅ Sim |
| **Ganho (Δ)** | **+63,6 pp** | −3 | — |

## 5. Análise

O documento estruturado elevou a conformidade de 36,4% para 100% na funcionalidade avaliada, um ganho de 63,6 pontos percentuais. Mais relevante que o percentual: as três falhas de veto do braço controle são exatamente as classes de defeito que o processo prioriza — **autorização ausente, vazamento de dados entre usuários (IDOR) e exposição de senha**. Nenhuma delas aparece explicitamente numa especificação em prosa; todas estavam declaradas como critérios de aceitação e guardrails `Never` no documento estruturado, e por isso a LLM as implementou.

As causas de falha do braço controle classificam-se como **contrato incompleto** (a prosa não especificava respostas de erro nem isolamento) e **regra incompleta** (não definia validação de valor nem de e-mail) — precisamente as categorias que, segundo o processo, justificam a existência do documento estruturado.

**Conclusão:** rejeita-se H₀. As três LLMs testadas (Claude, Perplexity, Gemini), sob o documento estruturado, atingiram 100% de conformidade ponderada sem veto reprovado, contra 36,4% da especificação livre — um ganho de 63,6 pontos percentuais que replica entre modelos.

## 6. Ameaças à validade (declaração honesta)

Este experimento avaliou **1 funcionalidade** com **3 LLMs distintas** (1 execução por modelo). As seguintes limitações se aplicam e definem o trabalho de replicação pendente:

| Ameaça | Situação | Trabalho para robustez plena |
|---|---|---|
| Amostra (n=1 funcionalidade) | Uma funcionalidade avaliada | Replicar em ≥ 3 funcionalidades distintas |
| Estocasticidade da LLM | 1 execução por modelo | ≥ 3 execuções por modelo; reportar média ± desvio |
| Dependência de modelo | **Mitigada** — 3 modelos (Claude, Perplexity, Gemini) convergiram em 100% | Manter comparação multi-modelo nas réplicas |
| Circularidade teste↔código | **Mitigada** — testes congelados antes da geração, independentes do código | Manter em todas as réplicas |
| Inflação por granularidade | **Mitigada** — métrica ponderada + veto | Manter |
| Simplicidade do domínio | A funcionalidade é pequena (8 critérios) | Avaliar funcionalidade de maior complexidade, onde a ambiguidade tende a crescer |

A honestidade desta seção é parte da metodologia. O experimento demonstra o mecanismo e o sentido do efeito com replicação entre três modelos; a generalização para domínios complexos exige as réplicas acima. Note que a conformidade de 100% foi obtida numa funcionalidade de escopo pequeno e bem delimitado — é esperado (e desejável para o método) que domínios maiores exponham falhas residuais e produzam conformidade entre 85% e 100%, o que dá mais espaço para o ciclo de refinamento demonstrar valor.

## 7. Execução comparativa entre múltiplas LLMs

Para atenuar a ameaça "dependência de modelo", o **mesmo documento estruturado** (prompt de tratamento) e a **mesma suíte congelada** foram submetidos a três LLMs distintas. A única variável alterada foi o modelo gerador; a régua de avaliação e o input permaneceram idênticos.

| LLM (tratamento) | Conformidade ponderada | Vetos reprovados | Meta ≥ 85% |
|---|---:|:--:|:--:|
| Claude Sonnet | 100,0% | 0 | ✅ Sim |
| Perplexity | 100,0% | 0 | ✅ Sim |
| Gemini 3 Pro | 100,0% | 0 | ✅ Sim |
| **Média** | **100,0%** | **0** | ✅ Sim |
| — | — | — | — |
| Controle (prosa livre) | 36,4% | 3 | ❌ Não |

**Observação metodológica:** os códigos do Perplexity e do Gemini foram avaliados como recebidos. A única alteração foi restaurar a indentação perdida na cópia/cola e corrigir uma lista `[]` truncada na transcrição do código do Perplexity (`expenses_db[user_id] = ]` → `= []`) — ajuste de transcrição, não de lógica. Nenhum comportamento foi modificado.

**Interpretação:** as três LLMs, partindo do mesmo documento, produziram implementações estruturalmente diferentes (o Perplexity indexa usuários por e-mail e usa IDs sequenciais; o Gemini usa UUIDs; o Claude usa tokens hex) mas **todas satisfizeram 100% dos critérios ponderados**, incluindo os três critérios de veto (autenticação obrigatória, isolamento entre usuários e não exposição de senha). Isso indica que o resultado é **atribuível ao documento**, não a um modelo específico — o efeito replica entre modelos. A especificação em prosa livre, submetida à mesma régua, falhou nos três critérios de segurança, o que reforça que a estrutura do documento — e não a capacidade bruta da LLM — foi o fator determinante da conformidade.

### 7.1 Distribuição estruturalmente diferente, mesma conformidade

| Aspecto | Claude | Perplexity | Gemini |
|---|---|---|---|
| Identificador de usuário | token hex | ID sequencial (chave por e-mail) | UUID |
| Validação de e-mail | regex completa | verificação de `@` | verificação de `@` |
| Validação de valor | check explícito | `field_validator` Pydantic | check explícito |
| Isolamento por usuário | dict por e-mail | dict por user_id | dict por user_id |
| Conformidade | 100% | 100% | 100% |

A convergência de resultado apesar da divergência de implementação é a evidência central: o documento restringiu o *comportamento observável* sem impor a *estrutura interna*, que é exatamente o objetivo de uma boa especificação de requisitos.

## 8. Reprodutibilidade

Todos os artefatos executáveis estão anexados:

- `exp/spec/prompts.py` — prompt de controle e prompt de tratamento (documento estruturado congelado).
- `exp/tests/test_conformidade.py` — suíte congelada com pesos e marcação de veto.
- `exp/control/app.py` — código do braço controle (prosa livre).
- `exp/treatment/app.py` — código do braço tratamento (Claude Sonnet).
- `exp/perplexity/app.py` — código gerado pelo Perplexity.
- `exp/gemini/app.py` — código gerado pelo Gemini 3 Pro.
- `exp/run.py` — runner que executa a suíte e calcula a conformidade ponderada dos quatro braços.

Comando de reprodução:

```bash
pip install fastapi httpx pytest
cd exp && python3 run.py
```
