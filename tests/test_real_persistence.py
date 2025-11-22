import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models.graph import EcoGridGraph
from src.core.models.node import NodeType
from src.core.persistence.manager import PersistenceManager

def test_separated_files():
    path_topo = "data/test_topo.pkl"
    path_hist = "data/test_hist.db"
    
    # Limpa testes anteriores
    if os.path.exists(path_topo): os.remove(path_topo)
    if os.path.exists(path_hist): os.remove(path_hist)
    
    print("\n=== INICIANDO TESTE DIDÁTICO DE PERSISTÊNCIA SEGREGADA ===")
    
    # --- FASE 1 ---
    print("\n--- [FASE 1] Criação e Salvamento ---")
    graph = EcoGridGraph()
    print("1. Grafo vazio instanciado.")
    
    n1 = graph.add_node(1, NodeType.CONSUMER, 100, x=10, y=10)
    print(f"2. Nó 1 (Consumidor) adicionado em (10, 10).")
    
    # Gera dado histórico
    print("3. Simulando leitura de sensor: Carga = 50.0 kW")
    n1.update_load(50.0)
    
    # Salva em dois arquivos
    print(f"4. Salvando arquivo de TOPOLOGIA (Mapa) em: {path_topo}")
    PersistenceManager.save_topology(graph, filepath=path_topo)
    
    print(f"5. Salvando arquivo de HISTÓRICO (Dados) em: {path_hist}")
    PersistenceManager.save_history(graph, filepath=path_hist)
    
    assert os.path.exists(path_topo)
    assert os.path.exists(path_hist)
    print(">> Checkpoint: Arquivos físicos criados com sucesso.")

    # --- FASE 2 ---
    print("\n--- [FASE 2] Carregando Apenas o Mapa (Topologia) ---")
    graph2 = EcoGridGraph()
    print(f"1. Novo Grafo instanciado. Nós atuais: {len(graph2.nodes)}")
    
    PersistenceManager.load_topology(graph2, filepath=path_topo)
    print(f"2. Topologia carregada. Nós atuais: {len(graph2.nodes)}")
    
    # Deve ter o nó 1 (Estrutura)
    node_recuperado = graph2.get_node(1)
    assert node_recuperado is not None
    print(f"3. Nó 1 recuperado com sucesso: {node_recuperado}")
    
    # Mas NÃO deve ter o histórico (Dados)
    print("4. Verificando memória do Nó 1 (Esperado: Vazio)...")
    hist_vazio = node_recuperado.storage_tree.range_search(0, 10)
    print(f"   -> Conteúdo encontrado: {hist_vazio}")
    
    assert len(hist_vazio) == 0, "O histórico não deveria carregar com a topologia!"
    print(">> Checkpoint: Estrutura existe, mas está 'oca' (sem dados históricos).")
    
    # --- FASE 3 ---
    print("\n--- [FASE 3] Injetando o Histórico ---")
    PersistenceManager.load_history(graph2, filepath=path_hist)
    print("1. Arquivo de histórico carregado e processado.")
    
    # Agora o dado deve aparecer
    print("2. Verificando memória do Nó 1 novamente (Esperado: [50.0])...")
    hist_cheio = graph2.get_node(1).storage_tree.range_search(0, 10)
    print(f"   -> Conteúdo encontrado: {hist_cheio}")
    
    assert 50.0 in hist_cheio
    print(">> Checkpoint: Dados históricos foram conectados ao nó corretamente.")
    
    print("\n=== SUCESSO TOTAL: O sistema montou o grafo e depois preencheu os dados ===")
    
    # Limpeza (Comentada para você poder ver os arquivos se quiser)
    #if os.path.exists(path_topo): os.remove(path_topo)
    #if os.path.exists(path_hist): os.remove(path_hist)

if __name__ == "__main__":
    test_separated_files()