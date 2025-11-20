from src.core.structures.circular_buffer.py import CircularBuffer # type: ignore

class NodeType:
    """Enumeração para os tipos de nós hierárquicos."""
    SUBSTATION = "SUBESTACAO"       # Fonte de energia
    TRANSFORMER = "TRANSFORMADOR"   # Nó intermediário
    CONSUMER = "CONSUMIDOR"         # Ponto final (casas/indústrias)

class PowerNode:
    """
    Representa um nó físico na rede elétrica.
    Atende aos critérios da Issue #2: Capacidades limitadas e tipos definidos.
    """
    def __init__(self, node_id: int, node_type: str, max_capacity: float):
        self.id = node_id
        self.type = node_type
        self.max_capacity = max_capacity  # Limite físico em kW/kVA 
        self.current_load = 0.0           # Carga atual
        self.active = True                # Simulação de falhas (On/Off) 
        self.x = x  # Coordenada X (ou Latitude)
        self.y = y  # Coordenada Y (ou Longitude) #"ADICIONEI ESSES DOIS NOVOS ATRIBUTOS PARA CÁLCULO DA HEURISTICA" LUCAS
        
    @property
    def is_overloaded(self) -> bool:
        """Verifica se o nó está acima da capacidade permitida."""
        return self.current_load > self.max_capacity

    def __repr__(self):
        status = "OK" if self.active else "FALHA"
        return f"[{self.type}] ID:{self.id} | Carga: {self.current_load}/{self.max_capacity} | Status: {status}"
    
    def update_load(self, new_load: float):
        """Atualiza a carga atual e registra no histórico."""
        self.current_load = new_load
        self.readings_buffer.add(new_load)
