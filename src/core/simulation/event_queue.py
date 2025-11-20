from collections import deque
from datetime import datetime
from typing import Any, Optional

class EventType:
    """Enumeração para tipificar os eventos do sistema."""
    LOAD_CHANGE = "MUDANCA_CARGA"  # Consumo aumentou/diminuiu
    NODE_FAILURE = "FALHA_NO"      # Nó caiu/queimou
    MAINTENANCE = "MANUTENCAO"     # Nó voltou a operar

class GridEvent:
    """
    Representa um evento único na linha do tempo do EcoGrid+.
    Carrega os dados necessários para o sistema reagir.
    """
    def __init__(self, event_type: str, node_id: int, payload: Any = None):
        self.timestamp = datetime.now() # Carimbo de tempo real de criação
        self.type = event_type
        self.node_id = node_id
        self.payload = payload # Dados extras (ex: nova carga em kW)

    def __repr__(self):
        return f"[Event @ {self.timestamp.strftime('%H:%M:%S')}] {self.type} -> Node {self.node_id} | Data: {self.payload}"

class FIFOEventQueue:
    """
    Fila de Eventos (First-In, First-Out).
    Garante a ordem cronológica de processamento.
    """
    def __init__(self):
        self._queue = deque()

    def enqueue(self, event: GridEvent):
        """Adiciona um evento ao final da fila."""
        self._queue.append(event)

    def dequeue(self) -> Optional[GridEvent]:
        """
        Remove e retorna o evento mais antigo (do início da fila).
        Retorna None se a fila estiver vazia.
        """
        if self.is_empty():
            return None
        return self._queue.popleft()

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def size(self) -> int:
        return len(self._queue)

    def peek(self) -> Optional[GridEvent]:
        """Olha o próximo evento sem remover."""
        if self.is_empty():
            return None
        return self._queue[0]