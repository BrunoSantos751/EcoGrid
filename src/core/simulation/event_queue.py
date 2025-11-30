import heapq
from collections import deque, Counter
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict, Callable
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
    Fila de Prioridade aprimorada.
    Usa um Min-Heap binário para garantir que eventos CRITICAL saiam primeiro.
    Complexidade: O(log n) para push e pop.
    
    Melhorias implementadas:
    - Remoção de eventos específicos
    - Atualização de prioridade
    - Estatísticas da fila
    - Limpeza de eventos obsoletos
    - Limite de tamanho opcional
    - Verificação de existência de eventos
    """
    def __init__(self, max_size: Optional[int] = None):
        """
        Inicializa a fila de prioridade.
        
        Args:
            max_size: Tamanho máximo da fila. Se None, não há limite.
                     Quando atingido, eventos LOW são descartados primeiro.
        """
        self._heap = []
        self._max_size = max_size

    def push(self, event: GridEvent, check_duplicates: bool = True) -> bool:
        """
        Insere mantendo a propriedade do Heap (O(log n)).
        
        Args:
            event: Evento a ser inserido
            check_duplicates: Se True, remove eventos duplicados (mesmo node_id e event_type)
                            antes de inserir o novo
        
        Returns:
            True se o evento foi inserido, False se foi descartado (fila cheia)
        """
        # Verifica duplicatas se solicitado
        if check_duplicates:
            self._remove_duplicates(event.node_id, event.event_type)
        
        # Verifica limite de tamanho
        if self._max_size is not None and len(self._heap) >= self._max_size:
            # Se a fila está cheia, tenta descartar eventos LOW primeiro
            if event.priority == PriorityLevel.LOW:
                return False  # Descarta evento LOW se fila cheia
            
            # Remove o evento de menor prioridade (último no heap ordenado)
            # Para manter eficiência, removemos eventos LOW se existirem
            low_events = [e for e in self._heap if e.priority == PriorityLevel.LOW]
            if low_events:
                self._heap.remove(low_events[0])
                heapq.heapify(self._heap)
            else:
                # Se não há eventos LOW, descarta o novo evento
                return False
        
        heapq.heappush(self._heap, event)
        return True

    def pop(self) -> Optional[GridEvent]:
        """Remove e retorna o evento de maior prioridade (O(log n))."""
        if self.is_empty():
            return None
        return heapq.heappop(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0
    
    def peek(self) -> Optional[GridEvent]:
        """Retorna o próximo evento sem removê-lo."""
        return self._heap[0] if not self.is_empty() else None
    
    def get_all_events(self) -> List[GridEvent]:
        """
        Retorna uma lista ordenada de todos os eventos na fila sem removê-los.
        Útil para visualização em tempo real.
        Complexidade: O(n log n) devido à ordenação.
        """
        if self.is_empty():
            return []
        # Retorna uma cópia ordenada do heap (não modifica o original)
        return sorted(self._heap.copy())
    
    def get_events_by_priority(self, priority: int) -> List[GridEvent]:
        """
        Retorna todos os eventos de uma prioridade específica.
        
        Args:
            priority: Nível de prioridade (PriorityLevel.CRITICAL, HIGH, etc.)
        
        Returns:
            Lista de eventos com a prioridade especificada
        """
        return [e for e in self._heap if e.priority == priority]
    
    def get_events_by_node(self, node_id: int) -> List[GridEvent]:
        """
        Retorna todos os eventos relacionados a um nó específico.
        
        Args:
            node_id: ID do nó
        
        Returns:
            Lista de eventos do nó
        """
        return [e for e in self._heap if e.node_id == node_id]
    
    def has_event(self, node_id: int, event_type: str) -> bool:
        """
        Verifica se existe um evento específico na fila.
        
        Args:
            node_id: ID do nó
            event_type: Tipo do evento
        
        Returns:
            True se o evento existe, False caso contrário
        """
        return any(e.node_id == node_id and e.event_type == event_type for e in self._heap)
    
    def remove_event(self, node_id: int, event_type: str) -> bool:
        """
        Remove um evento específico da fila.
        
        Args:
            node_id: ID do nó
            event_type: Tipo do evento
        
        Returns:
            True se o evento foi removido, False se não foi encontrado
        """
        original_size = len(self._heap)
        self._heap = [e for e in self._heap if not (e.node_id == node_id and e.event_type == event_type)]
        
        if len(self._heap) < original_size:
            heapq.heapify(self._heap)  # Reorganiza o heap após remoção
            return True
        return False
    
    def _remove_duplicates(self, node_id: int, event_type: str):
        """Remove eventos duplicados (mesmo node_id e event_type) antes de inserir novo."""
        original_size = len(self._heap)
        self._heap = [e for e in self._heap if not (e.node_id == node_id and e.event_type == event_type)]
        
        if len(self._heap) < original_size:
            heapq.heapify(self._heap)
    
    def update_priority(self, node_id: int, event_type: str, new_priority: int) -> bool:
        """
        Atualiza a prioridade de um evento existente.
        Útil para escalar eventos quando a situação piora.
        
        Args:
            node_id: ID do nó
            event_type: Tipo do evento
            new_priority: Nova prioridade (menor = mais prioritário)
        
        Returns:
            True se o evento foi atualizado, False se não foi encontrado
        """
        # Encontra o evento
        event_to_update = None
        for e in self._heap:
            if e.node_id == node_id and e.event_type == event_type:
                event_to_update = e
                break
        
        if event_to_update is None:
            return False
        
        # Remove o evento antigo
        self._heap.remove(event_to_update)
        heapq.heapify(self._heap)
        
        # Cria novo evento com prioridade atualizada
        updated_event = GridEvent(
            priority=new_priority,
            timestamp=event_to_update.timestamp,
            event_type=event_to_update.event_type,
            node_id=event_to_update.node_id,
            payload=event_to_update.payload
        )
        
        # Insere o evento atualizado
        heapq.heappush(self._heap, updated_event)
        return True
    
    def clear_old_events(self, max_age_seconds: float = 300.0) -> int:
        """
        Remove eventos mais antigos que o limite especificado.
        
        Args:
            max_age_seconds: Idade máxima em segundos (padrão: 5 minutos)
        
        Returns:
            Número de eventos removidos
        """
        if self.is_empty():
            return 0
        
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=max_age_seconds)
        
        original_size = len(self._heap)
        self._heap = [e for e in self._heap if e.timestamp > cutoff_time]
        
        removed_count = original_size - len(self._heap)
        if removed_count > 0:
            heapq.heapify(self._heap)
        
        return removed_count
    
    def clear_by_priority(self, priority: int) -> int:
        """
        Remove todos os eventos de uma prioridade específica.
        
        Args:
            priority: Nível de prioridade a ser removido
        
        Returns:
            Número de eventos removidos
        """
        original_size = len(self._heap)
        self._heap = [e for e in self._heap if e.priority != priority]
        
        removed_count = original_size - len(self._heap)
        if removed_count > 0:
            heapq.heapify(self._heap)
        
        return removed_count
    
    def clear_by_filter(self, filter_func: Callable[[GridEvent], bool]) -> int:
        """
        Remove eventos que atendem a um critério específico.
        
        Args:
            filter_func: Função que retorna True para eventos que devem ser removidos
        
        Returns:
            Número de eventos removidos
        """
        original_size = len(self._heap)
        self._heap = [e for e in self._heap if not filter_func(e)]
        
        removed_count = original_size - len(self._heap)
        if removed_count > 0:
            heapq.heapify(self._heap)
        
        return removed_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas sobre a fila de eventos.
        
        Returns:
            Dicionário com estatísticas:
            - total: Total de eventos
            - by_priority: Contagem por nível de prioridade
            - by_type: Contagem por tipo de evento
            - oldest_timestamp: Timestamp do evento mais antigo
            - newest_timestamp: Timestamp do evento mais recente
        """
        if self.is_empty():
            return {
                'total': 0,
                'by_priority': {},
                'by_type': {},
                'oldest_timestamp': None,
                'newest_timestamp': None
            }
        
        priorities = [e.priority for e in self._heap]
        event_types = [e.event_type for e in self._heap]
        timestamps = [e.timestamp for e in self._heap]
        
        # Mapeia prioridades para nomes
        priority_names = {
            PriorityLevel.CRITICAL: 'CRITICAL',
            PriorityLevel.HIGH: 'HIGH',
            PriorityLevel.MEDIUM: 'MEDIUM',
            PriorityLevel.LOW: 'LOW'
        }
        
        by_priority = {}
        for priority, count in Counter(priorities).items():
            by_priority[priority_names.get(priority, f'UNKNOWN_{priority}')] = count
        
        return {
            'total': len(self._heap),
            'by_priority': by_priority,
            'by_type': dict(Counter(event_types)),
            'oldest_timestamp': min(timestamps) if timestamps else None,
            'newest_timestamp': max(timestamps) if timestamps else None
        }
    
    def size(self) -> int:
        """Retorna o número de eventos na fila."""
        return len(self._heap)
    
    def clear(self):
        """Remove todos os eventos da fila."""
        self._heap.clear()