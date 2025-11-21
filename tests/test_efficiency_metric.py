import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models.graph import EcoGridGraph
from src.core.models.node import NodeType
from src.core.algorithms.heuristics import EnergyHeuristics

def test_global_efficiency():
    print("--- Iniciando Teste da Métrica Global E (Issue #14) ---")
    
    graph = EcoGridGraph()
    
    # 1. Criar Nós com Carga e Eficiência
    # Nó 1: Carga 100, Eficiência 1.0 -> Numerador += 100
    n1 = graph.add_node(1, NodeType.SUBSTATION, 1000, x=0, y=0, efficiency=1.0)
    n1.update_load(100)
    
    # Nó 2: Carga 50, Eficiência 0.8 -> Numerador += 40
    n2 = graph.add_node(2, NodeType.CONSUMER, 100, x=10, y=0, efficiency=0.8)
    n2.update_load(50)
    
    # Numerador Esperado = 100 + 40 = 140
    
    # 2. Criar Linha (Perda)
    # Dist 10, Res 1.0, Eff 1.0 -> Peso = 10.0
    graph.add_edge(1, 2, distance=10.0, resistance=1.0, efficiency=1.0)
    
    # Denominador Esperado = 10.0 (Soma única das perdas)
    
    # 3. Calcular E
    E = EnergyHeuristics.calculate_global_efficiency(graph)
    
    print(f"Numerador (Útil): {140}")
    print(f"Denominador (Perda): {10}")
    print(f"Eficiência E Calculada: {E}")
    
    expected_E = 140 / 10.0 # = 14.0
    
    assert E == expected_E, f"Erro no cálculo de E. Esperado {expected_E}, obteve {E}"
    print(">> SUCESSO: Métrica de eficiência global validada.")

if __name__ == "__main__":
    test_global_efficiency()