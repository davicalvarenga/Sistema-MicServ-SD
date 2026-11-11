"""Porta EventBus com outbox (ADR-010): os eventos passam por uma tabela antes do Kafka.

`publish` grava o envelope em `<schema>.outbox` e retorna. Uma thread (`iniciar`)
lê os eventos pendentes na ordem em que foram gravados, publica cada um no Kafka e
marca `publicado_em`. Se o Kafka estiver fora, os eventos esperam na tabela e saem
quando ele voltar: nada se perde e o cliente da API não recebe erro por isso.

Garantias e limites:
- Entrega pelo menos uma vez: se o processo cair depois de publicar e antes de
  marcar `publicado_em`, o evento sai de novo. Os consumidores descartam repetidos
  pelo `eventId` (processed_events, ADR-007).
- Ordem por chave: só uma instância publica de cada vez (advisory lock do
  PostgreSQL), lendo por `criado_em` e `event_id`. Se um evento falhar, os
  seguintes do mesmo tópico e da mesma chave esperam a próxima rodada; os de
  outras chaves seguem.
- O envelope é gravado logo depois do commit da alteração, não na mesma
  transação, porque as ESPs mandam publicar depois da transação (ESP-FRN-001,
  §5.1). Se o processo cair exatamente entre o commit e a gravação no outbox, o
  evento se perde. Registrado no Relatório Técnico (seção 13).

Este arquivo é idêntico em produtos-service e fornecimentos-service.
"""

import logging
import threading
import zlib

from psycopg2.extras import Json

logger = logging.getLogger(__name__)

SCHEMAS = ("produtos", "fornecimentos")


class BarramentoOutbox:
    def __init__(self, pool, schema: str, kafka, intervalo: float = 1.0, lote: int = 100):
        if schema not in SCHEMAS:
            raise ValueError(f"schema deve ser um de {SCHEMAS}")
        self._pool = pool
        self._tabela = f"{schema}.outbox"
        self._kafka = kafka
        self._intervalo = intervalo
        self._lote = lote
        # Chave do advisory lock: fixa por schema, para que as instâncias do mesmo serviço se excluam
        self._trava = zlib.crc32(f"outbox:{schema}".encode("utf-8"))
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    def publish(self, topic: str, key: str, message: dict) -> None:
        conexao = self._pool.getconn()
        try:
            with conexao, conexao.cursor() as cursor:
                # clock_timestamp() (e não now()) dá horários distintos a eventos gravados em sequência
                cursor.execute(
                    f"INSERT INTO {self._tabela} (event_id, topico, chave, envelope, criado_em) "
                    "VALUES (%s, %s, %s, %s, clock_timestamp()) ON CONFLICT (event_id) DO NOTHING",
                    (message["eventId"], topic, key, Json(message)),
                )
        finally:
            self._pool.putconn(conexao)

    def subscribe(self, topic: str, handler) -> None:
        self._kafka.subscribe(topic, handler)

    def disponivel(self) -> bool:
        return self._kafka.disponivel()

    def publicar_pendentes(self) -> int:
        """Publica uma rodada de eventos pendentes e devolve quantos saíram."""
        conexao = self._pool.getconn()
        try:
            with conexao, conexao.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", (self._trava,))
                if not cursor.fetchone()[0]:
                    return 0
                cursor.execute(
                    f"SELECT event_id, topico, chave, envelope FROM {self._tabela} "
                    "WHERE publicado_em IS NULL ORDER BY criado_em, event_id LIMIT %s",
                    (self._lote,),
                )
                publicados = 0
                bloqueados: set[tuple[str, str]] = set()
                for event_id, topico, chave, envelope in cursor.fetchall():
                    if (topico, chave) in bloqueados:
                        continue
                    try:
                        self._kafka.publish(topico, chave, envelope)
                    except Exception as erro:
                        logger.warning("evento %s continua no outbox (topico %s): %s", event_id, topico, erro)
                        if not self._kafka.disponivel():
                            break  # broker fora: tentar os demais só gastaria o tempo limite de cada um
                        bloqueados.add((topico, chave))
                        continue
                    cursor.execute(f"UPDATE {self._tabela} SET publicado_em = clock_timestamp() WHERE event_id = %s",
                                   (event_id,))
                    publicados += 1
                return publicados
        finally:
            self._pool.putconn(conexao)

    def iniciar(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._executar, name="publicador-outbox", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        if self._thread is not None:
            self._thread.join(timeout=15)

    def _executar(self) -> None:
        while not self._parar.is_set():
            try:
                publicados = self.publicar_pendentes()
            except Exception:
                logger.exception("falha na rodada do publicador do outbox")
                publicados = 0
            # Rodada cheia: pode haver mais pendentes, então segue sem esperar
            if publicados < self._lote:
                self._parar.wait(self._intervalo)
