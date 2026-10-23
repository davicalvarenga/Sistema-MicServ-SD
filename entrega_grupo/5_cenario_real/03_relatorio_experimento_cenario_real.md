---
title: "Relatório do experimento em cenário real — Produtos e Fornecimentos"
data: "2026-10-22"
status: "Concluído (1ª rodada)"
---

# Relatório do experimento em cenário real

## 1. Objetivo

Medir a acurácia de LLMs gerando os microsserviços reais do grupo (Produtos e Fornecimentos) a partir de diferentes especificações, numa escala bem maior que o piloto: 2 serviços, JWT, SQLite por serviço, eventos Kafka publicados e consumidos, reserva de estoque concorrente, idempotência e tópico de erro.

## 2. Desenho

| Item | Piloto | Este experimento |
|---|---|---|
| Domínio | API de despesas | Produtos + Fornecimentos + estoque por eventos |
| Critérios | 8 (peso 22, 3 vetos) | **45 (peso 114, 14 vetos)** |
| Braços | 2 | **4** |
| Modelos | 3 (1 execução cada) | **3: Haiku, Sonnet, Opus** (Fable sem crédito) |
| Execuções | 4 | **24** |
| Separação gerador × testes | Mesmo autor | Suíte escrita por outro agente e mantida fora do alcance dos geradores |

**Braços.** Todos recebem as mesmas instruções (`spec/00_instrucoes.md`) e a mesma interface técnica (`spec/01_interface_tecnica.md`: rotas, campos, formato do JWT, contrato `publisher`/`handle_event` e mensagens de pedido). Muda só o conteúdo de requisitos:

| Braço | Conteúdo | Execuções |
|---|---|---|
| `controle` | 4 parágrafos de prosa livre | 3 (1 por modelo) |
| `v03` | Documento de Requisitos v0.3 atual do grupo, sem alteração | 6 (2 por modelo) |
| `v10_prosa` | Mesma informação da v1.0, em texto corrido, sem IDs, tabelas ou Gherkin | 6 (2 por modelo) |
| `v10` | Documento de Requisitos v1.0 estruturado (`02_documento_requisitos_v1.0.md`) | 9 (3 por modelo) |

**Métrica.** Conformidade ponderada (Alta 3, Média 2, Baixa 1), com regra de veto. O valor também é reportado para o subconjunto **núcleo**: os 29 critérios (peso 80) cujo comportamento a v0.3 já descreve. Esse recorte é a comparação justa com a v0.3, porque a v0.3 não pode acertar decisões que ainda não tomou.

## 3. Fluxo executado

1. **Revisão do piloto** (`01_revisao_piloto.md`): rodei a suíte original e uma suíte revisada nos 4 braços antigos.
2. **Design comum** (`spec/_design_comum.md`): 18 decisões provisórias (DEC-01 a DEC-18), que resolvem pendências da v0.3, e os 45 critérios.
3. **Três frentes em paralelo:**
   - documento v1.0;
   - versão em prosa equivalente;
   - suíte e implementação de referência.
4. **Validação da suíte, antes de qualquer medição:**
   - **Referência:** 45/45 em 3 execuções seguidas; o teste de concorrência passou 15/15.
   - **App vazio:** 45/45 reprovados, sem erro de coleta.
   - **Mutantes:** reserva com condição de corrida, validação com 422 no lugar de 400 e eventos sem deduplicação foram todos detectados.
5. **Congelamento** (SHA-256):
   - `conftest.py`: `0b8cc30f…2954a`
   - `test_cenario_real.py`: `d67dde33…78b3`
   - `weights.py`: `91aba7c1…0e9c`
6. **Geração.** Cada execução é um agente isolado que lê apenas o seu prompt, escreve `app.py` e só pode checar a sintaxe. Nenhuma correção foi feita no código gerado.
7. **Medição** (`run.py`): pytest por execução, timeout de 60 s por teste, agregação por braço e por modelo.

## 4. Resultados

### 4.1 Por braço

| Braço | n | Conformidade total (média ± dp) | Mín.–máx. | Núcleo (média ± dp) | Execuções com meta válida (≥ 85% e 0 vetos) |
|---|---:|---:|---|---:|---:|
| Controle | 3 | **75,1% ± 2,0** | 72,8–76,3 | 88,8% ± 0,0 | 0/3 |
| v0.3 | 6 | **79,4% ± 15,7** | 47,4–86,8 | 92,7% ± 17,9 | 5/6 |
| v1.0 em prosa | 6 | **100% ± 0** | 100–100 | 100% | 6/6 |
| v1.0 estruturada | 9 | **100% ± 0** | 100–100 | 100% | 9/9 |

### 4.2 Por execução

| Braço | Haiku | Sonnet | Opus |
|---|---|---|---|
| Controle | 72,8% (1 veto) | 76,3% | 76,3% |
| v0.3 | 86,8% · **47,4% (8 vetos)** | 86,8% · 85,1% | 85,1% · 85,1% |
| v1.0 em prosa | 100% · 100% | 100% · 100% | 100% · 100% |
| v1.0 | 100% ×3 | 100% ×3 | 100% ×3 |

### 4.3 Onde cada braço falhou (taxa de aprovação por critério)

| Critério | Controle | v0.3 | Causa (Fase 8) |
|---|---:|---:|---|
| Validação → 400 (produto e fornecimento) | 0% | 100% | Contrato incompleto: a prosa não diz o status, e o FastAPI devolve 422 por padrão |
| Corpo de erro com `codigo`/`campos` | 0% | 0% | Contrato incompleto |
| Lista de `tipo_transporte` | 0% | 0% | Regra incompleta (P-06) |
| Envelope do evento (`event_id`, `event_type`…) | 0% | 0% | Contrato incompleto (P-08) |
| Limites de preço/quantidade | 0% | 0% | Regra incompleta (P-15, P-21) |
| Pedido acima do disponível (`reserva_recusada`) | 0% | 0% | Regra incompleta (P-16) |
| Tópico `fornecimentos.dlq` | 0% | 0% | Contrato incompleto |
| Transportadora consultando fornecimentos → 403 | 0% | 50% | Ambiguidade (P-07) |
| Comprador cadastrando produto | 33% | 100% | Regra incompleta na prosa (RN-08) |
| Transportadora cadastrando produto → 403 (**veto**) | 67% | 100% | Regra incompleta na prosa |
| Payload de `estoque_atualizado` | 67% | 67% | Contrato incompleto |
| Fluxo de fornecimento e estoque inteiro (11 critérios, 7 vetos) | 100% | 83% | Falha de implementação: só no v0.3 Haiku r2 |

**O caso v0.3 Haiku r2.** O serviço de Fornecimentos não reconheceu os produtos recebidos pelos eventos de Produtos (`422 Produto inexistente`). A falha derrubou em cascata os 11 critérios de fornecimento e estoque, 7 deles com veto. A outra execução do mesmo modelo, com o mesmo prompt, tirou 86,8%. É a variância que uma execução única por modelo, como no piloto, não mostraria.

## 5. Análise

1. **A especificação estruturada atingiu a meta com folga e sem variância:** 15 de 15 execuções da v1.0 (estruturada e em prosa) chegaram a 100%, nos três modelos.
2. **A v0.3 atual não basta para gerar o sistema.**
   - Média de 79,4%: só 5 das 6 execuções passaram a meta, e uma ficou em 47,4% com 8 vetos.
   - Ela acerta o que descreve: núcleo de 100% em 5 das 6 execuções.
   - Perde nos 16 critérios que dependem das pendências P-06, P-08, P-15, P-16, P-21 e do tópico de erro.
   - Resolver as pendências, e não reescrever o formato, é o que leva aos 100%.
3. **O ganho veio do conteúdo, não da forma.**
   - A v1.0 em prosa empatou com a estruturada (100% × 100%).
   - Isso confirma a suspeita levantada na revisão do piloto: o que move a conformidade é decidir e escrever cada comportamento, não usar tabelas, IDs ou Gherkin.
   - A estrutura continua útil para rastreabilidade e revisão humana (seção 10 do documento liga cada critério a um teste). Este experimento só não mostrou ganho de acurácia por ela.
4. **O controle foi alto (75%) por causa da interface técnica comum,** que já fixa rotas, campos e o formato do token. Num cenário em que nem a interface é dada, o controle cairia bastante. Os 75% medem o valor dos requisitos de negócio *depois* de fixado o contrato técnico.
5. **Haiku foi o único modelo com falha grave**, e só sem a v1.0. Com a especificação completa, os três modelos convergem.

## 6. Ameaças à validade

| Ameaça | Situação |
|---|---|
| Efeito teto na v1.0 | Os dois braços v1.0 tiraram 100%. A suíte distingue a v0.3 e o controle, mas não distingue estruturada de prosa. Uma suíte mais difícil (ex.: falhas de rede, reentrega fora de ordem) pode separar as duas |
| Mesmo autor do design e da suíte | A suíte foi escrita por outro agente a partir do design, e os geradores nunca a viram. O design, porém, saiu da mesma sessão que escreveu os documentos |
| Decisões provisórias | DEC-01 a DEC-18 são propostas para o experimento, não decisões do professor nem dos outros grupos. Os critérios do grupo D medem aderência a elas |
| Infraestrutura simulada | Kafka substituído por `publisher`/`handle_event` em memória; SQLite no lugar do banco final. O adaptador Kafka real não foi gerado nem testado |
| Modelos de um único fornecedor | Só modelos Claude; Fable indisponível por crédito |
| n por braço | 3 a 9 execuções. O controle tem n = 1 por modelo |
| Geração por agente | Os geradores podiam checar a sintaxe, mas não executar o código. Eram agentes, não chamadas puras de API |

## 7. Conclusão

| Pergunta | Resposta |
|---|---|
| A acurácia do piloto se sustenta num cenário real? | **Sim, para a v1.0:** 100% em 15/15 execuções, nos três modelos, com 45 critérios |
| O documento atual do grupo (v0.3) já serve para gerar o sistema? | **Não:** 79,4% ± 15,7, com uma execução em 47,4% e 8 vetos |
| O que faltava? | Decidir as pendências (P-06, P-08, P-15, P-16, P-21) e fechar os contratos de erro e de eventos |
| A estrutura (IDs, tabelas, Gherkin) aumenta a acurácia? | **Não foi demonstrado:** a prosa com a mesma informação também tirou 100% |

**Recomendação:** levar as decisões DEC-01 a DEC-18 ao professor e aos grupos de autenticação, pedidos e infra (issues #1 a #8). Confirmadas, a v1.0 vira o documento oficial e esta suíte vira a régua de aceite do QA.

## 8. Reprodução

```bash
pip install fastapi pydantic pyjwt pytest pytest-timeout httpx
```

```bash
cd entrega_grupo/5_cenario_real/evidencias && python run.py
```

Para medir uma execução isolada: `APP_FILE=bracos/v10/opus_r1/app.py python -m pytest tests -q --timeout=60`. Os resultados ficam em `evidencias/resultados/` (`resultados.json` com o resultado de cada critério em cada execução, e `por_execucao.csv`).
