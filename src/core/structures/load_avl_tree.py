from typing import List
from src.core.models.node import PowerNode

class LoadAVLNode:
    """Nó da AVL Tree organizado por capacidade disponível."""
    def __init__(self, node: PowerNode):
        self.node = node
        self.key = node.available_capacity
        self.left = None
        self.right = None
        self.height = 1

class LoadAVLTree:
    """
    Árvore AVL para balanceamento de carga energética.
    Organiza nós por capacidade disponível (maior capacidade disponível = mais à direita).
    Quando um nó ultrapassa seu limite, a árvore é rebalanceada usando rotações AVL.
    """
    def __init__(self):
        self.root = None

    def insert(self, node: PowerNode):
        """Insere um nó e rebalanceia a árvore automaticamente."""
        self.root = self._insert_recursive(self.root, node)

    def _insert_recursive(self, avl_node, node: PowerNode):
        """Inserção recursiva com balanceamento automático."""
        if not avl_node:
            return LoadAVLNode(node)
        
        node_key = node.available_capacity
        
        if node_key < avl_node.key:
            avl_node.left = self._insert_recursive(avl_node.left, node)
        elif node_key > avl_node.key:
            avl_node.right = self._insert_recursive(avl_node.right, node)
        else:
            avl_node.node = node
            return avl_node

        avl_node.height = 1 + max(
            self._get_height(avl_node.left),
            self._get_height(avl_node.right)
        )

        balance = self._get_balance(avl_node)

        if balance > 1 and node_key < avl_node.left.key:
            return self._rotate_right(avl_node)

        if balance < -1 and node_key > avl_node.right.key:
            return self._rotate_left(avl_node)

        if balance > 1 and node_key > avl_node.left.key:
            avl_node.left = self._rotate_left(avl_node.left)
            return self._rotate_right(avl_node)

        if balance < -1 and node_key < avl_node.right.key:
            avl_node.right = self._rotate_right(avl_node.right)
            return self._rotate_left(avl_node)

        return avl_node

    def find_node_with_capacity(self, min_capacity: float) -> PowerNode:
        """
        Encontra um nó com pelo menos min_capacity disponível.
        Retorna o nó com maior capacidade disponível que atenda ao requisito.
        """
        return self._find_recursive(self.root, min_capacity)

    def _find_recursive(self, avl_node, min_capacity: float) -> PowerNode:
        """Busca recursiva por capacidade."""
        if not avl_node:
            return None
        
        if avl_node.key >= min_capacity:
            better = self._find_recursive(avl_node.right, min_capacity)
            return better if better else avl_node.node
        
        return self._find_recursive(avl_node.right, min_capacity)
        return self._find_recursive(avl_node.right, min_capacity)

    def get_all_nodes_sorted(self) -> List[PowerNode]:
        """Retorna todos os nós ordenados por capacidade disponível (crescente)."""
        from typing import List
        nodes: List[PowerNode] = []
        self._in_order(self.root, nodes)
        return nodes

    def _in_order(self, avl_node, nodes: List[PowerNode]):
        """Traversal in-order para obter nós ordenados."""
        if avl_node:
            self._in_order(avl_node.left, nodes)
            nodes.append(avl_node.node)
            self._in_order(avl_node.right, nodes)

    def update_node(self, node: PowerNode):
        """Atualiza um nó existente na árvore."""
        self.remove_node(node.id)
        self.insert(node)

    def remove_node(self, node_id: int):
        """Remove um nó da árvore."""
        all_nodes = self.get_all_nodes_sorted()
        self.root = None
        for n in all_nodes:
            if n.id != node_id:
                self.insert(n)

    def _get_height(self, node):
        if not node:
            return 0
        return node.height

    def _get_balance(self, node):
        if not node:
            return 0
        return self._get_height(node.left) - self._get_height(node.right)

    def _rotate_left(self, z):
        """Rotação simples à esquerda."""
        y = z.right
        T2 = y.left

        y.left = z
        z.right = T2

        z.height = 1 + max(self._get_height(z.left), self._get_height(z.right))
        y.height = 1 + max(self._get_height(y.left), self._get_height(y.right))

        return y

    def _rotate_right(self, z):
        """Rotação simples à direita."""
        y = z.left
        T3 = y.right

        y.right = z
        z.left = T3

        z.height = 1 + max(self._get_height(z.left), self._get_height(z.right))
        y.height = 1 + max(self._get_height(y.left), self._get_height(y.right))

        return y

