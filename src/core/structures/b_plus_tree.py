# src/core/structures/b_plus_tree.py
import pickle
import os
from typing import List, Any, Optional

class BPlusNode:
    """
    Nó da Árvore B+.
    - Se folha: 'children' contém os valores (dados).
    - Se interno: 'children' contém referências para outros BPlusNode.
    """
    def __init__(self, is_leaf: bool = False):
        self.is_leaf = is_leaf
        self.keys = []
        self.children = [] 
        self.next_leaf = None 

class BPlusTree:
    """
    Implementação robusta de Árvore B+ com Persistência Real em Disco.
    Atende Issue #5.
    """
    def __init__(self, order: int = 4, filepath: str = "ecogrid_data.db"):
        self.root = BPlusNode(is_leaf=True)
        self.order = order
        self.filepath = filepath
        
        # Tenta carregar dados existentes ao iniciar
        self.load_from_disk()

    def save_to_disk(self):
        """Salva o estado atual da árvore no arquivo."""
        try:
            # Garante que o diretório existe antes de salvar
            directory = os.path.dirname(self.filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            with open(self.filepath, 'wb') as f:
                data = {
                    'order': self.order,
                    'root': self.root
                }
                pickle.dump(data, f)
        except Exception as e:
            print(f"[IO Erro] Falha ao salvar no disco: {e}")

    def load_from_disk(self):
        """Carrega a árvore do arquivo se existir."""
        if not os.path.exists(self.filepath):
            return 
            
        try:
            with open(self.filepath, 'rb') as f:
                data = pickle.load(f)
                self.order = data['order']
                self.root = data['root']
            # print(f"[IO] Dados carregados de {self.filepath}")
        except Exception as e:
            print(f"[IO Erro] Falha ao carregar (iniciando vazio): {e}")

    def insert(self, key: float, value: Any):
        """Insere um par chave/valor e persiste no disco."""
        root = self.root
        
        # Lógica de split da raiz
        if len(root.keys) == self.order - 1:
            new_root = BPlusNode(is_leaf=False)
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root
            self._insert_non_full(new_root, key, value)
        else:
            self._insert_non_full(root, key, value)
            
        # WRITE-THROUGH: Salva imediatamente após a inserção
        self.save_to_disk()

    def _insert_non_full(self, node: BPlusNode, key: float, value: Any):
        if node.is_leaf:
            # Inserção ordenada na folha
            pos = 0
            while pos < len(node.keys) and key > node.keys[pos]:
                pos += 1
            
            node.keys.insert(pos, key)
            node.children.insert(pos, value)
            
        else:
            # Nó interno
            pos = 0
            while pos < len(node.keys) and key > node.keys[pos]:
                pos += 1
            
            if len(node.children[pos].keys) == self.order - 1:
                self._split_child(node, pos)
                if key > node.keys[pos]:
                    pos += 1
            
            self._insert_non_full(node.children[pos], key, value)

    def _split_child(self, parent: BPlusNode, index: int):
        node_to_split = parent.children[index]
        mid_point = len(node_to_split.keys) // 2
        
        new_node = BPlusNode(is_leaf=node_to_split.is_leaf)
        
        if node_to_split.is_leaf:
            # Split de Folha
            new_node.keys = node_to_split.keys[mid_point:]
            new_node.children = node_to_split.children[mid_point:] 
            
            node_to_split.keys = node_to_split.keys[:mid_point]
            node_to_split.children = node_to_split.children[:mid_point]
            
            # Sobe a chave (cópia)
            promoted_key = new_node.keys[0]
            
            parent.keys.insert(index, promoted_key)
            parent.children.insert(index + 1, new_node)
            
            # Lista ligada
            new_node.next_leaf = node_to_split.next_leaf
            node_to_split.next_leaf = new_node
            
        else:
            # Split Interno
            promoted_key = node_to_split.keys[mid_point]
            
            new_node.keys = node_to_split.keys[mid_point + 1:]
            new_node.children = node_to_split.children[mid_point + 1:]
            
            node_to_split.keys = node_to_split.keys[:mid_point]
            node_to_split.children = node_to_split.children[:mid_point + 1]
            
            parent.keys.insert(index, promoted_key)
            parent.children.insert(index + 1, new_node)

    def range_search(self, start_key: float, end_key: float) -> List[Any]:
        """Busca intervalo e retorna valores."""
        results = []
        current = self.root
        while not current.is_leaf:
            i = 0
            while i < len(current.keys) and start_key > current.keys[i]:
                i += 1
            current = current.children[i]
            
        while current:
            for i, key in enumerate(current.keys):
                if key >= start_key:
                    if key <= end_key:
                        if i < len(current.children):
                            results.append(current.children[i])
                    else:
                        return results
            current = current.next_leaf
        return results