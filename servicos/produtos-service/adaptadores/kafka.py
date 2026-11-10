"""Porta EventBus sobre o Redpanda/Kafka, com confluent-kafka.

Produtor com acks=all e idempotência (ADR-009). Publicação síncrona: publish só
retorna depois da confirmação do broker. O consumo roda numa thread e confirma o
offset depois que o handler termina; os handlers do serviço nunca propagam exceção
e mandam para a DLT as mensagens que não conseguem processar.
"""

import json
import logging
import threading

from confluent_kafka import Consumer, KafkaException, Producer

logger = logging.getLogger(__name__)


class BarramentoKafka:
    def __init__(self, bootstrap_servers: str, grupo_consumidor: str, timeout_publicacao: float = 10.0):
        self._bootstrap = bootstrap_servers
        self._grupo = grupo_consumidor
        self._timeout = timeout_publicacao
        self._produtor = Producer({"bootstrap.servers": bootstrap_servers, "acks": "all", "enable.idempotence": True})
        self._handlers: dict[str, list] = {}
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    def publish(self, topic: str, key: str, message: dict) -> None:
        falhas = []

        def ao_entregar(erro, _mensagem):
            if erro is not None:
                falhas.append(erro)

        self._produtor.produce(topic, key=key.encode("utf-8"), value=json.dumps(message, ensure_ascii=False).encode("utf-8"),
                               on_delivery=ao_entregar)
        pendentes = self._produtor.flush(self._timeout)
        if pendentes or falhas:
            raise KafkaException(f"Falha ao publicar em {topic}: {falhas or 'tempo esgotado'}")

    def subscribe(self, topic: str, handler) -> None:
        self._handlers.setdefault(topic, []).append(handler)

    def disponivel(self) -> bool:
        try:
            self._produtor.list_topics(timeout=2)
            return True
        except Exception:
            return False

    def iniciar(self) -> None:
        """Começa a consumir os tópicos inscritos, se houver algum."""
        if not self._handlers or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._consumir, name="consumidor-kafka", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        if self._thread is not None:
            self._thread.join(timeout=10)

    def _consumir(self) -> None:
        consumidor = Consumer({
            "bootstrap.servers": self._bootstrap,
            "group.id": self._grupo,
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        })
        consumidor.subscribe(list(self._handlers))
        try:
            while not self._parar.is_set():
                registro = consumidor.poll(1.0)
                if registro is None:
                    continue
                if registro.error():
                    logger.warning("erro do consumidor kafka: %s", registro.error())
                    continue
                try:
                    mensagem = json.loads(registro.value())
                except (ValueError, TypeError):
                    # Mensagem que não é JSON: o handler recebe o texto e a envia para a DLT.
                    mensagem = registro.value().decode("utf-8", errors="replace") if registro.value() else None
                for handler in self._handlers.get(registro.topic(), []):
                    handler(mensagem)
                consumidor.commit(message=registro, asynchronous=False)
        finally:
            consumidor.close()
