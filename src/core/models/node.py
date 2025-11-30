from src.core.structures.circular_buffer import CircularBuffer

class NodeType:
    SUBSTATION = "SUBESTACAO"
    TRANSFORMER = "TRANSFORMADOR"
    CONSUMER = "CONSUMIDOR"

class PowerNode:
    """
    Nó da rede elétrica com estrutura hierárquica.
    Hierarquia: SUBESTACAO → TRANSFORMADOR → CONSUMIDOR
    """
    def __init__(self, node_id: int, node_type: str, max_capacity: float, x: float = 0.0, y: float = 0.0, efficiency: float = 0.98, parent_id: int = None):
        self.id = node_id
        self.type = node_type
        self.max_capacity = max_capacity
        self.current_load = 0.0
        self.active = True
        self.x = x
        self.y = y
        self.efficiency = efficiency
        
        self.parent_id = parent_id
        self.children_ids = []
        self.readings_buffer = CircularBuffer(capacity=24)
        self.internal_clock = 0
        self.voltage = 220.0
        self.current = 0.0
        self.manual_load = False
        self.last_reactivation_tick = -1

    @property
    def is_overloaded(self) -> bool:
        return self.current_load > self.max_capacity

    def update_load(self, new_load: float):
        """Atualiza a carga do nó e registra no buffer circular."""
        self.current_load = new_load
        
        if self.voltage > 0:
            self.current = new_load / self.voltage
        
        self.readings_buffer.add(new_load)
        self.internal_clock += 1
    
    @property
    def available_capacity(self) -> float:
        return max(0.0, self.max_capacity - self.current_load)
    
    @property
    def load_percentage(self) -> float:
        if self.max_capacity == 0:
            return 0.0
        return self.current_load / self.max_capacity

    def __repr__(self):
        status = "OK" if self.active else "FALHA"
        return f"[{self.type}] ID:{self.id} @({self.x},{self.y}) | Carga: {self.current_load}/{self.max_capacity}"
