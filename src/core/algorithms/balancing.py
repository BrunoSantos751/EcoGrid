from typing import List, Tuple
from src.core.models.graph import EcoGridGraph
from src.core.models.node import PowerNode
from src.core.structures.avl_tree import AVLTree

class LoadBalancer:
    """
    Responsável pela lógica de redistribuição de energia.
    Detecta sobrecarga e tenta balancear a rede.
    """
    def __init__(self, graph: EcoGridGraph, avl_index: AVLTree):
        self.graph = graph
        self.avl = avl_index

    def update_node_load(self, node_id: int, new_load: float) -> List[str]:
        """
        Atualiza a carga de um nó e verifica se é necessário balanceamento.
        Retorna uma lista de logs/ações tomadas.
        """
        logs = []
        
        # 1. Busca Rápida na AVL (O(log n)) [cite: 28, 54]
        node = self.avl.search(node_id)
        
        if not node:
            return [f"Erro: Nó {node_id} não encontrado na AVL."]

        # 2. Atualiza a carga física e o histórico (Buffer)
        old_load = node.current_load
        node.update_load(new_load)
        logs.append(f"Nó {node_id}: Carga alterada {old_load} -> {new_load} kW")

        # 3. Verifica Sobrecarga 
        if node.is_overloaded:
            logs.append(f"ALERTA: Nó {node_id} sobrecarregado! ({node.current_load}/{node.max_capacity})")
            actions = self._attempt_redistribution(node)
            logs.extend(actions)
        
        return logs

    def _attempt_redistribution(self, overloaded_node: PowerNode) -> List[str]:
        """
        Tenta mover o excesso de carga para vizinhos diretos com capacidade ociosa.
        Lógica simplificada de 'Load Shedding' para vizinhos.
        """
        actions = []
        excess_load = overloaded_node.current_load - overloaded_node.max_capacity
        
        # Busca vizinhos no grafo físico 
        neighbors_edges = self.graph.get_neighbors(overloaded_node.id)
        
        actions.append(f"Tentando redistribuir {excess_load:.2f} kW para {len(neighbors_edges)} vizinhos...")

        for edge in neighbors_edges:
            if excess_load <= 0:
                break

            neighbor_id = edge.target if edge.source == overloaded_node.id else edge.source
            neighbor = self.avl.search(neighbor_id) # Busca rápida via AVL

            if neighbor and neighbor.active:
                # Verifica quanto o vizinho aguenta
                available_capacity = neighbor.max_capacity - neighbor.current_load
                
                if available_capacity > 0:
                    # Transfere o que der (ou tudo que precisa, ou tudo que o vizinho aguenta)
                    transfer_amount = min(excess_load, available_capacity)
                    
                    # Aplica a transferência física
                    neighbor.update_load(neighbor.current_load + transfer_amount)
                    overloaded_node.update_load(overloaded_node.current_load - transfer_amount)
                    
                    excess_load -= transfer_amount
                    actions.append(f" >> Transferido {transfer_amount:.2f} kW para Vizinho {neighbor_id}")

        if excess_load > 0:
            actions.append(f"FALHA CRÍTICA: Não foi possível redistribuir tudo. Excesso restante: {excess_load:.2f} kW")
            # falta implementar o A* para buscar vizinhos distantes 
        else:
            actions.append("SUCESSO: Carga balanceada entre vizinhos.")

        return actions