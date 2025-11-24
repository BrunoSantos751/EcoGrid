# src/core/algorithms/balancing.py
from typing import List, Set, Tuple
from src.core.models.graph import EcoGridGraph
from src.core.models.node import PowerNode
from src.core.structures.avl_tree import AVLTree

class LoadBalancer:
    """
    Responsável pela lógica de redistribuição de energia.
    Atualizado: Algoritmo de Propagação Profunda (Deep Cascade) para encontrar 
    capacidade em qualquer lugar da rede conectada.
    """
    TARGET_LOAD_PCT = 0.70     
    EMERGENCY_CAP_PCT = 0.99   # Em cascata, aceitamos encher até a borda para salvar o vizinho
    MAX_CASCADE_DEPTH = 15     # Aumentado para percorrer a rede quase toda se necessário

    def __init__(self, graph: EcoGridGraph, avl_index: AVLTree):
        self.graph = graph
        self.avl = avl_index

    def update_node_load(self, node_id: int, new_load: float) -> List[str]:
        logs = []
        node = self.avl.search(node_id)
        if not node: return [f"Erro: Nó {node_id} não encontrado."]

        node.update_load(new_load)
        
        # Meta de segurança
        target_load = node.max_capacity * self.TARGET_LOAD_PCT
        
        if node.current_load > target_load:
            pct = (node.current_load / node.max_capacity) * 100
            status = "CRÍTICO" if pct > 100 else "ALERTA"
            logs.append(f"{status}: Nó {node_id} atingiu {pct:.1f}%")
            
            # Inicia a busca profunda por espaço
            actions = self._distribute_cascade(node, target_load, visited={node.id}, depth=self.MAX_CASCADE_DEPTH)
            logs.extend(actions)
        
        return logs

    def _distribute_cascade(self, source: PowerNode, target_abs: float, visited: Set[int], depth: int) -> List[str]:
        actions = []
        excess = source.current_load - target_abs
        
        if excess <= 0.1: return []
        if depth <= 0: return [] # Limite de segurança da recursão

        # 1. Identificar Vizinhos
        candidates = self._get_sorted_neighbors(source)

        for score, neighbor, nid in candidates:
            if excess <= 1.0: break
            if nid in visited: continue # Evita ciclo (A->B->A)

            # --- PASSO 1: QUANTO O VIZINHO AGUENTA AGORA? ---
            neighbor_limit = neighbor.max_capacity * self.EMERGENCY_CAP_PCT
            room = neighbor_limit - neighbor.current_load

            # --- PASSO 2: SE NÃO TIVER ESPAÇO, MANDE ELE ABRIR ESPAÇO ---
            if room < excess:
                # Adiciona o vizinho atual à lista de visitados para a próxima etapa
                next_visited = visited.copy()
                next_visited.add(nid)
                
                # "Empurra" o vizinho: Tente ficar com 70% da sua carga para me ajudar
                neighbor_target = neighbor.max_capacity * self.TARGET_LOAD_PCT
                
                # Recursão! O vizinho vai tentar jogar a carga dele para frente
                cascade_logs = self._distribute_cascade(neighbor, neighbor_target, next_visited, depth - 1)
                
                if cascade_logs:
                    # Se ele conseguiu se mexer, recalculamos o espaço
                    room = neighbor_limit - neighbor.current_load
                    # actions.extend(cascade_logs) # (Opcional: Descomente para ver o log completo da cadeia)

            # --- PASSO 3: TRANSFERÊNCIA ---
            if room > 1.0:
                amount = min(excess, room)
                
                # 1. Efetiva a física (Nós)
                neighbor.update_load(neighbor.current_load + amount)
                source.update_load(source.current_load - amount)
                
                # 2. NOVO: Registra o fluxo na aresta (Visualização)
                edge_obj = self.graph.get_edge_obj(source.id, nid)
                if edge_obj:
                    # Soma ao fluxo existente (caso haja múltiplas transferências no mesmo tick)
                    edge_obj.current_flow += amount
                    
                    # Atualiza também a aresta inversa (grafo não direcionado visualmente)
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
                # Ordena por % de Carga (Mais vazio primeiro)
                neighbor_pct = neighbor.current_load / neighbor.max_capacity
                # Fator de resistência ajuda a decidir entre dois vazios iguais
                score = neighbor_pct + (edge.resistance * 0.05)
                candidates.append((score, neighbor, nid))
        
        candidates.sort(key=lambda x: x[0])
        return candidates