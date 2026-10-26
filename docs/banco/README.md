# Proposta de DDL: schemas `produtos` e `fornecimentos`

**De:** grupo de Fornecimento e Produtos
**Para:** grupo de Banco de Dados (com cópia ao grupo de Infraestrutura)
**Data:** 26/10/2026
**Script:** [`01-proposta-ddl-produtos-fornecimentos.sql`](01-proposta-ddl-produtos-fornecimentos.sql)

O DDL é responsabilidade do grupo de Banco de Dados, conforme o guia do kit de infraestrutura (seção 5). Este arquivo é uma **proposta** para facilitar a revisão. A decisão final é de vocês.

## Por que precisamos destas mudanças

| Mudança | Motivo | Requisito |
|---|---|---|
| `quantidade_reservada` em `fornecimento` | O professor pediu que o estoque fique bloqueado enquanto o pedido está em andamento, separado da quantidade disponível | RF-13, RF-14 |
| `CHECK` de quantidades não negativas | O estoque nunca pode ficar negativo. A verificação no banco é a última barreira caso o código tenha um erro | RN-11 |
| Tabela `reserva` | Guarda quanto cada pedido reservou de cada fornecimento, para liberar (cancelamento) ou dar baixa (venda) no valor exato. A situação `CANCELADA_SEM_RESERVA`, com quantidade 0, registra um cancelamento que chegou antes do `pedido_criado` (estão em tópicos diferentes, sem ordem garantida entre si) e impede a reserva posterior | RF-19, RF-20, ESP-FRN-001 §6.2 |
| Tabela `produto_referencia` e chave estrangeira | Cópia local dos produtos, alimentada pelo evento `produto_cadastrado`, já que Fornecimentos não pode ler o schema `produtos`. A chave estrangeira impede fornecimento de produto inexistente | RF-16, RN-03 |
| `pedido_id` em `movimento_estoque` | Liga cada movimento de estoque ao pedido que o causou (auditoria) | RF-14 |
| Tabelas `outbox` | O evento é gravado na mesma transação da alteração e publicado depois. Evita perder evento quando o Redpanda está fora | ADR-010 |
| `atualizado_em` e índices | Data da última alteração e índices para as listagens filtradas por produto, fornecedor e categoria | RF-02, RF-10 |
| Permissões refeitas | No `01-init.sql` do kit, os `GRANT` rodam antes do `CREATE TABLE`, e `svc_produtos` e `svc_fornecimentos` ficam sem acesso às próprias tabelas. A proposta concede só DML (`SELECT`, `INSERT`, `UPDATE`, `DELETE`), como pede a seção 5.2 do guia, e define permissões padrão para tabelas futuras | RNF-24, P-32 |

O script não remove nada que o kit criou. Ele só acrescenta colunas, restrições, tabelas e índices, e pode ser executado mais de uma vez (`IF NOT EXISTS` e verificações em `pg_constraint`).

## Como foi testado

Em 26/10/2026, num PostgreSQL 16 local (T12 depois do ajuste para a ESP-FRN-001, no mesmo dia), na seguinte ordem: o `database/01-init.sql` do kit (commit `630515c`), esta proposta duas vezes seguidas e os testes abaixo, executados com o usuário `svc_fornecimentos`.

| # | Teste | Resultado esperado | Resultado obtido |
|---|---|---|---|
| T0 | Executar a proposta duas vezes | Nenhum erro na segunda execução | Sem erros |
| T1 | Cadastrar produto de referência e fornecimento com 100 unidades | Gravado | Gravado |
| T2 | Reservar 30 numa transação com `processed_events`, `reserva` e `movimento_estoque` | 70 disponíveis, 30 reservadas | 70,00 e 30,00 |
| T3 | Registrar de novo o mesmo `eventId` com `ON CONFLICT DO NOTHING` | 0 linhas (evento repetido identificado) | 0 linhas |
| T4 | Reservar 80 com 70 disponíveis usando `UPDATE ... WHERE quantidade_disponivel >= 80` | 0 linhas alteradas | `UPDATE 0` |
| T5 | Forçar estoque negativo sem a condição | Erro de `CHECK` | `violates check constraint "ck_fornecimento_disponivel_nao_negativo"` |
| T6 | Criar fornecimento de produto desconhecido | Erro de chave estrangeira | `violates foreign key constraint "fk_fornecimento_produto_referencia"` |
| T7 | Cancelamento: liberar a reserva de 30 | 100 disponíveis, 0 reservadas | 100,00 e 0,00 |
| T8 | Reservar 40 e dar baixa (venda concluída) | 60 disponíveis, 0 reservadas | 60,00 e 0,00 |
| T9 | Gravar evento na `outbox` | Gravado | Gravado |
| T10 | `DROP TABLE` e leitura do schema `produtos` como `svc_fornecimentos` | Ambos recusados | `must be owner of table` e `permission denied for schema produtos` |
| T12 | Gravar reserva `CANCELADA_SEM_RESERVA` com quantidade 0; tentar quantidade -1 e situação `RECUSADA` | A primeira é aceita; as duas outras são recusadas pelos `CHECK` | Aceita; `reserva_quantidade_check` e `reserva_situacao_check` recusaram as outras duas |
| T11 | **Concorrência:** duas sessões reservam 60 de um fornecimento com 100. A sessão A segura a transação por 3 segundos, e a sessão B tenta reservar nesse intervalo | Só uma reserva passa, e o estoque não fica negativo | A: `UPDATE 1`. B esperou A terminar e fez `UPDATE 0`. Final: 40 disponíveis, 60 reservadas |

O T11 confirma o comportamento descrito no ADR-006 do Relatório Técnico: no PostgreSQL, com o isolamento padrão (Read Committed), a segunda atualização espera a primeira e reavalia a condição sobre a linha já atualizada.

## Pontos que dependem de outras decisões

- **Exclusão de produto (P-09):** se for lógica, `produtos.produto` precisa de uma coluna `ativo`. Ficou fora até a decisão.
- **Descrição do produto (RD-02):** proposta do grupo, ainda não confirmada. Ficou fora.
- **Empresa com vários perfis (P-31):** afeta o schema `usuarios`, que não é nosso.
