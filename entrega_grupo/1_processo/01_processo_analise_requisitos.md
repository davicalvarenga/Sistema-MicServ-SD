---
title: "Processo de Análise e Especificação de Requisitos para Geração de Software por LLM"
subtitle: "Processo estruturado com meta de conformidade ≥ 85%"
version: "2.0"
status: "Aprovado"
owner: "Daniel Carvalho Coutinho · Gabriel Vicentte dos Santos Ferreira · Pedro Cardoso da Mata · Rafael de Castro"
---

# Processo de Análise de Requisitos para Geração de Software por LLM

> **Objetivo geral:** desenvolver um processo estruturado de análise e especificação de requisitos capaz de gerar um documento padronizado em Markdown, utilizável por uma LLM para produzir software com conformidade **igual ou superior a 85%** em relação aos requisitos definidos.

Este é o **artefato 1 de 4** da entrega. Os demais são: o *Artefato* (modelo do documento de requisitos), as *Instruções de preenchimento* e o *Relatório técnico do experimento*.

---

## 1. Fundamento: por que 85% depende do processo, não da LLM

A conformidade final não é produzida pela LLM. É produzida pela **redução de ambiguidade a montante** e pela **medição rastreável a jusante**. A LLM é apenas a variável de tratamento; o que muda o resultado é a qualidade da especificação e a honestidade da medição.

Três pilares sustentam a meta:

1. **Elicitação e refinamento** — eliminar ambiguidade *antes* de gerar código. Ambiguidade não resolvida vira decisão silenciosa da LLM, e decisão silenciosa é a causa nº 1 de não conformidade.
2. **Documento estruturado em Markdown** — especificar comportamento, regras, contratos, limites e critérios de aceitação de forma interpretável por humanos e por LLMs, com IDs rastreáveis.
3. **Medição objetiva e iteração controlada** — avaliar por testes vinculados aos critérios de aceitação, com uma métrica **ponderada** e **à prova de manipulação**, dentro de um método científico com grupo de controle.

> **Princípio inegociável:** conformidade nunca é medida por percepção humana nem por opinião de outra IA. É demonstrada por testes vinculados a critérios de aceitação, e esses testes são congelados *antes* da geração de código (test-first).

---

## 2. O problema do mundo real que o processo resolve

Clientes reais entregam requisitos incompletos, contraditórios, vagos ou mutáveis. Frases como *"o sistema deve ser rápido"*, *"deve ser fácil de usar"*, *"não pode permitir erros"* não orientam uma LLM nem permitem validar a implementação.

O trabalho central do processo é converter afirmações imprecisas em **condições observáveis e testáveis**:

| Requisito impreciso | Requisito verificável |
|---|---|
| O sistema deve ser rápido | A consulta responde em ≤ 2 s no percentil 95 para até 10.000 registros por usuário |
| Deve haver segurança | Usuário sem permissão não consulta dados de outro usuário; acesso cruzado retorna HTTP 403 |
| Deve ser fácil cadastrar | O cadastro é concluído com no máximo 5 campos obrigatórios; campo inválido exibe mensagem de erro específica |
| O sistema deve validar dados | E-mail em formato válido; CPF com 11 dígitos válidos; campos obrigatórios não nulos |

**Teste de prontidão de qualquer requisito** — a equipe deve conseguir responder objetivamente:

> "Como provaremos, por teste ou evidência objetiva, que este requisito foi atendido?"

Se a resposta não for clara, o requisito **não está pronto** para a LLM e retorna à fase de refinamento.

---

## 3. Visão do processo em fases

O processo tem **8 fases**, agrupadas em três blocos:

| Bloco | Fases | Resultado |
|---|---|---|
| Especificação | 0 · Preparação → 1 · Elicitação → 2 · Refinamento → 3 · Estruturação | Documento de requisitos versionado |
| Preparação da medição | 4 · Validação pré-geração → 5 · Derivação de testes (test-first) | Suíte de testes congelada |
| Execução e evolução | 6 · Geração com LLM → 7 · Medição → 8 · Iteração | Métrica de conformidade + causas de falha |

```text
Fase 0        Fase 1        Fase 2         Fase 3          Fase 4         Fase 5
Preparação →  Elicitação →  Refinamento →  Estruturação →  Validação  →   Testes
                  ↑                                          │            (test-first,
                  │                                          │             congelados
                  │            (requisito não                │             ANTES da
                  └──── verificável volta ───────────────────┘             geração)
                                                                              │
                                                                              ▼
                                          Fase 8         Fase 7          Fase 6
                                        Iteração  ←──  Medição   ←──   Geração LLM
                                     (nova versão      (conformidade    (por módulos
                                      do documento)     ponderada)       rastreáveis)
```

**Ordenação crítica (correção metodológica):** a derivação de testes (Fase 5) ocorre **antes** da geração de código (Fase 6). Isso quebra a circularidade em que a mesma passagem de leitura do documento produziria simultaneamente o código e o critério que o julga. Ver a justificativa em `03_relatorio_tecnico.md`, seção de ameaças à validade.

---

## Fase 0 — Preparação e alinhamento

**Objetivo:** definir problema, envolvidos, contexto e limites iniciais.

**Atividades**

1. Registrar o problema de negócio em 1–2 frases.
2. Identificar atores: usuários, clientes, equipe técnica, demais interessados.
3. Definir objetivo do produto e resultado esperado (critério de sucesso do negócio).
4. Delimitar escopo inicial e exclusões conhecidas.
5. Registrar restrições: prazo, orçamento, tecnologia, privacidade, legislação.
6. Criar glossário mínimo de termos de domínio.

**Perguntas ao cliente**

- Qual problema precisa ser resolvido? Quem sofre impacto se o sistema não existir?
- Quem utilizará o sistema? Qual resultado indica que a solução deu certo?
- Quais informações o sistema recebe e quais resultados entrega?
- O que está explicitamente fora do escopo?
- Há regras legais, financeiras, de segurança ou privacidade?

**Saídas:** problema de negócio · objetivo do produto · lista de atores · escopo inicial · restrições · glossário preliminar.

---

## Fase 1 — Elicitação de requisitos

**Objetivo:** coletar necessidades e convertê-las em funcionalidades, regras, cenários e restrições.

**Técnicas:** entrevistas estruturadas · workshops com stakeholders · histórias de usuário · casos de uso · wireframes simples · exemplos de dados reais/simulados · análise de documentos existentes · observação do processo atual.

**Estrutura de história de usuário**

```text
Como [tipo de usuário],
quero [objetivo ou ação],
para [benefício esperado].
```

Exemplo: *Como cliente, quero cadastrar uma despesa, para acompanhar meu orçamento mensal.*

**Saídas:** necessidades levantadas · histórias de usuário · fluxos principais · regras de negócio preliminares · dúvidas e decisões pendentes.

---

## Fase 2 — Refinamento e desambiguação

**Objetivo:** transformar desejos vagos em requisitos claros, consistentes, mensuráveis e testáveis.

**Regras de qualidade — cada requisito deve ser:**

- **Claro** — linguagem simples, sem termos vagos.
- **Atômico** — uma única obrigação principal.
- **Consistente** — não contradiz outro requisito.
- **Necessário** — contribui para o objetivo do produto.
- **Viável** — técnica e economicamente possível.
- **Rastreável** — possui identificador único.
- **Verificável** — permite teste, inspeção ou medição.
- **Priorizado** — indica importância para o negócio (Alta/Média/Baixa).

> ⚠️ **Regra anti-inflação da métrica (correção metodológica).** É proibido fragmentar um requisito complexo em vários requisitos triviais para inflar artificialmente a conformidade. A atomicidade vale para a *obrigação de negócio*, não para dividir uma única regra difícil em fatias fáceis. A auditoria de granularidade é obrigatória na Fase 4.

**Cenários de aceitação — formato Given/When/Then**

```gherkin
Given [contexto inicial]
When [ação executada]
Then [resultado esperado]
```

Exemplo:

```gherkin
Given que o usuário está autenticado
And possui saldo disponível de R$ 100,00
When registra uma despesa de R$ 30,00
Then o saldo disponível deve ser atualizado para R$ 70,00
And a despesa deve aparecer no histórico do usuário
```

**Saídas:** requisitos funcionais refinados · requisitos não funcionais mensuráveis · critérios de aceitação · casos de borda · regras de negócio numeradas.

---

## Fase 3 — Estruturação do documento em Markdown

**Objetivo:** consolidar os requisitos no artefato único, padronizado e versionável (modelo em `02_modelo_e_instrucoes.md`).

**Princípios do artefato**

- IDs únicos: `RF-01`, `RN-01`, `RNF-01`, `CA-01` (critério de aceitação).
- Linguagem objetiva e afirmativa; verbos observáveis.
- Exemplos concretos de entrada e saída.
- Separar regras de negócio de requisitos funcionais.
- Declarar escopo e não escopo.
- Especificar comportamento em erro e exceção.
- Incluir plano de testes e rastreabilidade.
- **Numerar cada critério de aceitação individualmente** (`RF-01/CA-01`, `RF-01/CA-02`), porque a unidade de medição da conformidade é o *critério*, não o requisito.

**Saída:** documento de requisitos em Markdown, versionado.

---

## Fase 4 — Validação pré-geração

**Objetivo:** garantir que o documento tem informação suficiente para orientar a LLM e para julgar o resultado.

**Checklist de validação**

- [ ] Objetivo de negócio claro.
- [ ] Escopo e não escopo explícitos.
- [ ] Glossário para termos de domínio.
- [ ] Todo RF possui ID.
- [ ] Cada RF possui ≥ 1 critério de aceitação testável, com ID próprio.
- [ ] Regras de negócio numeradas e com exemplos.
- [ ] RNFs com métricas mensuráveis e método de verificação.
- [ ] Contratos de entrada/saída nas operações relevantes.
- [ ] Casos de erro e borda especificados.
- [ ] Plano de testes vinculado aos requisitos.
- [ ] Decisões pendentes identificadas (nada assumido silenciosamente).

**Auditoria de granularidade (correção metodológica) — obrigatória:**

- [ ] Nenhum requisito de negócio único foi fatiado em vários IDs triviais.
- [ ] A distribuição de prioridade é realista (não há maioria artificial de itens "Baixa" fáceis).
- [ ] Cada critério de aceitação tem peso coerente com o risco de negócio.

Se qualquer requisito não for verificável, ele **volta à Fase 2**.

---

## Fase 5 — Derivação de testes (test-first, congelados)

**Objetivo:** produzir a suíte de testes que medirá a conformidade, **antes** de qualquer geração de código.

**Regras (correção metodológica contra circularidade):**

1. Os testes são derivados dos critérios de aceitação por um integrante **diferente** de quem escreverá o prompt de geração, sempre que a equipe permitir.
2. Cada teste referencia o ID do critério que verifica (`RF-01/CA-02`).
3. A suíte é **congelada** junto com a versão do documento. Nenhum teste é ajustado depois de ver o código gerado — se um teste estava errado, isso é registrado como *falha de teste* e vira nova versão, não um conserto silencioso.
4. Critérios de segurança/autorização/integridade recebem teste próprio e marcação de **veto** (falha neles invalida a alegação de conformidade, independentemente do percentual).

**Saída:** suíte de testes versionada + matriz de rastreabilidade preenchida (coluna "Resultado" ainda vazia).

---

## Fase 6 — Geração de código com LLM

**Objetivo:** usar o documento congelado como fonte de verdade para gerar a implementação.

**Estratégia:** não solicitar o sistema inteiro numa única interação. Dividir por módulos coerentes de 3–5 requisitos relacionados, o que facilita revisão, correção e rastreabilidade.

Exemplo de divisão: (1) modelos de dados e validações → (2) regras de negócio → (3) API/interface de cadastro → (4) consulta e listagem → (5) autenticação e autorização.

**Prompt base padronizado** (variável de controle do experimento — não alterar entre execuções comparáveis):

```text
Você é um engenheiro de software responsável por implementar os requisitos abaixo.
Use o documento como única fonte de verdade.

Instruções:
1. Implemente somente os requisitos identificados nesta solicitação.
2. Respeite regras de negócio, contratos de entrada/saída e critérios de aceitação.
3. Não invente comportamentos que não estejam definidos.
4. Havendo ambiguidade ou decisão pendente, PARE e liste perguntas objetivas antes de implementar.
5. Preserve as restrições de segurança, desempenho e escopo do documento.
6. Ao final, liste os IDs de requisitos implementados e os não implementados.

NÃO gere os testes de aceitação — eles já existem e foram congelados.

Requisitos a implementar:
[COLAR RF, RN, RNF E CONTRATOS RELEVANTES]
```

> A instrução 5 do prompt original ("gere testes automatizados para cada critério") foi **removida deliberadamente**: se a LLM gera o código e os testes, a medição vira autoavaliação enviesada. Os testes vêm da Fase 5, escritos independentemente.

---

## Fase 7 — Medição de conformidade

**Objetivo:** determinar objetivamente se o software gerado atende aos requisitos.

### Fórmula de conformidade ponderada (correção metodológica)

A conformidade **não** é medida por "requisitos atendidos ÷ requisitos totais" — essa contagem é binária demais e manipulável pela granularidade. A unidade de medição é o **critério de aceitação**, ponderado por prioridade:

```
                    Σ (critérios aprovados × peso_prioridade)
Conformidade (%) = ───────────────────────────────────────────── × 100
                    Σ (critérios totais    × peso_prioridade)
```

Pesos: **Alta = 3 · Média = 2 · Baixa = 1**.

### Regra de veto (gate de segurança)

Independentemente do percentual calculado, a alegação de conformidade ≥ 85% é **inválida** se qualquer critério marcado como veto (segurança, autorização, integridade de dados, privacidade, regra financeira) estiver reprovado. Nesse caso a conformidade reportável é limitada e o defeito é bloqueante.

### Exemplo de cálculo

| Critério | Prioridade | Peso | Resultado | Contribuição |
|---|---|---:|---|---:|
| RF-01/CA-01 | Alta | 3 | Aprovado | 3 |
| RF-01/CA-02 | Alta | 3 | Aprovado | 3 |
| RF-02/CA-01 | Média | 2 | Aprovado | 2 |
| RF-02/CA-02 | Média | 2 | Reprovado | 0 |
| RF-03/CA-01 | Baixa | 1 | Aprovado | 1 |
| **Total** | | **11** | | **9** |

Conformidade = 9 / 11 × 100 = **81,8%** → abaixo da meta; RF-02/CA-02 é a causa a tratar na Fase 8.

### Métricas complementares (registrar sempre)

- Cobertura de requisitos (% com ≥ 1 teste) e de critérios de aceitação.
- Taxa de testes aprovados.
- Ambiguidades identificadas antes da implementação.
- Mudanças de requisitos por versão.
- Defeitos encontrados após a geração.
- Tempo por ciclo de geração/teste/correção.
- **Desvio entre execuções** (LLMs são estocásticas — ver Fase 8).

---

## Fase 8 — Iteração e melhoria

**Objetivo:** corrigir causas de não conformidade sem contaminar a medição.

**Ciclo:** gerar (versão congelada) → executar testes → calcular conformidade → identificar reprovados → **classificar a causa** → corrigir documento/prompt/implementação/teste → **criar nova versão** → repetir.

**Estocasticidade (correção metodológica):** cada versão do documento é executada com **≥ 3 seeds/execuções independentes** da LLM. Reporta-se **média ± desvio-padrão**, nunca um número único de uma rodada só — caso contrário o resultado é ruído.

**Classificação de causas de falha**

| Categoria | Descrição | Exemplo |
|---|---|---|
| Ambiguidade | O requisito admite mais de uma interpretação | "Listar despesas recentes" sem definir quantidade/ordenação |
| Regra incompleta | Faltam condições de negócio | Não define o que ocorre com saldo negativo |
| Contrato incompleto | Entrada, saída ou erro não definidos | API não especifica resposta para campo inválido |
| Falha de implementação | Requisito claro, código errado | Cálculo do saldo não subtrai a despesa |
| Falha de teste | O teste não representa o requisito | Teste aceita comportamento proibido |
| Mudança de escopo | Cliente alterou decisão após a geração | Passou a exigir múltiplas moedas |

> **Distinção crítica para o método:** só as causas *Ambiguidade*, *Regra incompleta* e *Contrato incompleto* justificam melhorar o **documento** (é o que a hipótese testa). *Falha de implementação* é ruído da LLM. *Mudança de escopo* exige nova versão e novo ciclo. Confundir essas categorias é overfitting do documento aos testes.

---

## 4. Gestão de volatilidade do cliente

**Versionamento:** toda execução usa uma versão **congelada** do documento (`v1.0`, `v1.1`, `v2.0`). Nunca alterar silenciosamente uma especificação já usada para medir — isso destrói a rastreabilidade da medição.

**Gestão de mudança:** registrar a solicitação → identificar requisitos/testes/telas/APIs afetados → avaliar impacto → aprovar → nova versão do documento → atualizar testes e regerar.

**Três estados de cada decisão:**

| Estado | Significado | Tratamento |
|---|---|---|
| Confirmado | Validado por cliente/equipe | Pode implementar e testar |
| Pendente | Falta informação | Não assumir — perguntar (`Ask First`) |
| Alterado | Regra mudou após versão anterior | Versionar e reexecutar testes afetados |

---

## 5. Critérios mínimos para alegar conformidade ≥ 85%

A equipe só declara a meta atingida se **todos** os itens forem verdadeiros:

- Versão do documento usada na geração está identificada e congelada.
- Conjunto de critérios de aceitação testáveis está listado com pesos.
- Cada critério possui ID e teste executável associado.
- O cálculo usa a **fórmula ponderada** e cobre todos os critérios do escopo congelado.
- A conformidade média (sobre ≥ 3 execuções) é ≥ 85%.
- Nenhum critério de veto (segurança/autorização/integridade/privacidade) está reprovado.
- Falhas e requisitos excluídos estão explicitamente registrados.
- Há um braço de controle no experimento (especificação não estruturada) para isolar o efeito do documento — ver relatório técnico.

---

## 6. Recomendações finais

1. **Não meça qualidade por percepção** — transforme requisitos em testes.
2. **Não deixe decisões implícitas** — o não definido é dúvida, não suposição da LLM.
3. **Não envie o sistema inteiro de uma vez** — implemente por módulos rastreáveis.
4. **Não altere requisitos após executar sem nova versão** — compromete a medição.
5. **Não deixe a LLM avaliar o próprio código** — testes independentes e congelados.
6. **Priorize requisitos críticos** — segurança, autorização, integridade e regras financeiras não passam com falhas.
7. **Use os erros para melhorar o template**, não para consertar testes — falha recorrente da LLM num ponto significa que falta detalhe, exemplo ou limite no documento.
8. **Mantenha o cliente no ciclo de validação** antes da geração.
