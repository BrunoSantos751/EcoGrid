import heapq
from typing import List, Optional, Dict
from src.core.models.graph import EcoGridGraph
from src.core.algorithms.heuristics import EnergyHeuristics

class EnergyRouter:
    """
    Implementa o algoritmo A* para encontrar rotas de energia eficientes.
    """
    def __init__(self, graph: EcoGridGraph):
        self.graph = graph

    def find_path_a_star(self, start_node_id: int, target_node_id: int, verbose: bool = True) -> Optional[List[int]]:
        """
        Executa o A* para achar a rota de menor perda energética.
        Args:
            verbose: Se True, imprime o passo a passo da decisão.
        """
        start_node = self.graph.get_node(start_node_id)
        target_node = self.graph.get_node(target_node_id)
        
        if not start_node or not target_node:
            if verbose: print("Erro: Nós inválidos.")
            return None

        if verbose:
            print(f"\n[A* START] Buscando rota de {start_node_id} para {target_node_id}")
            dist_geo = EnergyHeuristics.euclidean_distance(start_node, target_node)
            print(f"[A* INFO] Distância Euclidiana direta: {dist_geo:.2f} km")

        open_set = []
        heapq.heappush(open_set, (0.0, start_node_id))
        came_from: Dict[int, int] = {}

        g_score: Dict[int, float] = {node_id: float('inf') for node_id in self.graph.nodes}
        g_score[start_node_id] = 0.0

        f_score: Dict[int, float] = {node_id: float('inf') for node_id in self.graph.nodes}
        h_start = EnergyHeuristics.calculate_h(start_node, target_node)
        f_score[start_node_id] = h_start

        while open_set:
            current_f, current_id = heapq.heappop(open_set)

            if verbose:
                print(f"\n  > Explorando Nó {current_id} (f_score atual: {current_f:.4f})")

            if current_id == target_node_id:
                if verbose: print(f"[A* SUCCESS] Destino {target_node_id} alcançado!")
                return self._reconstruct_path(came_from, current_id)

            neighbors_edges = self.graph.get_neighbors(current_id)
            
            for edge in neighbors_edges:
                neighbor_id = edge.target if edge.source == current_id else edge.source
                tentative_g_score = g_score[current_id] + edge.weight

                if tentative_g_score < g_score[neighbor_id]:
                    came_from[neighbor_id] = current_id
                    g_score[neighbor_id] = tentative_g_score
                    
                    neighbor_node = self.graph.get_node(neighbor_id)
                    h_score = EnergyHeuristics.calculate_h(neighbor_node, target_node)
                    f_score[neighbor_id] = g_score[neighbor_id] + h_score
                    
                    if verbose:
                        print(f"    - Vizinho {neighbor_id}: Novo g={tentative_g_score:.4f}, h={h_score:.4f} -> f={f_score[neighbor_id]:.4f}")
                        if edge.resistance > 0.5:
                            print(f"      (! ALERTA: Linha {current_id}-{neighbor_id} tem alta resistência! Penalizando...)")

                    heapq.heappush(open_set, (f_score[neighbor_id], neighbor_id))

        if verbose: print("[A* FAIL] Caminho não encontrado.")
        return None

    def _reconstruct_path(self, came_from: Dict[int, int], current_id: int) -> List[int]:
        path = [current_id]
        while current_id in came_from:
            current_id = came_from[current_id]
            path.append(current_id)
        return path[::-1]