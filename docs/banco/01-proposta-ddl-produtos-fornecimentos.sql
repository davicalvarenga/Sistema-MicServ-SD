-- ==============================================================================
-- Proposta de DDL dos schemas produtos e fornecimentos
-- Grupo: Fornecimento e Produtos
-- Destinatário: grupo de Banco de Dados
-- Base: database/01-init.sql do kit de infraestrutura (commit 630515c)
-- Versão: 1.1 (10/11/2026): colunas exigidas pelas ESPs e reserva sem chave estrangeira
-- Versão: 1.2 (10/11/2026): UF da origem do fornecimento e peso unitário do produto,
--         pedidos pelo grupo de Logística/Transporte (ESP-FRN-001 v1.2, ESP-PRD-001 v1.2)
-- Versão: 1.3 (11/11/2026): coluna chave do outbox passa a TEXT. Na DLT, a chave é o
--         aggregateId recebido de outro serviço, sem limite de tamanho garantido
--
-- Executar depois do 01-init.sql do kit, com um usuário que possa assumir a role
-- portal_ddl (dona das tabelas). O script pode ser executado mais de uma vez.
--
-- Rastreabilidade: Documento de Requisitos v0.4 (RF-13, RF-14, RF-16, RF-19,
-- RF-20, RN-03, RN-11, RNF-06, RNF-24) e Relatório Técnico v0.2 (ADR-004,
-- ADR-005, ADR-006, ADR-007, ADR-010, ADR-011). Pendências P-28 e P-32.
-- ==============================================================================

BEGIN;

SET LOCAL ROLE portal_ddl;

-- ------------------------------------------------------------------------------
-- 1. Schema fornecimentos
-- ------------------------------------------------------------------------------

-- 1.1 Quantidade reservada e data de atualização no fornecimento (RF-13, P-28)
ALTER TABLE fornecimentos.fornecimento
  ADD COLUMN IF NOT EXISTS quantidade_reservada NUMERIC(12, 2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  -- Atributos do fornecimento na ESP-FRN-001 (§6.1) que a tabela do kit não tem
  ADD COLUMN IF NOT EXISTS unidade VARCHAR(32),
  ADD COLUMN IF NOT EXISTS criado_por_usuario_id VARCHAR(64),
  -- Origem em cidade e UF (P-05): a coluna origem do kit passa a guardar a cidade,
  -- e a UF fica nesta coluna nova
  ADD COLUMN IF NOT EXISTS origem_uf VARCHAR(2);

-- 1.2 O estoque nunca fica negativo (RN-11). A verificação no banco é a última
--     barreira caso o código tenha um erro.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_fornecimento_disponivel_nao_negativo') THEN
    ALTER TABLE fornecimentos.fornecimento
      ADD CONSTRAINT ck_fornecimento_disponivel_nao_negativo CHECK (quantidade_disponivel >= 0);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_fornecimento_reservada_nao_negativa') THEN
    ALTER TABLE fornecimentos.fornecimento
      ADD CONSTRAINT ck_fornecimento_reservada_nao_negativa CHECK (quantidade_reservada >= 0);
  END IF;
  -- Sigla de uma das 27 unidades da federação (IBGE)
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_fornecimento_origem_uf') THEN
    ALTER TABLE fornecimentos.fornecimento
      ADD CONSTRAINT ck_fornecimento_origem_uf CHECK (origem_uf IN (
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
        'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'));
  END IF;
END $$;

-- 1.3 Índices para as listagens filtradas por produto e por fornecedor (RF-10)
CREATE INDEX IF NOT EXISTS ix_fornecimento_produto ON fornecimentos.fornecimento (produto_id);
CREATE INDEX IF NOT EXISTS ix_fornecimento_fornecedor ON fornecimentos.fornecimento (fornecedor_id);

-- 1.4 Cópia local dos produtos válidos, alimentada pelos eventos de produto
--     (RF-16, RN-03, ADR-011). O serviço de Fornecimentos não acessa o schema produtos.
CREATE TABLE IF NOT EXISTS fornecimentos.produto_referencia (
  id VARCHAR(64) PRIMARY KEY,
  nome VARCHAR(255) NOT NULL,
  unidade VARCHAR(32) NOT NULL,
  tipo_transporte VARCHAR(64) NOT NULL,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  versao_evento TIMESTAMP WITH TIME ZONE NOT NULL, -- timestamp do último evento aplicado
  atualizado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 1.5 Todo fornecimento referencia um produto conhecido (RN-03)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_fornecimento_produto_referencia') THEN
    ALTER TABLE fornecimentos.fornecimento
      ADD CONSTRAINT fk_fornecimento_produto_referencia
      FOREIGN KEY (produto_id) REFERENCES fornecimentos.produto_referencia (id);
  END IF;
END $$;

-- 1.6 Uma reserva por pedido e fornecimento (RF-14, RF-19, RF-20, ADR-005).
--     Guarda a quantidade reservada para liberar ou dar baixa no valor exato.
CREATE TABLE IF NOT EXISTS fornecimentos.reserva (
  pedido_id VARCHAR(64) NOT NULL,
  -- Sem chave estrangeira: um cancelamento pode chegar para um fornecimento que não existe e é
  -- registrado como CANCELADA_SEM_RESERVA (ESP-FRN-001, §6.2)
  fornecimento_id VARCHAR(64) NOT NULL,
  quantidade NUMERIC(12, 2) NOT NULL CHECK (quantidade >= 0),
  -- CANCELADA_SEM_RESERVA (quantidade 0): o cancelamento chegou antes do pedido_criado,
  -- que fica em outro tópico; impede que a criação posterior reserve (ESP-FRN-001, §6.2)
  situacao VARCHAR(32) NOT NULL CHECK (situacao IN ('RESERVADA', 'LIBERADA', 'BAIXADA', 'CANCELADA_SEM_RESERVA')),
  criado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (pedido_id, fornecimento_id)
);

-- 1.7 Ligação de cada movimento de estoque com o pedido que o causou (auditoria)
ALTER TABLE fornecimentos.movimento_estoque
  ADD COLUMN IF NOT EXISTS pedido_id VARCHAR(64);

-- 1.8 Outbox: o evento é gravado na mesma transação da alteração e publicado
--     depois por um processo do serviço (ADR-010)
CREATE TABLE IF NOT EXISTS fornecimentos.outbox (
  event_id VARCHAR(64) PRIMARY KEY,
  topico VARCHAR(128) NOT NULL,
  chave VARCHAR(64) NOT NULL,
  envelope JSONB NOT NULL,
  criado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  publicado_em TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_fornecimentos_outbox_pendente
  ON fornecimentos.outbox (criado_em) WHERE publicado_em IS NULL;
ALTER TABLE fornecimentos.outbox ALTER COLUMN chave TYPE TEXT;

-- ------------------------------------------------------------------------------
-- 2. Schema produtos
-- ------------------------------------------------------------------------------

-- 2.1 Data de atualização do produto. A coluna "ativo" só será necessária se a
--     exclusão for lógica (P-09), e por isso não está nesta proposta.
ALTER TABLE produtos.produto
  ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  -- Quem cadastrou (ESP-PRD-001, §6.1): claims tenant_id e sub do token
  ADD COLUMN IF NOT EXISTS cadastrado_por_empresa_id VARCHAR(64),
  ADD COLUMN IF NOT EXISTS cadastrado_por_usuario_id VARCHAR(64),
  -- Peso de uma unidade do produto em kg, opcional (ESP-PRD-001, RN-08). Permite a
  -- Logística calcular o peso da carga quando a unidade é UN, CX ou L
  ADD COLUMN IF NOT EXISTS peso_unitario_kg NUMERIC(12, 3);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_produto_peso_unitario_positivo') THEN
    ALTER TABLE produtos.produto
      ADD CONSTRAINT ck_produto_peso_unitario_positivo CHECK (peso_unitario_kg > 0);
  END IF;
END $$;

-- 2.2 Índice para o filtro por categoria (RF-02)
CREATE INDEX IF NOT EXISTS ix_produto_categoria ON produtos.produto (categoria);

-- 2.3 Outbox do serviço de Produtos (ADR-010)
CREATE TABLE IF NOT EXISTS produtos.outbox (
  event_id VARCHAR(64) PRIMARY KEY,
  topico VARCHAR(128) NOT NULL,
  chave VARCHAR(64) NOT NULL,
  envelope JSONB NOT NULL,
  criado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  publicado_em TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_produtos_outbox_pendente
  ON produtos.outbox (criado_em) WHERE publicado_em IS NULL;
ALTER TABLE produtos.outbox ALTER COLUMN chave TYPE TEXT;

RESET ROLE;

-- ------------------------------------------------------------------------------
-- 3. Permissões (correção da P-32)
--    No 01-init.sql do kit, os GRANT rodam antes do CREATE TABLE. No PostgreSQL,
--    GRANT ... ON ALL TABLES IN SCHEMA vale só para tabelas que já existem, então
--    svc_produtos e svc_fornecimentos ficam sem acesso às próprias tabelas.
--    Aqui as permissões são só de DML, como pede a seção 5.2 do guia do kit.
-- ------------------------------------------------------------------------------

REVOKE ALL ON ALL TABLES IN SCHEMA produtos FROM svc_produtos;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA produtos TO svc_produtos;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA produtos TO svc_produtos;
ALTER DEFAULT PRIVILEGES FOR ROLE portal_ddl IN SCHEMA produtos
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO svc_produtos;
ALTER DEFAULT PRIVILEGES FOR ROLE portal_ddl IN SCHEMA produtos
  GRANT USAGE, SELECT ON SEQUENCES TO svc_produtos;

REVOKE ALL ON ALL TABLES IN SCHEMA fornecimentos FROM svc_fornecimentos;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA fornecimentos TO svc_fornecimentos;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA fornecimentos TO svc_fornecimentos;
ALTER DEFAULT PRIVILEGES FOR ROLE portal_ddl IN SCHEMA fornecimentos
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO svc_fornecimentos;
ALTER DEFAULT PRIVILEGES FOR ROLE portal_ddl IN SCHEMA fornecimentos
  GRANT USAGE, SELECT ON SEQUENCES TO svc_fornecimentos;

COMMIT;
