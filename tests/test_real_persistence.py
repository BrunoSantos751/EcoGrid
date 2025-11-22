# tests/test_single_file.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models.graph import EcoGridGraph
from src.core.models.node import NodeType
from src.core.persistence.manager import PersistenceManager

def test_single_file_persistence():
    db_path = "data/ecogrid_master_test.db"
    
    # Limpa teste anterior
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print("--- Fase 1: Criando Rede e Salvando ---")
    graph = EcoGridGraph()
    n1 = graph.add_node(1, NodeType.CONSUMER, 100)
    n2 = graph.add_node(2, NodeType.CONSUMER, 100)
    
    # Inserindo dados
    n1.update_load(50.0)
    n2.update_load(80.0)
    
    # Salvando TUDO no arquivo único
    PersistenceManager.save_all(graph, filepath=db_path)
    print("Snapshot salvo em arquivo único.")

    print("\n--- Fase 2: Carregando em nova sessão ---")
    new_graph = EcoGridGraph()
    new_graph.add_node(1, NodeType.CONSUMER, 100) # Recria estrutura
    new_graph.add_node(2, NodeType.CONSUMER, 100)
    
    # Carrega do arquivo único
    PersistenceManager.load_all(new_graph, filepath=db_path)
    
    # Verifica se os dados voltaram para os nós certos
    hist_n1 = new_graph.get_node(1).storage_tree.range_search(0, 10)
    hist_n2 = new_graph.get_node(2).storage_tree.range_search(0, 10)
    
    print(f"Nó 1 recuperou: {hist_n1}")
    print(f"Nó 2 recuperou: {hist_n2}")
    
    assert 50.0 in hist_n1
    assert 80.0 in hist_n2
    
    print(">> SUCESSO: Tudo salvo em um único arquivo .db!")
    
    # Limpeza (Opcional)
    if os.path.exists(db_path):
        #pass
        os.remove(db_path)

if __name__ == "__main__":
    test_single_file_persistence()