import sys
import os

# Setup de importação
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.structures.avl_tree import AVLTree
from src.core.models.node import PowerNode, NodeType

def test_avl_balancing():
    print("--- Iniciando Teste da AVL (Issue #4) ---")
    
    avl = AVLTree()
    
    # Cenário: Inserção sequencial que desbalancearia uma árvore comum
    # Inserindo 10, 20, 30...
    ids_to_insert = [10, 20, 30, 40, 50, 25]
    
    print(f"Inserindo IDs na ordem: {ids_to_insert}")
    
    for node_id in ids_to_insert:
        # Criando um nó dummy só para teste
        p_node = PowerNode(node_id, NodeType.CONSUMER, 100)
        avl.insert(node_id, p_node)

    # Validação 1: A raiz não deve ser 10 (que foi o primeiro), 
    # pois a árvore deve ter girado para balancear.
    root_key = avl.root.key
    print(f"Raiz da árvore após balanceamento: {root_key}")
    
    # Numa árvore binária simples inserindo 10, 20, 30, a raiz seria 10.
    # Vamos verificar a altura. Para 6 nós, altura ideal é ~3.
    height = avl._get_height(avl.root)
    print(f"Altura da árvore: {height}")
    
    if height <= 4: 
        print(">> SUCESSO: A altura está controlada (logarítmica).")
    else:
        print(">> FALHA: A árvore degenerou.")

    # Validação 2: Busca
    search_id = 40
    found_node = avl.search(search_id)
    if found_node and found_node.id == 40:
        print(f">> SUCESSO: Busca pelo ID {search_id} retornou o objeto correto.")
    else:
        print(f">> FALHA: Não encontrou o ID {search_id}.")

if __name__ == "__main__":
    test_avl_balancing()