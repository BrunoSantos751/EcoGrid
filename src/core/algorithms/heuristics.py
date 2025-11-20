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
