import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models.graph import EcoGridGraph
from src.core.models.node import NodeType
from src.core.algorithms.routing import EnergyRouter

def test_a_star_routing():
    print("--- Iniciando Teste do Roteamento A* ---")
    
    # 1. Setup do Grafo "Armadilha"
    graph = EcoGridGraph()
    
    # Nó Inicial (0,0) e Final (10,0)
    graph.add_node(1, NodeType.SUBSTATION, 10000, x=0, y=0)
    graph.add_node(99, NodeType.CONSUMER, 500, x=10, y=0)
    
    # Caminho A (Direto, mas Ruim): Distância 10km, Resistência ALTA (1.0)
    # Custo = (10 * 1.0) / 0.99 ~= 10.1
    graph.add_edge(1, 99, distance=10.0, resistance=1.0, efficiency=0.99)
    
    # Caminho B (Longo, mas Bom): Passa por um nó intermediário
    # Nó Intermediário em (5, 5) - Faz um triângulo
    graph.add_node(2, NodeType.TRANSFORMER, 5000, x=5, y=5)
    
    # Perna 1 -> 2: Distancia ~7km, Resistência BAIXA (0.1)
    # Custo = (7.07 * 0.1) / 0.99 ~= 0.71
    graph.add_edge(1, 2, distance=7.07, resistance=0.1, efficiency=0.99)
    
    # Perna 2 -> 99: Distancia ~7km, Resistência BAIXA (0.1)
    # Custo = (7.07 * 0.1) / 0.99 ~= 0.71
    graph.add_edge(2, 99, distance=7.07, resistance=0.1, efficiency=0.99)
    
    # Custo Total Caminho A: ~10.1
    # Custo Total Caminho B: ~1.42 (Muito melhor, apesar de ser mais longo em km!)

    # 2. Executa o Roteador
    router = EnergyRouter(graph)
    print("Buscando rota de 1 para 99...")
    
    path = router.find_path_a_star(1, 99)
    print(f"Rota Encontrada: {path}")
    
    # 3. Validação
    # O algoritmo deve escolher passar pelo nó 2 ([1, 2, 99]) e não ir direto ([1, 99])
    assert path == [1, 2, 99], f"Erro: O A* escolheu o caminho errado/ineficiente: {path}"
    
    print(">> SUCESSO: O A* evitou a linha ruim e achou o caminho energeticamente eficiente.")

if __name__ == "__main__":
    test_a_star_routing()