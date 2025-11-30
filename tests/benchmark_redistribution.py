import sys
import os
import time
import random
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models.node import PowerNode, NodeType
from src.core.structures.avl_tree import AVLTree

# --- ADVERSÁRIO: Árvore Binária Comum (Sem Balanceamento) ---
class BSTNode:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.left = None
        self.right = None

class UnbalancedBST:
    """
    Árvore Binária de Busca Padrão.
    Não faz rotações. Se inserir dados ordenados, ela degenera numa linha.
    """
    def __init__(self):
        self.root = None

    def insert(self, key, value):
        if not self.root:
            self.root = BSTNode(key, value)
        else:
            self._insert_rec(self.root, key, value)

    def _insert_rec(self, node, key, value):
        if key < node.key:
            if node.left is None: node.left = BSTNode(key, value)
            else: self._insert_rec(node.left, key, value)
        elif key > node.key:
            if node.right is None: node.right = BSTNode(key, value)
            else: self._insert_rec(node.right, key, value)

    def search(self, key):
        return self._search_rec(self.root, key)

    def _search_rec(self, node, key):
        if node is None or node.key == key:
            return node
        if key < node.key:
            return self._search_rec(node.left, key)
        return self._search_rec(node.right, key)

# --- BENCHMARK ---

def run_speed_benchmark():
    print("--- INICIANDO BENCHMARK: AVL (EcoGrid) vs BST (Comum) ---")
    print("Cenário: Inserção de dados sequenciais (O pior caso para árvores)\n")
    
    # Vamos usar tamanhos menores pois a BST vai sofrer MUITO (Recursion Limit)
    # Python tem limite de recursão de 1000. Vamos aumentar ou usar iterativo.
    sys.setrecursionlimit(20000) 
    
    sizes = [500, 1000, 2000, 5000, 10000]
    
    bst_times = []
    avl_times = []
    improvements = []

    for n in sizes:
        print(f"\nConfigurando rede com {n} nós...")
        
        # DADOS SEQUENCIAIS: O Veneno para a BST
        # 0, 1, 2, 3... faz a árvore crescer apenas para a direita.
        keys = list(range(n)) 
        
        # 1. Setup
        bst_sys = UnbalancedBST()
        avl_sys = AVLTree()
        
        # Inserção (Preparo do terreno)
        for k in keys:
            node = PowerNode(k, NodeType.CONSUMER, 100.0)
            bst_sys.insert(k, node)
            avl_sys.insert(k, node)
            
        # 2. O Teste: Busca de Nós (Redistribuição)
        # Buscamos os últimos nós (que estão lá no fundo da BST)
        queries = keys[-1000:] # Pega os 1000 maiores IDs
        
        # --- Medição BST (Unbalanced) ---
        start = time.perf_counter()
        for q in queries:
            bst_sys.search(q)
        duration_bst = time.perf_counter() - start
        bst_times.append(duration_bst)
        
        # --- Medição AVL (EcoGrid) ---
        start = time.perf_counter()
        for q in queries:
            avl_sys.search(q)
        duration_avl = time.perf_counter() - start
        avl_times.append(duration_avl)
        
        # 3. Cálculo
        if duration_bst > 0:
            improvement = ((duration_bst - duration_avl) / duration_bst) * 100
        else:
            improvement = 0
            
        improvements.append(improvement)
        
        print(f"   > Tempo BST (Degenerada): {duration_bst:.5f} s")
        print(f"   > Tempo AVL (Balanceada): {duration_avl:.5f} s")
        print(f"   > Vantagem da AVL:        {improvement:.2f}%")

    # Média Final
    avg_imp = sum(improvements) / len(improvements)
    print(f"\n--- RESULTADO FINAL MÉDIO: {avg_imp:.2f}% ---")
    
    if avg_imp >= 40.0:
        print(">> SUCESSO: A AVL provou ser superior a uma árvore comum no pior caso.")

    plot_comparison(sizes, bst_times, avl_times)

def plot_comparison(sizes, bst, avl):
    plt.figure(figsize=(10, 6))
    plt.plot(sizes, bst, 'r-o', label='BST Comum (Degenerada)')
    plt.plot(sizes, avl, 'g-s', label='EcoGrid+ AVL (Balanceada)')
    
    plt.xlabel('Tamanho da Rede (Nós)')
    plt.ylabel('Tempo de Busca (s)')
    plt.title('AVL vs BST: Impacto do Balanceamento')
    plt.legend()
    plt.grid(True)
    
    if not os.path.exists("data"): os.makedirs("data")
    plt.savefig("data/benchmark_redistribution.png")
    plt.show()

if __name__ == "__main__":
    run_speed_benchmark()