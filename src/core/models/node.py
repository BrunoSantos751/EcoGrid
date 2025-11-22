from src.core.structures.b_plus_tree import BPlusTree
from src.core.structures.circular_buffer import CircularBuffer

class NodeType:
    SUBSTATION = "SUBESTACAO"
    TRANSFORMER = "TRANSFORMADOR"
    CONSUMER = "CONSUMIDOR"

class PowerNode:
    """
    Nó da rede elétrica.
    Versão Limpa para Arquivo Único: Não gerencia arquivos individuais.
    """
    def __init__(self, node_id: int, node_type: str, max_capacity: float, x: float = 0.0, y: float = 0.0, efficiency: float = 0.98):
        self.id = node_id
        self.type = node_type
        self.max_capacity = max_capacity
        self.current_load = 0.0
        self.active = True
        self.x = x
        self.y = y
        self.efficiency = efficiency
        
        # Memória de Curto Prazo (Runtime)
        self.readings_buffer = CircularBuffer(capacity=24)
        
        # Memória de Longo Prazo (B+ Tree)
        # O salvamento será feito externamente pelo PersistenceManager.
        self.storage_tree = BPlusTree(order=4) 
        self.internal_clock = 0

    @property
    def is_overloaded(self) -> bool:
        return self.current_load > self.max_capacity

    def update_load(self, new_load: float):
        self.current_load = new_load
        
        # Salva no buffer circular
        self.readings_buffer.add(new_load)
        
        # Salva na árvore (apenas na memória RAM)
        self.storage_tree.insert(self.internal_clock, new_load)
        self.internal_clock += 1

    def __repr__(self):
        status = "OK" if self.active else "FALHA"
        return f"[{self.type}] ID:{self.id} @({self.x},{self.y}) | Carga: {self.current_load}/{self.max_capacity}"