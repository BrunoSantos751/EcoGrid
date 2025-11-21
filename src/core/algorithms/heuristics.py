import math
from src.core.models.node import PowerNode

class EnergyHeuristics:
    """
    Implementação das funções heurísticas para o algoritmo A* do EcoGrid+.
    """
    
    # Defini constantes baseadas nos melhores cabos disponíveis no 'edge.py'
    MIN_RESISTANCE_PER_KM = 0.05  # Exemplo: Melhor cabo da rede
    MAX_EFFICIENCY = 1.0          # Eficiência ideal (100%)

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
        
        # Custo estimado assumindo o cenário ideal de transmissão
        estimated_loss = (dist * EnergyHeuristics.MIN_RESISTANCE_PER_KM) / EnergyHeuristics.MAX_EFFICIENCY
        
        return estimated_loss
    
    @staticmethod
    def calculate_global_efficiency(graph) -> float:
        """
        Calcula a eficiência global E da rede.
        Fórmula: E = (Soma(Carga * Eficiência_Nó)) / (Soma(Perdas_Arestas))
        """
        total_useful_load = 0.0
        total_losses = 0.0

        # 1. Numerador: Carga Ponderada pela Eficiência (Sigma Cn * nn)
        for node in graph.nodes.values():
            if node.active:
                total_useful_load += node.current_load * node.efficiency

        # 2. Denominador: Perdas nas Linhas (Sigma Pn)
        # Usamos o peso da aresta (Weight) como proxy de perda 
        # Precisamos somar apenas arestas únicas ou dividir o total por 2.
        raw_edge_sum = 0.0
        for node_id, edges in graph.adj_list.items():
            for edge in edges:
                raw_edge_sum += edge.weight
        
        # Como cada conexão física aparece 2 vezes (ida e volta), dividimos por 2
        total_losses = raw_edge_sum / 2.0

        # Evitar divisão por zero
        if total_losses == 0:
            return 0.0 if total_useful_load == 0 else float('inf')

        return total_useful_load / total_losses