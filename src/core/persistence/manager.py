import pickle
import os
from src.core.models.graph import EcoGridGraph

class PersistenceManager:
    """
    Responsável por salvar TODOS os dados do EcoGrid em um ÚNICO arquivo.
    """
    # Caminho padrão para salvar tudo
    DEFAULT_PATH = "data/ecogrid_master.db"

    @staticmethod
    def save_all(graph: EcoGridGraph, filepath: str = DEFAULT_PATH):
        """
        Pega as árvores de todos os nós e salva num arquivo só.
        """
        # Garante que a pasta existe
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Agrupa tudo: { id_do_no: arvore_do_no }
        backup_data = {}
        for node_id, node in graph.nodes.items():
            backup_data[node_id] = node.storage_tree
            
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(backup_data, f)
            # print(f"[Persistencia] Salvo {len(backup_data)} nós em {filepath}")
        except Exception as e:
            print(f"[Persistencia Erro] Falha ao salvar: {e}")

    @staticmethod
    def load_all(graph: EcoGridGraph, filepath: str = DEFAULT_PATH):
        """
        Lê o arquivo único e distribui as árvores para os nós certos.
        """
        if not os.path.exists(filepath):
            return

        try:
            with open(filepath, 'rb') as f:
                backup_data = pickle.load(f)
                
            count = 0
            for node_id, tree in backup_data.items():
                # Encontra o nó vivo no sistema e devolve a memória dele
                node = graph.get_node(node_id)
                if node:
                    node.storage_tree = tree
                    count += 1
            # print(f"[Persistencia] Restaurado histórico de {count} nós.")
        except Exception as e:
            print(f"[Persistencia Erro] Falha ao carregar: {e}")