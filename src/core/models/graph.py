from typing import Dict, List
from src.core.models.node import PowerNode
from src.core.models.edge import PowerLine

class EcoGridGraph:
    """
    Grafo hierárquico e não direcionado da rede elétrica.
    Mantém estrutura hierárquica: SUBESTACAO → TRANSFORMADOR → CONSUMIDOR
    """
    def __init__(self):
        # Dicionário para acesso rápido aos nós por ID: {id: PowerNode}
        self.nodes: Dict[int, PowerNode] = {}
        
        # Lista de Adjacência para as conexões: {id: [PowerLine, ...]}
        self.adj_list: Dict[int, List[PowerLine]] = {}
        
        # Estrutura hierárquica explícita
        self.root_nodes: List[int] = []  # IDs das subestações (raiz da hierarquia)

    def add_node(self, node_id: int, node_type: str, max_capacity: float, x: float = 0, y: float = 0, efficiency: float = 0.98, parent_id: int = None) -> PowerNode:
        """
        Adiciona um nó ao grafo mantendo a hierarquia.
        Se parent_id for None e for SUBESTACAO, adiciona como raiz.
        """
        if node_id not in self.nodes:
            new_node = PowerNode(node_id, node_type, max_capacity, x, y, efficiency, parent_id)
            self.nodes[node_id] = new_node
            self.adj_list[node_id] = [] # Inicializa lista de vizinhos vazia
            
            # Mantém hierarquia explícita
            if node_type == "SUBESTACAO" and parent_id is None:
                if node_id not in self.root_nodes:
                    self.root_nodes.append(node_id)
            elif parent_id is not None and parent_id in self.nodes:
                # Adiciona como filho do pai
                parent = self.nodes[parent_id]
                if node_id not in parent.children_ids:
                    parent.children_ids.append(node_id)
            
            return new_node
        return self.nodes[node_id]
    
    def get_children(self, node_id: int) -> List[PowerNode]:
        """Retorna os nós filhos na hierarquia."""
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[child_id] for child_id in node.children_ids if child_id in self.nodes]
    
    def get_parent(self, node_id: int) -> PowerNode:
        """Retorna o nó pai na hierarquia."""
        node = self.nodes.get(node_id)
        if not node or node.parent_id is None:
            return None
        return self.nodes.get(node.parent_id)

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
    
    def get_edge_obj(self, u_id: int, v_id: int):
        """Retorna o objeto PowerLine que conecta U e V."""
        if u_id in self.adj_list:
            for line in self.adj_list[u_id]:
                if line.target == v_id:
                    return line
        return None

    def get_node(self, node_id: int) -> PowerNode:
        """Recupera um objeto PowerNode pelo ID."""
        return self.nodes.get(node_id)