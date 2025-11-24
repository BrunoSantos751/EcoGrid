import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models.graph import EcoGridGraph
from src.core.models.node import NodeType
from src.core.structures.avl_tree import AVLTree
from src.core.algorithms.balancing import LoadBalancer

def test_load_balancing():
    print("--- Iniciando Teste de Balanceamento ---")
    
    # 1. Setup do Cenário
    graph = EcoGridGraph()
    avl = AVLTree()
    
    # Nó 1: Pequeno (Capacidade 100)
    node1 = graph.add_node(1, NodeType.TRANSFORMER, max_capacity=100, x=0, y=0)
    avl.insert(1, node1)
    
    # Nó 2: Grande Vizinho (Capacidade 1000) - Está vazio
    node2 = graph.add_node(2, NodeType.TRANSFORMER, max_capacity=1000, x=10, y=0)
    avl.insert(2, node2)
    
    # Conexão entre eles
    graph.add_edge(1, 2, distance=10, resistance=0.1)
    
    # 2. Inicializa o Balanceador
    balancer = LoadBalancer(graph, avl)
    
    # 3. Simula Sobrecarga no Nó 1
    # Capacidade é 100, vamos jogar 150. Excesso = 50.
    print(f"Estado Inicial -> Nó 1: {node1.current_load}/{node1.max_capacity} | Nó 2: {node2.current_load}/{node2.max_capacity}")
    
    print("\n>>> Aplicando carga de 150 no Nó 1 (Sobrecarga)...")
    logs = balancer.update_node_load(1, 150)
    
    # Imprime logs do algoritmo
    for log in logs:
        print(log)
        
    # 4. Validação dos Resultados
    print(f"\nEstado Final -> Nó 1: {node1.current_load}/{node1.max_capacity} | Nó 2: {node2.current_load}/{node2.max_capacity}")
    
    # Nó 1 deve ter ficado com 100 (no limite)
    assert node1.current_load <= 100.0, "Erro: Nó 1 deveria ter baixado para sua capacidade máxima."
    
    # Nó 2 deve ter recebido o excesso (50)
    assert node2.current_load <= 1000.0, "Erro: Nó 2 não recebeu a carga redistribuída."
    
    print(">> SUCESSO: O balanceador redistribuiu a carga corretamente.")

if __name__ == "__main__":
    test_load_balancing()