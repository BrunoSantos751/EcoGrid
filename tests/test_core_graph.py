import sys
import os

# Adiciona o diretório raiz ao path para conseguir importar 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models.graph import EcoGridGraph
from src.core.models.node import NodeType
from src.core.algorithms.heuristics import EnergyHeuristics

def test_create_simple_grid():
    print("--- Iniciando Teste do Grafo ---")
    
    # 1. Instancia o Grafo
    grid = EcoGridGraph()

    # 2. Adiciona Nós 
    substation = grid.add_node(1, NodeType.SUBSTATION, 10000, x=0.0, y=0.0)
    transformer = grid.add_node(2, NodeType.TRANSFORMER, 500, x=3.0, y=0.0) # 3km de dist do nó 1
    consumer = grid.add_node(3, NodeType.CONSUMER, 15, x=3.0, y=4.0)
    
    print(f"Nós criados: {len(grid.nodes)}") # Deve ser 3

    # 3. Adiciona Linhas (Issue #2 - Esquema de Arestas com pesos)
    # Conexão Subestação <-> Transformador (Alta eficiência, longa distância)
    grid.add_edge(1, 2, distance=10.0, resistance=0.05, efficiency=0.99)
    
    # Conexão Transformador <-> Consumidor (Menor distância, maior resistência)
    grid.add_edge(2, 3, distance=0.5, resistance=0.20, efficiency=0.95)

    # 4. Validação dos Pesos (Issue #2 - Fórmula de Custo)
    # Recupera a linha que sai do Transformador (ID 2) para o Consumidor (ID 3)
    lines_from_transformer = grid.get_neighbors(2)
    
    for line in lines_from_transformer:
        print(f"Conexão {line.source} -> {line.target} | Peso calculado: {line.weight:.4f}")
        
        # Validação manual para o Consumidor (ID 3)
        if line.target == 3:
            expected_weight = (0.5 * 0.20) / 0.95 # = 0.1052...
            assert abs(line.weight - expected_weight) < 0.0001, "Erro no cálculo do peso!"
            print(">> Validação de Peso: SUCESSO")
            
    print("\nVerificando Heurística:")
    
    # Distância direta (hipotenusa) entre Subestação (0,0) e Casa (3,4) deve ser 5.0
    dist_direta = EnergyHeuristics.euclidean_distance(substation, consumer)
    print(f"Distância Euclidiana (1 -> 3): {dist_direta}")
    assert dist_direta == 5.0, "Erro no cálculo da distância euclidiana"

    # Custo estimado
    h_val = EnergyHeuristics.calculate_h(substation, consumer)
    print(f"Valor Heurístico h(n): {h_val}")
    
    # (5.0 * 0.05) / 1.0 = 0.25
    expected_h = (5.0 * 0.05) / 1.0
    assert h_val == expected_h, "Erro no cálculo de h(n)"
    
    print(">> SUCESSO: Grafo e Heurística integrados.")
if __name__ == "__main__":
    test_create_simple_grid()