"""Puerto de transacción para los casos de uso (patrón Unit of Work).

Un caso de uso que escribe en varios repositorios confirma todo o nada. La
``Session`` de SQLAlchemy ya cumple este protocolo.
"""

from typing import Protocol


class TransactionManager(Protocol):
    def commit(self) -> None: ...

    def rollback(self) -> None: ...
