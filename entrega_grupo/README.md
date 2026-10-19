# Entrega — Processo de Análise de Requisitos para Geração de Software por LLM

**Meta do projeto:** documento de requisitos que, usado por uma LLM, gera software com conformidade ≥ 85%.

## Integrantes
- Daniel Carvalho Coutinho
- Gabriel Vicentte dos Santos Ferreira
- Pedro Cardoso da Mata
- Rafael de Castro

---

## Conteúdo da entrega

| Pasta | Item do enunciado | Arquivo |
|---|---|---|
| `1_processo/` | **Processo** de análise de requisitos | `01_processo_analise_requisitos.md` |
| `2_artefato_instrucoes/` | **Artefato** (modelo do documento) + **Instruções** de preenchimento | `02_modelo_e_instrucoes.md` |
| `3_relatorio_tecnico/` | **Relatório técnico** do experimento (método científico) | `04_relatorio_experimento_executado.md` |
| `4_evidencias/` | Evidências reprodutíveis do experimento | código + testes |

## Ordem de leitura recomendada

1. **Processo** — descreve as 8 fases da metodologia de análise de requisitos.
2. **Artefato + Instruções** — o modelo Markdown a ser preenchido por funcionalidade e como preenchê-lo.
3. **Relatório técnico** — a hipótese, o método e os resultados reais do experimento.

## Resumo do resultado

O experimento comparou dois braços avaliados pela **mesma suíte de testes congelada**:

| Braço | Modelo | Conformidade ponderada | Vetos de segurança reprovados | Meta ≥ 85% |
|---|---|---:|:--:|:--:|
| Controle (prosa livre) | — | 36,4% | 3 | ❌ |
| Tratamento (documento estruturado) | Claude Sonnet | 100% | 0 | ✅ |
| Tratamento (documento estruturado) | Perplexity | 100% | 0 | ✅ |
| Tratamento (documento estruturado) | Gemini 3 Pro | 100% | 0 | ✅ |

Três LLMs distintas, partindo do mesmo documento, atingiram 100% de conformidade — indicando que o resultado é atribuível à **estrutura do documento**, não a um modelo específico.

---

## Como reproduzir as evidências

Dentro de `4_evidencias/`:

```bash
pip install fastapi httpx pytest
python3 run.py
```

O `run.py` executa a suíte congelada (`tests/test_conformidade.py`) sobre os quatro braços e imprime a conformidade ponderada de cada um.

### Estrutura das evidências

- `spec/prompts.py` — prompt de controle (prosa livre) e prompt de tratamento (documento de requisitos estruturado e congelado).
- `tests/test_conformidade.py` — suíte de aceitação **escrita antes da geração** (test-first), com pesos por prioridade e marcação de veto.
- `control/app.py` — código gerado a partir da prosa livre.
- `treatment/app.py` — código gerado pelo Claude a partir do documento estruturado.
- `perplexity/app.py` — código gerado pelo Perplexity a partir do mesmo documento.
- `gemini/app.py` — código gerado pelo Gemini 3 Pro a partir do mesmo documento.
- `run.py` — runner que calcula a conformidade ponderada com regra de veto.

### Nota de transparência

Os códigos do Perplexity e do Gemini foram avaliados como recebidos. As únicas alterações foram restaurar a indentação perdida na cópia/cola e corrigir uma lista truncada na transcrição do Perplexity (`= ]` → `= []`) — ajustes de transcrição, sem mudança de lógica. Detalhes na seção 7 do relatório técnico.
