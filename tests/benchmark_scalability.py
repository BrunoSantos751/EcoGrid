import sys
import os
import time
import random
import matplotlib.pyplot as plt  

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models.graph import EcoGridGraph
from src.core.models.node import NodeType
from src.core.structures.avl_tree import AVLTree
from src.core.algorithms.routing import EnergyRouter

def run_benchmark():
    print("--- INICIANDO BENCHMARK DE ESCALABILIDADE  ---")
    
    # Tamanhos de rede para testar (Escala Logarítmica: 100 -> 100.000)
    sizes = [100, 500, 1000, 5000, 10000, 20000, 50000, 100000]
    
    avl_insert_times = []
    avl_search_times = []
    astar_times = []
    
    for n in sizes:
        print(f"\nTestando com N = {n} nós...")
        
        # 1. Preparação
        graph = EcoGridGraph()
        avl = AVLTree()
        ids = list(range(n))
        random.shuffle(ids) # Embaralha para testar o balanceamento da AVL
        
        # --- TESTE 1: Inserção na AVL (e no Grafo) ---
        start_time = time.time()
        for i in ids:
            # Cria nó e insere na AVL
            node = graph.add_node(i, NodeType.CONSUMER, 100.0)
            avl.insert(i, node)
        end_time = time.time()
        avg_insert = (end_time - start_time) / n
        avl_insert_times.append(avg_insert * 1000) # ms
        
        # --- TESTE 2: Busca na AVL ---
        # Buscamos 1000 nós aleatórios para tirar uma média
        search_targets = random.sample(ids, min(n, 1000))
        start_time = time.time()
        for i in search_targets:
            avl.search(i)
        end_time = time.time()
        avg_search = (end_time - start_time) / len(search_targets)
        avl_search_times.append(avg_search * 1000) # ms
        
        # --- TESTE 3: Roteamento A* ---
        # Conecta o grafo aleatoriamente (Topologia tipo 'Small World')
        # Cada nó conecta com ~3 outros próximos
        edges_count = 0
        for i in range(n - 5):
            # Conecta com alguns vizinhos à frente
            graph.add_edge(i, i+1, distance=1.0, resistance=0.1)
            graph.add_edge(i, i+2, distance=1.0, resistance=0.1)
            # Conexão aleatória de longo alcance (atalho)
            if random.random() < 0.05: 
                target = random.randint(0, n-1)
                if target != i:
                    graph.add_edge(i, target, distance=10.0, resistance=0.5)
        
        router = EnergyRouter(graph)
        # Rota do início ao fim (pior caso provável)
        start_time = time.time()
        router.find_path_a_star(0, n-1, verbose=False) # Desliga logs para não sujar tempo
        end_time = time.time()
        astar_duration = end_time - start_time
        astar_times.append(astar_duration * 1000) # ms
        
        print(f"   > Inserção (méd): {avl_insert_times[-1]:.4f} ms")
        print(f"   > Busca (méd):    {avl_search_times[-1]:.4f} ms")
        print(f"   > Rota A*:        {astar_times[-1]:.2f} ms")

    # --- GERAR GRÁFICO (Prova Visual) ---
    plot_results(sizes, avl_insert_times, avl_search_times, astar_times)

def plot_results(sizes, inserts, searches, routes):
    plt.figure(figsize=(12, 5))
    
    # Gráfico 1: Estruturas de Dados (AVL)
    plt.subplot(1, 2, 1)
    plt.plot(sizes, inserts, marker='o', label='Inserção AVL')
    plt.plot(sizes, searches, marker='x', label='Busca AVL')
    plt.xlabel('Número de Nós (N)')
    plt.ylabel('Tempo Médio (ms)')
    plt.title('Performance AVL: O(log n)')
    plt.legend()
    plt.grid(True)
    
    # Gráfico 2: Algoritmo (A*)
    plt.subplot(1, 2, 2)
    plt.plot(sizes, routes, marker='s', color='orange', label='Roteamento A*')
    plt.xlabel('Número de Nós (N)')
    plt.ylabel('Tempo Total (ms)')
    plt.title('Performance A*: O(E log V)')
    plt.legend()
    plt.grid(True)
    
    # Salva em imagem para colocar no relatório
    plt.savefig("data/benchmark_results.png")
    print("\n>> Gráfico salvo em 'data/benchmark_results.png'")
    plt.show()

if __name__ == "__main__":
    run_benchmark()