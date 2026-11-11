"""Porta RepositorioFornecimentos sobre o schema `fornecimentos` do PostgreSQL 16.

Conecta com o usuário svc_fornecimentos (RNF-24) e no máximo 5 conexões (RNF-23).
`transacao()` prende uma conexão à thread atual: todas as chamadas feitas dentro do
mesmo `with` usam a mesma transação, confirmada no fim ou desfeita em exceção.
`aplicar_movimento` é o UPDATE condicional do ADR-006, que garante saldo não negativo
mesmo com duas instâncias do serviço. Depende da proposta de DDL em docs/banco/.
"""

import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal

from psycopg2.pool import ThreadedConnectionPool

COLUNAS_FORNECIMENTO = ("id, fornecedor_id, produto_id, unidade, preco, quantidade_disponivel, quantidade_reservada, "
                        "origem, origem_uf, criado_por_usuario_id, criado_em, atualizado_em")


def _instante(momento: datetime) -> str:
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fornecimento(linha) -> dict:
    return {
        "fornecimento_id": linha[0], "fornecedor_id": linha[1], "produto_id": linha[2], "unidade": linha[3],
        "preco": linha[4], "quantidade_disponivel": linha[5], "quantidade_reservada": linha[6],
        # A coluna origem do kit guarda a cidade; origem_uf foi acrescentada pela proposta de DDL v1.2
        "origem": {"cidade": linha[7], "uf": linha[8]},
        "criado_por_usuario_id": linha[9], "criado_em": _instante(linha[10]), "atualizado_em": _instante(linha[11]),
    }


class RepositorioFornecimentosPostgres:
    def __init__(self, dsn: str, max_conexoes: int = 5):
        self._pool = ThreadedConnectionPool(1, max_conexoes, dsn)
        self._local = threading.local()

    @property
    def pool(self) -> ThreadedConnectionPool:
        """Pool compartilhado com o BarramentoOutbox, para respeitar o limite de conexões (RNF-23)."""
        return self._pool

    @contextmanager
    def transacao(self):
        if getattr(self._local, "conexao", None) is not None:
            yield  # já dentro de uma transação desta thread
            return
        conexao = self._pool.getconn()
        self._local.conexao = conexao
        try:
            yield
            conexao.commit()
        except BaseException:
            conexao.rollback()
            raise
        finally:
            self._local.conexao = None
            self._pool.putconn(conexao)

    def _executar(self, sql: str, parametros=(), buscar: str | None = None):
        conexao = getattr(self._local, "conexao", None)
        avulsa = conexao is None
        if avulsa:
            conexao = self._pool.getconn()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(sql, parametros)
                resultado = cursor.fetchone() if buscar == "um" else cursor.fetchall() if buscar == "todos" else None
            if avulsa:
                conexao.commit()
            return resultado
        except BaseException:
            if avulsa:
                conexao.rollback()
            raise
        finally:
            if avulsa:
                self._pool.putconn(conexao)

    def evento_processado(self, event_id: str) -> bool:
        return self._executar("SELECT 1 FROM fornecimentos.processed_events WHERE event_id = %s", (event_id,), "um") is not None

    def registrar_evento_processado(self, event_id: str) -> None:
        self._executar("INSERT INTO fornecimentos.processed_events (event_id) VALUES (%s) ON CONFLICT DO NOTHING", (event_id,))

    def salvar_produto_referencia(self, produto: dict) -> None:
        self._executar(
            "INSERT INTO fornecimentos.produto_referencia (id, nome, unidade, tipo_transporte, ativo, versao_evento) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET nome = EXCLUDED.nome, unidade = EXCLUDED.unidade, "
            "tipo_transporte = EXCLUDED.tipo_transporte, ativo = EXCLUDED.ativo, versao_evento = EXCLUDED.versao_evento, "
            "atualizado_em = CURRENT_TIMESTAMP",
            (produto["produto_id"], produto["nome"], produto["unidade"], produto["tipo_transporte"], produto["ativo"],
             produto["versao_evento"]))

    def obter_produto_referencia(self, produto_id: str) -> dict | None:
        linha = self._executar("SELECT id, nome, unidade, tipo_transporte, ativo, versao_evento FROM fornecimentos.produto_referencia "
                               "WHERE id = %s", (produto_id,), "um")
        if linha is None:
            return None
        return {"produto_id": linha[0], "nome": linha[1], "unidade": linha[2], "tipo_transporte": linha[3], "ativo": linha[4],
                "versao_evento": _instante(linha[5])}

    def inserir_fornecimento(self, fornecimento: dict) -> None:
        self._executar(
            f"INSERT INTO fornecimentos.fornecimento ({COLUNAS_FORNECIMENTO}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (fornecimento["fornecimento_id"], fornecimento["fornecedor_id"], fornecimento["produto_id"], fornecimento["unidade"],
             fornecimento["preco"], fornecimento["quantidade_disponivel"], fornecimento["quantidade_reservada"],
             fornecimento["origem"]["cidade"], fornecimento["origem"]["uf"],
             fornecimento["criado_por_usuario_id"], fornecimento["criado_em"], fornecimento["atualizado_em"]))

    def obter_fornecimento(self, fornecimento_id: str) -> dict | None:
        linha = self._executar(f"SELECT {COLUNAS_FORNECIMENTO} FROM fornecimentos.fornecimento WHERE id = %s", (fornecimento_id,), "um")
        return _fornecimento(linha) if linha else None

    def listar_fornecimentos(self, produto_id: str | None, offset: int, limite: int) -> tuple[list[dict], int]:
        filtro = "WHERE produto_id = %s" if produto_id is not None else ""
        parametros = (produto_id,) if produto_id is not None else ()
        linhas = self._executar(f"SELECT {COLUNAS_FORNECIMENTO} FROM fornecimentos.fornecimento {filtro} "
                                "ORDER BY criado_em, id LIMIT %s OFFSET %s", parametros + (limite, offset), "todos")
        total = self._executar(f"SELECT count(*) FROM fornecimentos.fornecimento {filtro}", parametros, "um")[0]
        return [_fornecimento(linha) for linha in linhas], total

    def aplicar_movimento(self, fornecimento_id: str, delta_disponivel: Decimal, delta_reservada: Decimal,
                          atualizado_em: datetime) -> dict | None:
        linha = self._executar(
            "UPDATE fornecimentos.fornecimento SET quantidade_disponivel = quantidade_disponivel + %s, "
            "quantidade_reservada = quantidade_reservada + %s, atualizado_em = %s "
            "WHERE id = %s AND quantidade_disponivel + %s >= 0 AND quantidade_reservada + %s >= 0 "
            f"RETURNING {COLUNAS_FORNECIMENTO}",
            (delta_disponivel, delta_reservada, atualizado_em, fornecimento_id, delta_disponivel, delta_reservada), "um")
        return _fornecimento(linha) if linha else None

    def obter_reserva(self, pedido_id: str, fornecimento_id: str) -> dict | None:
        linha = self._executar("SELECT pedido_id, fornecimento_id, quantidade, situacao, criado_em, atualizado_em "
                               "FROM fornecimentos.reserva WHERE pedido_id = %s AND fornecimento_id = %s",
                               (pedido_id, fornecimento_id), "um")
        if linha is None:
            return None
        return {"pedido_id": linha[0], "fornecimento_id": linha[1], "quantidade": linha[2], "situacao": linha[3],
                "criado_em": _instante(linha[4]), "atualizado_em": _instante(linha[5])}

    def salvar_reserva(self, reserva: dict) -> None:
        self._executar(
            "INSERT INTO fornecimentos.reserva (pedido_id, fornecimento_id, quantidade, situacao, criado_em, atualizado_em) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (pedido_id, fornecimento_id) DO UPDATE SET "
            "quantidade = EXCLUDED.quantidade, situacao = EXCLUDED.situacao, atualizado_em = EXCLUDED.atualizado_em",
            (reserva["pedido_id"], reserva["fornecimento_id"], reserva["quantidade"], reserva["situacao"],
             reserva["criado_em"], reserva["atualizado_em"]))

    def disponivel(self) -> bool:
        try:
            self._executar("SELECT 1", buscar="um")
            return True
        except Exception:
            return False
