from typing import List, Any

class BPlusNode:
    def __init__(self, is_leaf: bool = False):
        self.is_leaf = is_leaf
        self.keys = []
        self.children = [] 
        self.next_leaf = None 

class BPlusTree:
    """
    Árvore B+ em Memória (Pure Python).
    A persistência será gerenciada externamente para permitir arquivo único.
    """
    def __init__(self, order: int = 4):
        self.root = BPlusNode(is_leaf=True)
        self.order = order

    def insert(self, key: float, value: Any):
        root = self.root
        if len(root.keys) == self.order - 1:
            new_root = BPlusNode(is_leaf=False)
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root
            self._insert_non_full(new_root, key, value)
        else:
            self._insert_non_full(root, key, value)

    def _insert_non_full(self, node: BPlusNode, key: float, value: Any):
        if node.is_leaf:
            pos = 0
            while pos < len(node.keys) and key > node.keys[pos]:
                pos += 1
            node.keys.insert(pos, key)
            node.children.insert(pos, value)
        else:
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
            new_node.keys = node_to_split.keys[mid_point:]
            new_node.children = node_to_split.children[mid_point:] 
            node_to_split.keys = node_to_split.keys[:mid_point]
            node_to_split.children = node_to_split.children[:mid_point]
            promoted_key = new_node.keys[0]
            parent.keys.insert(index, promoted_key)
            parent.children.insert(index + 1, new_node)
            new_node.next_leaf = node_to_split.next_leaf
            node_to_split.next_leaf = new_node
        else:
            promoted_key = node_to_split.keys[mid_point]
            new_node.keys = node_to_split.keys[mid_point + 1:]
            new_node.children = node_to_split.children[mid_point + 1:]
            node_to_split.keys = node_to_split.keys[:mid_point]
            node_to_split.children = node_to_split.children[:mid_point + 1]
            parent.keys.insert(index, promoted_key)
            parent.children.insert(index + 1, new_node)

    def range_search(self, start_key: float, end_key: float) -> List[Any]:
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
                        if i < len(current.children): results.append(current.children[i])
                    else: return results
            current = current.next_leaf
        return results