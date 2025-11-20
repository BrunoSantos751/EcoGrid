from typing import Dict, List
from src.core.models.node import PowerNode
from src.core.models.edge import PowerLine

class EcoGridGraph:
    """
    Grafo hierárquico e não direcionado da rede elétrica.
    """
    def __init__(self):
        # Dicionário para acesso rápido aos nós por ID: {id: PowerNode}
        self.nodes: Dict[int, PowerNode] = {}
        
        # Lista de Adjacência para as conexões: {id: [PowerLine, ...]}
        self.adj_list: Dict[int, List[PowerLine]] = {}

    def add_node(self, node_id: int, node_type: str, max_capacity: float, x: float = 0, y: float = 0) -> PowerNode:
        """Adiciona um nó ao grafo se ele não existir."""
        if node_id not in self.nodes:
            new_node = PowerNode(node_id, node_type, max_capacity, x, y)
            self.nodes[node_id] = new_node
            self.adj_list[node_id] = [] # Inicializa lista de vizinhos vazia
            return new_node
        return self.nodes[node_id]

    def add_edge(self, u_id: int, v_id: int, distance: float, resistance: float, efficiency: float = 0.99):
        """
        Cria uma conexão bidirecional (Não direcionada).
        Isso permite redundância de rotas: a energia pode fluir de U->V ou V->U.
        """
        if u_id in self.nodes and v_id in self.nodes:
            # Sentido U -> V
            line_uv = PowerLine(u_id, v_id, distance, resistance, efficiency)
            self.adj_list[u_id].append(line_uv)

            # Sentido V -> U (Mesmos parâmetros físicos)
            line_vu = PowerLine(v_id, u_id, distance, resistance, efficiency)
            self.adj_list[v_id].append(line_vu)
        else:
            raise ValueError(f"Tentativa de conectar nós inexistentes: {u_id}, {v_id}")

    def get_neighbors(self, node_id: int) -> List[PowerLine]:
        """Retorna todas as linhas conectadas a um nó específico."""
        return self.adj_list.get(node_id, [])

    def get_node(self, node_id: int) -> PowerNode:
        """Recupera um objeto PowerNode pelo ID."""
        return self.nodes.get(node_id)