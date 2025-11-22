import pickle
import os
from typing import Dict, List, Any
from src.core.models.graph import EcoGridGraph

class PersistenceManager:
    """
    Gerenciador de Persistência Separada:
    1. Topologia (Estrutura da Rede, Posições, Conexões)
    2. Histórico (Dados de Consumo/B+ Trees)
    """
    PATH_TOPOLOGY = "data/network_topology.pkl"
    PATH_HISTORY = "data/network_history.db"

    # --- PARTE 1: TOPOLOGIA (O Grafo) ---
    
    @staticmethod
    def save_topology(graph: EcoGridGraph, filepath: str = PATH_TOPOLOGY):
        """
        Salva apenas a definição estrutural da rede.
        Não salva os objetos B+ Tree pesados.
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 1. Extrair dados dos Nós (Blueprint)
        nodes_data = []
        for node in graph.nodes.values():
            nodes_data.append({
                'id': node.id,
                'type': node.type,
                'max_capacity': node.max_capacity,
                'x': node.x,
                'y': node.y,
                'efficiency': node.efficiency,
                'active': node.active
            })
            
        # 2. Extrair dados das Arestas (Blueprint)
        edges_data = []
        # Set para evitar duplicatas em grafo não direcionado
        processed_edges = set()
        
        for u_id, lines in graph.adj_list.items():
            for line in lines:
                # Cria uma chave única ordenada para verificar duplicidade (1-2 é igual a 2-1)
                edge_key = tuple(sorted((line.source, line.target)))
                if edge_key not in processed_edges:
                    edges_data.append({
                        'u': line.source,
                        'v': line.target,
                        'dist': line.distance,
                        'res': line.resistance,
                        'eff': line.efficiency
                    })
                    processed_edges.add(edge_key)

        blueprint = {
            'nodes': nodes_data,
            'edges': edges_data
        }

        try:
            with open(filepath, 'wb') as f:
                pickle.dump(blueprint, f)
            # print(f"[Topologia] Estrutura salva em {filepath}")
        except Exception as e:
            print(f"[Topologia Erro] Falha ao salvar: {e}")

    @staticmethod
    def load_topology(graph: EcoGridGraph, filepath: str = PATH_TOPOLOGY) -> bool:
        """
        Lê o arquivo de topologia e reconstrói o grafo.
        Retorna True se conseguiu carregar.
        """
        if not os.path.exists(filepath):
            return False

        try:
            with open(filepath, 'rb') as f:
                blueprint = pickle.load(f)

            # 1. Recriar Nós
            for n_data in blueprint['nodes']:
                node = graph.add_node(
                    node_id=n_data['id'],
                    node_type=n_data['type'],
                    max_capacity=n_data['max_capacity'],
                    x=n_data['x'],
                    y=n_data['y'],
                    efficiency=n_data.get('efficiency', 0.98)
                )
                node.active = n_data.get('active', True)

            # 2. Recriar Arestas
            for e_data in blueprint['edges']:
                graph.add_edge(
                    u_id=e_data['u'],
                    v_id=e_data['v'],
                    distance=e_data['dist'],
                    resistance=e_data['res'],
                    efficiency=e_data['eff']
                )
            
            # print(f"[Topologia] Rede reconstruída: {len(graph.nodes)} nós.")
            return True
            
        except Exception as e:
            print(f"[Topologia Erro] Arquivo corrompido: {e}")
            return False

    # --- PARTE 2: HISTÓRICO (Os Dados) ---

    @staticmethod
    def save_history(graph: EcoGridGraph, filepath: str = PATH_HISTORY):
        """Salva apenas as árvores B+."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        history_data = {}
        for node_id, node in graph.nodes.items():
            history_data[node_id] = node.storage_tree
            
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(history_data, f)
        except Exception as e:
            print(f"[Historico Erro] Falha ao salvar: {e}")

    @staticmethod
    def load_history(graph: EcoGridGraph, filepath: str = PATH_HISTORY):
        """Carrega as árvores e anexa aos nós existentes."""
        if not os.path.exists(filepath):
            return

        try:
            with open(filepath, 'rb') as f:
                history_data = pickle.load(f)
                
            count = 0
            for node_id, tree in history_data.items():
                node = graph.get_node(node_id)
                if node:
                    node.storage_tree = tree
                    count += 1
        except Exception as e:
            print(f"[Historico Erro] Falha ao carregar: {e}")