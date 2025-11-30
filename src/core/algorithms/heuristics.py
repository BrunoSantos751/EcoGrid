import math
from src.core.models.node import PowerNode, NodeType

class EnergyHeuristics:
    """
    Implementação das funções heurísticas para o algoritmo A* do EcoGrid+.
    """
    
    MIN_RESISTANCE_PER_KM = 0.05
    MAX_EFFICIENCY = 1.0

    @staticmethod
    def euclidean_distance(node_a: PowerNode, node_b: PowerNode) -> float:
        """Calcula a distância geométrica linear entre dois nós."""
        return math.sqrt((node_a.x - node_b.x)**2 + (node_a.y - node_b.y)**2)

    @staticmethod
    def calculate_h(current_node: PowerNode, target_node: PowerNode) -> float:
        """
        Calcula h(n): Estimativa de custo energético baseada em física.
        Fórmula: (Dist_Euclidiana * Min_Resistência) / Max_Eficiência
        """
        dist = EnergyHeuristics.euclidean_distance(current_node, target_node)
        estimated_loss = (dist * EnergyHeuristics.MIN_RESISTANCE_PER_KM) / EnergyHeuristics.MAX_EFFICIENCY
        return estimated_loss
    
    @staticmethod
    def calculate_global_efficiency(graph) -> float:
        """
        Calcula a eficiência global E da rede usando apenas eficiências (sem voltagem).
        Fórmula: E = (Σ(Cn * ηn)) / (ΣPn)
        onde:
        - Cn = carga de cada nó
        - ηn = eficiência do nó
        - Pn = perdas calculadas usando eficiências
        
        Perdas são calculadas como:
        - Nós: P = C * (1 - η) / η
        - Arestas: P = C * (1 - η_edge) / η_edge
        """
        total_useful_load = 0.0
        total_losses = 0.0
        processed_edges = set()

        for node in graph.nodes.values():
            if node.active:
                total_useful_load += node.current_load * node.efficiency

        for node in graph.nodes.values():
            if node.active and node.current_load > 0:
                if node.efficiency > 0 and node.efficiency < 1.0:
                    node_losses = node.current_load * (1.0 - node.efficiency) / node.efficiency
                    total_losses += node_losses

        for node_id, edges in graph.adj_list.items():
            for edge in edges:
                edge_key = tuple(sorted([edge.source, edge.target]))
                if edge_key in processed_edges:
                    continue
                processed_edges.add(edge_key)
                
                source_node = graph.get_node(edge.source)
                target_node = graph.get_node(edge.target)
                
                if not source_node or not target_node or not source_node.active or not target_node.active:
                    continue
                
                load_passing = 0.0
                is_hierarchical = False
                
                if edge.current_flow > 0.1:
                    load_passing = edge.current_flow
                    is_hierarchical = True
                else:
                    if (source_node.type == NodeType.TRANSFORMER and target_node.type == NodeType.CONSUMER):
                        if target_node.parent_id == source_node.id:
                            is_hierarchical = True
                            load_passing = target_node.current_load
                    elif (target_node.type == NodeType.TRANSFORMER and source_node.type == NodeType.CONSUMER):
                        if source_node.parent_id == target_node.id:
                            is_hierarchical = True
                            load_passing = source_node.current_load
                    elif (source_node.type == NodeType.SUBSTATION and target_node.type == NodeType.TRANSFORMER):
                        if target_node.parent_id == source_node.id:
                            is_hierarchical = True
                            load_passing = target_node.current_load
                    elif (target_node.type == NodeType.SUBSTATION and source_node.type == NodeType.TRANSFORMER):
                        if source_node.parent_id == target_node.id:
                            is_hierarchical = True
                            load_passing = source_node.current_load
                
                if is_hierarchical and load_passing > 1.0:
                    if edge.efficiency > 0 and edge.efficiency < 1.0:
                        edge_losses = load_passing * (1.0 - edge.efficiency) / edge.efficiency
                        total_losses += edge_losses

        if total_losses == 0:
            if total_useful_load == 0:
                return 0.0
            return 1000.0

        efficiency = total_useful_load / total_losses
        return min(efficiency, 1000.0)