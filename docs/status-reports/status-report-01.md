# Status Report 01

**Grupo:** Fornecimento e Produtos
**Integrantes:** Daniel Carvalho Coutinho, Davi Coelho de Alvarenga, Gabriel Vicentte dos Santos Ferreira, Rafael de Castro Noleto
**Situação em:** 18/11/2026
**Repositório:** [`davicalvarenga/Sistema-MicServ-SD`](https://github.com/davicalvarenga/Sistema-MicServ-SD)

---

## 1. Resumo

| Item | Situação |
|---|---|
| Escopo do grupo | `produtos-service` (catálogo de produtos) e `fornecimentos-service` (ofertas e estoque) |
| Situação geral | Os dois serviços estão implementados, testados e rodando no kit de infraestrutura da turma, com as respostas do professor da última aula já incorporadas (versão 2.0) |
| Bloqueios do grupo | Nenhum que impeça o nosso trabalho. A integração completa depende de outros grupos (seção 5) |

---

## 2. Entregas

| Entrega | Versão | Onde está |
|---|---|---|
| Documento de Requisitos | 0.11 | [`docs/documento-de-requisitos.md`](../documento-de-requisitos.md) |
| Relatório Técnico (arquitetura e decisões) | 0.10 | [`docs/relatorio-tecnico.md`](../relatorio-tecnico.md) |
| Contrato de eventos, com JSON Schema e exemplo de cada evento | 2.1 | [`docs/contrato-eventos.md`](../contrato-eventos.md) e [`docs/contratos/`](../contratos/) |
| Especificação do `produtos-service` | 2.0 | [`docs/especificacoes/ESP-PRD-001_Produtos.md`](../especificacoes/ESP-PRD-001_Produtos.md) |
| Especificação do `fornecimentos-service` | 2.0 | [`docs/especificacoes/ESP-FRN-001_Fornecimentos.md`](../especificacoes/ESP-FRN-001_Fornecimentos.md) |
| Proposta de DDL dos nossos schemas no banco do kit | 1.4 | [`docs/banco/`](../banco/README.md) |
| `produtos-service` e `fornecimentos-service` | 2.0 | [`servicos/`](../../servicos/) |
| Integração com o kit (duas instâncias de cada serviço) | | [`servicos/integracao-kit/`](../../servicos/integracao-kit/README.md) |

---

## 3. O que foi feito desde a última aula

1. **Respostas do professor implementadas (versão 2.0).**
   - Produto só pode ser alterado ou excluído enquanto não tiver movimentação. A movimentação é marcada quando o primeiro fornecimento do produto é cadastrado.
   - Oferta pode ser reposta, ter o preço alterado (vale para todo o estoque) e ser encerrada (zera o disponível e mantém o reservado).
   - Preço e quantidade podem ser zero; a oferta zerada some da vitrine dos compradores.
   - Categoria do produto passou a ser lista fixa.
   - Eventos novos: `produto_atualizado`, `produto_excluido` e `fornecimento_atualizado`.
2. **Testes.**
   - Testes automatizados com PostgreSQL real: 62 no `produtos-service` e 111 no `fornecimentos-service`, todos passando, também no CI do GitHub.
   - Teste de ponta a ponta no kit (HTTP nas quatro instâncias, Redpanda, banco e token RS256): 17 de 17 verificações em duas rodadas seguidas.
3. **Defeito novo no kit (K15).** O script de criação de tópicos do kit esconde falhas e informa sucesso; rodado cedo demais, deixa de criar tópicos. Era a causa provável da falha intermitente que tínhamos registrado (issue #24). Contorno documentado e problema relatado à Infraestrutura (issue #12).
4. **Análise do serviço de Autenticação.** O repositório ficou acessível em 17/11. Os nossos serviços aceitam o formato real do token deles. Abrimos 9 issues com inconsistências (#27 a #35); o grupo de Autenticação corrigiu 4 delas em 18/11 (#27, #28, #29 e #31).

---

## 4. Próximos passos

| # | Ação | Responsável |
|---|---|---|
| 1 | Decidir como tratar o token de visão de grupo econômico (`MACRO_GROUP`) e a folga de 60 s na expiração do token (issues #33 e #32) | Grupo |
| 2 | Decidir se aceitamos o risco de revogação de token em até 15 minutos ou se consumimos os eventos de bloqueio da Autenticação (issue #34) | Grupo |
| 3 | Decidir se o `fornecimento_criado` passa a levar o grupo econômico, para Mercado e Negociação aplicarem a trava de auto-negociação (issue #35) | Grupo |
| 4 | Testar com tokens reais do serviço de Autenticação (login seguido de `switch-context`) | Grupo, quando o serviço estiver no kit |
| 5 | Avisar os outros grupos das mudanças incompatíveis da versão 2.0 (issue #25) | Grupo |

---

## 5. Dependências de outros grupos

| Grupo | O que falta | Efeito para nós | Issue |
|---|---|---|---|
| Infraestrutura | Corrigir o banco do kit, que não sobe (K12); rota do JWKS no gateway (K13); criar 4 tópicos que faltam (K14); script de tópicos (K15) | Hoje rodamos o kit com contornos documentados | #12 |
| Mercado, Negociação/Leilão e Pedidos | Incluir `fornecimentoId` no `pedido_criado` e no `pedido_atualizado`; informar os status de cancelamento e de venda concluída; avaliar `reserva_estoque_recusada` | Sem isso, não conseguimos reservar e baixar o estoque com os pedidos reais | #1 |
| Compra e Demanda | Revisar os eventos de catálogo e estoque da versão 2.0 | Possível divergência na integração | #21 |
| UX/UI | O protótipo usa valores fora do contrato (tipo de transporte, origem em texto, categoria "Grãos") | As telas não vão funcionar com a nossa API sem ajuste | #22 |
| Autenticação | Padrão único para o corpo de erro (`code` ou `codigo`) | Front-end e testes tratam dois formatos | #30 |
| Grupo de Teste | Atualizar os casos para a versão 2.0 | Casos antigos vão falhar (ex.: preço zero agora é aceito) | #25 |

---

## 6. Perguntas ao professor

As respostas da última aula ficaram cortadas na transcrição nestes pontos. O grupo adotou uma decisão provisória em cada um:

| # | Pergunta | Decisão provisória |
|---|---|---|
| 1 | Oferta com preço zero e quantidade maior que zero deve aparecer na vitrine? | Aparece |
| 2 | Só a empresa que cadastrou o produto pode alterá-lo ou excluí-lo? | Sim |
| 3 | A lista de categorias pode ser definida pelo grupo? | Sim: `GRAOS`, `INSUMOS`, `SUBPRODUTOS`, `LATICINIOS`, `CARNES`, `HORTIFRUTI`, `BEBIDAS`, `OUTROS` |
| 4 | O que o administrador da plataforma pode fazer nos nossos serviços? | Sem decisão. Hoje o serviço trata qualquer usuário pelo escopo ativo do token; o administrador da empresa (`TENANT_ADMIN`) só consulta |

---

## 7. Riscos

| Risco | Efeito | Tratamento |
|---|---|---|
| Kit de infraestrutura com defeitos (K12 a K15) | Nenhum serviço da turma sobe sem contorno | Contornos documentados no README da integração; pedidos na issue #12 |
| Eventos de pedido sem `fornecimentoId` | Reserva e baixa de estoque não funcionam na integração | Pedido feito ao grupo de Pedidos (issue #1) |
| Token continua válido por até 15 minutos depois de logout ou bloqueio | Empresa bloqueada ainda opera nesse intervalo | Em decisão (issue #34) |
| Teste no kit fora do CI | Regressão na integração só aparece no teste manual | Teste de fumaça repetido a cada mudança relevante |
