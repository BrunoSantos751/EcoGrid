# src/core/structures/b_plus_tree.py
from typing import List, Any, Optional

class BPlusNode:
    """
    Nó da Árvore B+. Pode ser interno (índices) ou folha (dados reais).
    """
    def __init__(self, is_leaf: bool = False):
        self.is_leaf = is_leaf
        self.keys = []
        self.children = []  # Se interno: Lista de BPlusNode. Se folha: Lista de valores (DataPoints)
        self.next_leaf = None  # Ponteiro para a próxima folha (Lista Ligada)

class BPlusTree:
    """
    Implementação in-memory de uma Árvore B+.
    Propriedades chave:
    1. Dados apenas nas folhas.
    2. Folhas conectadas (Range Query eficiente).
    3. Auto-balanceada via split (cresce para cima).
    """
    def __init__(self, order: int = 4):
        self.root = BPlusNode(is_leaf=True)
        self.order = order  # Fator de ramificação (máximo de filhos)

    def insert(self, key: float, value: Any):
        """Insere um par chave(timestamp)/valor(carga)."""
        root = self.root
        
        # Se a raiz encher, divide e cria nova raiz
        if len(root.keys) == self.order - 1:
            new_root = BPlusNode(is_leaf=False)
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root
            self._insert_non_full(new_root, key, value)
        else:
            self._insert_non_full(root, key, value)

    def _insert_non_full(self, node: BPlusNode, key: float, value: Any):
        i = len(node.keys) - 1
        
        if node.is_leaf:
            # Inserção ordenada na folha
            node.keys.append(None)
            node.children.append(None)
            while i >= 0 and key < node.keys[i]:
                node.keys[i + 1] = node.keys[i]
                node.children[i + 1] = node.children[i]
                i -= 1
            node.keys[i + 1] = key
            node.children[i + 1] = value
        else:
            # Busca o filho correto
            while i >= 0 and key < node.keys[i]:
                i -= 1
            i += 1
            
            if len(node.children[i].keys) == self.order - 1:
                self._split_child(node, i)
                if key > node.keys[i]:
                    i += 1
            self._insert_non_full(node.children[i], key, value)

    def _split_child(self, parent: BPlusNode, index: int):
        """Divide um nó cheio e sobe a mediana para o pai."""
        node_to_split = parent.children[index]
        mid_point = (self.order - 1) // 2
        
        new_node = BPlusNode(is_leaf=node_to_split.is_leaf)
        
        # Move chaves/filhos para o novo nó
        parent.keys.insert(index, node_to_split.keys[mid_point])
        parent.children.insert(index + 1, new_node)
        
        new_node.keys = node_to_split.keys[mid_point + 1:]
        node_to_split.keys = node_to_split.keys[:mid_point]
        
        if node_to_split.is_leaf:
            # Se for folha, mantém a chave mediana na direita (duplicação) e copia valores
            new_node.children = node_to_split.children[mid_point + 1:]
            node_to_split.children = node_to_split.children[:mid_point + 1]
            node_to_split.keys.append(parent.keys[index]) # Bota de volta na folha
            new_node.children.insert(0, node_to_split.children.pop()) # Ajusta valor
            
            # Linkagem das folhas
            new_node.next_leaf = node_to_split.next_leaf
            node_to_split.next_leaf = new_node
        else:
            # Se interno, move filhos
            new_node.children = node_to_split.children[mid_point + 1:]
            node_to_split.children = node_to_split.children[:mid_point + 1]

    def range_search(self, start_key: float, end_key: float) -> List[Any]:
        """
        Busca todos os valores cujas chaves estão entre start e end.
        """
        results = []
        
        # 1. Desce até a folha correta
        current = self.root
        while not current.is_leaf:
            i = 0
            while i < len(current.keys) and start_key > current.keys[i]:
                i += 1
            current = current.children[i]
            
        # 2. Percorre a lista ligada horizontalmente
        while current:
            for i, key in enumerate(current.keys):
                if key >= start_key:
                    if key <= end_key:
                        results.append(current.children[i])
                    else:
                        # Passou do limite final, pode parar tudo
                        return results
            current = current.next_leaf
            
        return results