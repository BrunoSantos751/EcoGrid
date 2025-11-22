import sys
import os
import shutil

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.core.structures.b_plus_tree import BPlusTree

def test_disk_persistence():
    db_path = "test_persistence.db"
    
    # Limpa teste anterior
    if os.path.exists(db_path):
        os.remove(db_path)

    print("--- Fase 1: Escrevendo dados e fechando programa ---")
    tree = BPlusTree(order=4, filepath=db_path)
    tree.insert(10, "Dado Importante 1")
    tree.insert(20, "Dado Importante 2")
    print("Dados inseridos na árvore. Objeto será destruído.")
    del tree # Deleta da memória RAM

    print("\n--- Fase 2: Reiniciando do zero (Lendo do Disco) ---")
    new_tree = BPlusTree(order=4, filepath=db_path)
    
    # Se a persistência funcionar, o range_search vai achar os dados
    results = new_tree.range_search(0, 30)
    print(f"Dados recuperados do disco: {results}")
    
    assert "Dado Importante 1" in results
    assert "Dado Importante 2" in results
    
    print(">> SUCESSO: Os dados sobreviveram ao desligamento do programa!")
    
    # Limpeza
    if os.path.exists(db_path):
        #pass
        os.remove(db_path) #remove o arquivo de teste (cuidados com arquivos reais)

if __name__ == "__main__":
    test_disk_persistence()