from typing import List, Set, Tuple
from src.core.models.graph import EcoGridGraph
from src.core.models.node import PowerNode
from src.core.structures.avl_tree import AVLTree
from src.core.structures.load_avl_tree import LoadAVLTree

class LoadBalancer:
    """
    Responsável pela lógica de redistribuição de energia usando AVL Tree.
    Conforme especificação: "Quando um nó se desequilibra (diferença de alturas > 1),
    uma rotação simples ou dupla é aplicada, assegurando que a árvore continue balanceada."
    
    Usa duas AVL Trees:
    1. avl_index: Para busca rápida por ID (O(log n))
    2. load_avl: Para balanceamento por capacidade disponível (O(log n))
    """
    TARGET_LOAD_PCT = 0.70
    EMERGENCY_CAP_PCT = 0.99
    MAX_CASCADE_DEPTH = 15

    def __init__(self, graph: EcoGridGraph, avl_index: AVLTree):
        self.graph = graph
        self.avl = avl_index
        self.load_avl = LoadAVLTree()
        self._rebuild_load_avl()

    def _rebuild_load_avl(self):
        """Reconstrói a AVL de carga com todos os nós ativos."""
        self.load_avl = LoadAVLTree()
        for node in self.graph.nodes.values():
            if node.active:
                self.load_avl.insert(node)

    def update_node_load(self, node_id: int, new_load: float) -> List[str]:
        """
        Atualiza a carga de um nó e redistribui usando AVL Tree se necessário.
        Conforme especificação: usa rotações AVL para balanceamento.
        """
        logs = []
        node = self.avl.search(node_id)
        if not node: 
            return [f"Erro: Nó {node_id} não encontrado."]

        node.update_load(new_load)
        self.load_avl.update_node(node)
        target_load = node.max_capacity * self.TARGET_LOAD_PCT
        
        if node.current_load > target_load:
            pct = (node.current_load / node.max_capacity) * 100
            status = "CRÍTICO" if pct > 100 else "ALERTA"
            logs.append(f"{status}: Nó {node_id} atingiu {pct:.1f}%")
            excess = node.current_load - target_load
            actions = self._redistribute_using_avl(node, excess, visited={node.id})
            logs.extend(actions)
        
        return logs
    
    def _redistribute_using_avl(self, source: PowerNode, excess: float, visited: Set[int]) -> List[str]:
        """
        Redistribui carga usando AVL Tree organizada por capacidade disponível.
        Respeita a hierarquia - energia não pode fluir para cima.
        """
        actions = []
        if excess <= 0.1:
            return actions
        
        candidates = self.load_avl.get_all_nodes_sorted()
        candidates.reverse()
        
        for candidate in candidates:
            if excess <= 0.1:
                break
            
            if candidate.id in visited or not candidate.active:
                continue
            
            if not self._can_transfer_to(source, candidate):
                continue
            
            if not self._are_connected(source.id, candidate.id):
                continue
            
            available = candidate.available_capacity
            if available <= 0.1:
                continue
            
            transfer = min(excess, available * 0.8)
            
            if transfer > 0.1:
                candidate.update_load(candidate.current_load + transfer)
                source.update_load(source.current_load - transfer)
                self.load_avl.update_node(candidate)
                self.load_avl.update_node(source)
                excess -= transfer
                
                edge = self.graph.get_edge_obj(source.id, candidate.id)
                if edge:
                    edge.current_flow += transfer
                
                pct = (candidate.current_load / candidate.max_capacity) * 100
                actions.append(f" >> AVL Balance: {transfer:.0f}kW -> Nó {candidate.id} ({pct:.0f}%)")
        
        if excess > 0.1:
            cascade_actions = self._distribute_cascade(source, source.max_capacity * self.TARGET_LOAD_PCT, visited, self.MAX_CASCADE_DEPTH)
            actions.extend(cascade_actions)
        
        return actions
    
    def _are_connected(self, node_id1: int, node_id2: int) -> bool:
        """Verifica se dois nós estão conectados no grafo."""
        neighbors = self.graph.get_neighbors(node_id1)
        for edge in neighbors:
            if edge.target == node_id2 or edge.source == node_id2:
                return True
        return False
    
    def _can_transfer_to(self, source: PowerNode, target: PowerNode) -> bool:
        """
        Verifica se uma transferência de energia é válida segundo a hierarquia.
        Energia não pode fluir para cima na hierarquia.
        """
        from src.core.models.node import NodeType
        
        if source.type == NodeType.CONSUMER and target.type == NodeType.CONSUMER:
            return False
        
        if source.type == NodeType.TRANSFORMER and target.type == NodeType.CONSUMER:
            return False
        
        if source.type == target.type:
            if source.type == NodeType.SUBSTATION:
                return self._are_connected(source.id, target.id)
            if source.type == NodeType.TRANSFORMER:
                return False
        
        hierarchy = {
            NodeType.SUBSTATION: 1,
            NodeType.TRANSFORMER: 2,
            NodeType.CONSUMER: 3
        }
        
        source_level = hierarchy.get(source.type, 999)
        target_level = hierarchy.get(target.type, 999)
        
        if target_level < source_level:
            return False
        
        return self._are_connected(source.id, target.id)

    def _distribute_cascade(self, source: PowerNode, target_abs: float, visited: Set[int], depth: int) -> List[str]:
        actions = []
        excess = source.current_load - target_abs
        
        if excess <= 0.1:
            return []
        if depth <= 0:
            return []

        candidates = self._get_sorted_neighbors(source)

        for score, neighbor, nid in candidates:
            if excess <= 1.0:
                break
            if nid in visited:
                continue

            if not self._can_transfer_to(source, neighbor):
                continue

            neighbor_limit = neighbor.max_capacity * self.EMERGENCY_CAP_PCT
            room = neighbor_limit - neighbor.current_load

            if room < excess:
                next_visited = visited.copy()
                next_visited.add(nid)
                neighbor_target = neighbor.max_capacity * self.TARGET_LOAD_PCT
                cascade_logs = self._distribute_cascade(neighbor, neighbor_target, next_visited, depth - 1)
                
                if cascade_logs:
                    room = neighbor_limit - neighbor.current_load

            if room > 1.0:
                amount = min(excess, room)
                neighbor.update_load(neighbor.current_load + amount)
                source.update_load(source.current_load - amount)
                
                edge_obj = self.graph.get_edge_obj(source.id, nid)
                if edge_obj:
                    edge_obj.current_flow += amount
                    edge_reverse = self.graph.get_edge_obj(nid, source.id)
                    if edge_reverse:
                        edge_reverse.current_flow += amount
                
                excess -= amount
                n_pct = (neighbor.current_load / neighbor.max_capacity) * 100
                actions.append(f" >> Repasse: {amount:.0f}kW -> Vizinho {nid} ({n_pct:.0f}%)")
        return actions

    def _get_sorted_neighbors(self, source: PowerNode) -> List[Tuple[float, PowerNode, int]]:
        raw_neighbors = self.graph.get_neighbors(source.id)
        candidates = []

        for edge in raw_neighbors:
            nid = edge.target if edge.source == source.id else edge.source
            neighbor = self.avl.search(nid)

            if neighbor and neighbor.active:
                neighbor_pct = neighbor.current_load / neighbor.max_capacity
                score = neighbor_pct + (edge.resistance * 0.05)
                candidates.append((score, neighbor, nid))
        
        candidates.sort(key=lambda x: x[0])
        return candidates