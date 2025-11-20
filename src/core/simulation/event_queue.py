# src/core/simulation/event_queue.py
import heapq
from collections import deque
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, field

class EventType:
    LOAD_CHANGE = "MUDANCA_CARGA"
    NODE_FAILURE = "FALHA_NO"
    MAINTENANCE = "MANUTENCAO"
    OVERLOAD_WARNING = "ALERTA_SOBRECARGA" # Novo tipo crítico

class PriorityLevel:
    """
    Define a criticidade. 
    Menor número = Maior Prioridade (lógica de Min-Heap).
    """
    CRITICAL = 0  # Blackout, Falha de Nó
    HIGH = 1      # Sobrecarga iminente
    MEDIUM = 2    # Manutenção preventiva
    LOW = 3       # Leitura de rotina / Log

@dataclass(order=True)
class GridEvent:
    """
    Representa um evento na rede.
    Decorador @dataclass(order=True) gera automaticamente os métodos de comparação (__lt__, etc).
    A comparação é feita campo por campo na ordem de declaração.
    """
    priority: int # Primeiro campo: define a ordenação no Heap
    timestamp: datetime = field(compare=False) # Não ordenar por data se prioridade empatar
    event_type: str = field(compare=False)
    node_id: int = field(compare=False)
    payload: Any = field(compare=False, default=None)

    def __repr__(self):
        p_name = "UNKNOWN"
        if self.priority == 0: p_name = "CRITICAL"
        elif self.priority == 1: p_name = "HIGH"
        elif self.priority == 2: p_name = "MEDIUM"
        elif self.priority == 3: p_name = "LOW"
        
        return f"[{p_name}] {self.event_type} -> Node {self.node_id}"

class FIFOEventQueue:
    """Fila simples ."""
    def __init__(self):
        self._queue = deque()

    def enqueue(self, event: GridEvent):
        self._queue.append(event)

    def dequeue(self) -> Optional[GridEvent]:
        return self._queue.popleft() if self._queue else None

    def is_empty(self) -> bool:
        return len(self._queue) == 0
    
    def size(self) -> int:
        return len(self._queue)

class PriorityEventQueue:
    """
    Fila de Prioridade.
    Usa um Min-Heap binário para garantir que eventos CRITICAL saiam primeiro.
    Complexidade: O(log n) para push e pop.
    """
    def __init__(self):
        self._heap = []

    def push(self, event: GridEvent):
        """Insere mantendo a propriedade do Heap (O(log n))."""
        heapq.heappush(self._heap, event)

    def pop(self) -> Optional[GridEvent]:
        """Remove e retorna o evento de maior prioridade (O(log n))."""
        if self.is_empty():
            return None
        return heapq.heappop(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0
    
    def peek(self) -> Optional[GridEvent]:
        return self._heap[0] if not self.is_empty() else None