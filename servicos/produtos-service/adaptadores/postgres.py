"""Porta ProdutoRepositorio sobre o schema `produtos` do PostgreSQL 16.

Conecta com o usuário svc_produtos (RNF-24) e no máximo 5 conexões (RNF-23).
Depende da proposta de DDL em docs/banco/.
"""

from datetime import timezone

from psycopg2.pool import ThreadedConnectionPool

COLUNAS = ("id, nome, categoria, unidade, tipo_transporte, peso_unitario_kg, cadastrado_por_empresa_id, "
           "cadastrado_por_usuario_id, criado_em")


def _instante(momento) -> str:
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _produto(linha) -> dict:
    return {
        "produto_id": linha[0], "nome": linha[1], "categoria": linha[2], "unidade": linha[3], "tipo_transporte": linha[4],
        "peso_unitario_kg": linha[5], "cadastrado_por_empresa_id": linha[6], "cadastrado_por_usuario_id": linha[7],
        "cadastrado_em": _instante(linha[8]),
    }


class RepositorioProdutosPostgres:
    def __init__(self, dsn: str, max_conexoes: int = 5):
        self._pool = ThreadedConnectionPool(1, max_conexoes, dsn)

    def _executar(self, sql: str, parametros=(), buscar: str | None = None):
        conexao = self._pool.getconn()
        try:
            with conexao, conexao.cursor() as cursor:
                cursor.execute(sql, parametros)
                if buscar == "um":
                    return cursor.fetchone()
                if buscar == "todos":
                    return cursor.fetchall()
                return None
        finally:
            self._pool.putconn(conexao)

    def inserir(self, produto: dict) -> None:
        self._executar(
            f"INSERT INTO produtos.produto ({COLUNAS}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (produto["produto_id"], produto["nome"], produto["categoria"], produto["unidade"], produto["tipo_transporte"],
             produto["peso_unitario_kg"], produto["cadastrado_por_empresa_id"], produto["cadastrado_por_usuario_id"], produto["cadastrado_em"]),
        )

    def obter(self, produto_id: str) -> dict | None:
        linha = self._executar(f"SELECT {COLUNAS} FROM produtos.produto WHERE id = %s", (produto_id,), "um")
        return _produto(linha) if linha else None

    def listar(self, categoria: str | None, offset: int, limite: int) -> tuple[list[dict], int]:
        filtro = "WHERE categoria = %s" if categoria is not None else ""
        parametros = (categoria,) if categoria is not None else ()
        linhas = self._executar(
            f"SELECT {COLUNAS} FROM produtos.produto {filtro} ORDER BY criado_em, id LIMIT %s OFFSET %s",
            parametros + (limite, offset), "todos")
        total = self._executar(f"SELECT count(*) FROM produtos.produto {filtro}", parametros, "um")[0]
        return [_produto(linha) for linha in linhas], total

    def disponivel(self) -> bool:
        try:
            self._executar("SELECT 1", buscar="um")
            return True
        except Exception:
            return False
