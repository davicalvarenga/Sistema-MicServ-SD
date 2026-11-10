"""Porta Clock: relógio do sistema em UTC."""

from datetime import datetime, timezone


class RelogioSistema:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
