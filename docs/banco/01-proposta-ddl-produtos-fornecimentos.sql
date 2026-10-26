-- ==============================================================================
-- Proposta de DDL dos schemas produtos e fornecimentos
-- Grupo: Fornecimento e Produtos
-- Destinatário: grupo de Banco de Dados
-- Base: database/01-init.sql do kit de infraestrutura (commit 630515c)
-- Versão: 1.0 (26/10/2026)
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
  ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;

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
  fornecimento_id VARCHAR(64) NOT NULL REFERENCES fornecimentos.fornecimento (id),
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

-- ------------------------------------------------------------------------------
-- 2. Schema produtos
-- ------------------------------------------------------------------------------

-- 2.1 Data de atualização do produto. A coluna "ativo" só será necessária se a
--     exclusão for lógica (P-09), e por isso não está nesta proposta.
ALTER TABLE produtos.produto
  ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;

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
