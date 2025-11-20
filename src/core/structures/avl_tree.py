class AVLNode:
    """
    Nó interno da Árvore AVL.
    Armazena a chave (ID), o valor (Objeto PowerNode) e a altura.
    """
    def __init__(self, key, value):
        self.key = key          # Geralmente o node_id
        self.value = value      # O objeto PowerNode (do modelo físico)
        self.left = None
        self.right = None
        self.height = 1         # Altura inicial do nó é 1

class AVLTree:
    """
    Implementação da Árvore AVL para a Camada Lógica do EcoGrid+.
    Garante operações de busca e inserção em O(log n).
    """
    def __init__(self):
        self.root = None

    def insert(self, key, value):
        """Insere um novo nó e rebalanceia a árvore automaticamente."""
        self.root = self._insert_recursive(self.root, key, value)

    def search(self, key):
        """Busca um nó pelo ID em O(log n). Retorna o PowerNode ou None."""
        current = self.root
        while current:
            if key == current.key:
                return current.value
            elif key < current.key:
                current = current.left
            else:
                current = current.right
        return None

    def _insert_recursive(self, node, key, value):
        # 1. Inserção normal de BST (Binary Search Tree)
        if not node:
            return AVLNode(key, value)
        
        if key < node.key:
            node.left = self._insert_recursive(node.left, key, value)
        elif key > node.key:
            node.right = self._insert_recursive(node.right, key, value)
        else:
            # Chaves duplicadas não são permitidas, atualizamos o valor
            node.value = value
            return node

        # 2. Atualizar altura do nó ancestral
        node.height = 1 + max(self._get_height(node.left), self._get_height(node.right))

        # 3. Obter o fator de balanceamento para verificar se houve desequilíbrio
        balance = self._get_balance(node)

        # 4. Se o nó estiver desbalanceado, aplicar Rotações

        # Caso 1 - Rotação à Direita (Left-Left Case)
        if balance > 1 and key < node.left.key:
            return self._rotate_right(node)

        # Caso 2 - Rotação à Esquerda (Right-Right Case)
        if balance < -1 and key > node.right.key:
            return self._rotate_left(node)

        # Caso 3 - Rotação Dupla à Direita (Left-Right Case)
        if balance > 1 and key > node.left.key:
            node.left = self._rotate_left(node.left)
            return self._rotate_right(node)

        # Caso 4 - Rotação Dupla à Esquerda (Right-Left Case)
        if balance < -1 and key < node.right.key:
            node.right = self._rotate_right(node.right)
            return self._rotate_left(node)

        return node

    # --- Métodos Auxiliares e Rotações ---

    def _get_height(self, node):
        if not node:
            return 0
        return node.height

    def _get_balance(self, node):
        if not node:
            return 0
        return self._get_height(node.left) - self._get_height(node.right)

    def _rotate_left(self, z):
        """
        Realiza rotação simples à esquerda.
        Usada quando o peso está na direita (Right-Right).
        """
        y = z.right
        T2 = y.left

        # Rotação
        y.left = z
        z.right = T2

        # Atualiza alturas
        z.height = 1 + max(self._get_height(z.left), self._get_height(z.right))
        y.height = 1 + max(self._get_height(y.left), self._get_height(y.right))

        return y

    def _rotate_right(self, z):
        """
        Realiza rotação simples à direita.
        Usada quando o peso está na esquerda (Left-Left).
        """
        y = z.left
        T3 = y.right

        # Rotação
        y.right = z
        z.left = T3

        # Atualiza alturas
        z.height = 1 + max(self._get_height(z.left), self._get_height(z.right))
        y.height = 1 + max(self._get_height(y.left), self._get_height(y.right))

        return y

    def get_all_values(self):
        """Retorna todos os valores (in-order traversal) para debug."""
        values = []
        self._in_order(self.root, values)
        return values

    def _in_order(self, node, values):
        if node:
            self._in_order(node.left, values)
            values.append(node.value)
            self._in_order(node.right, values)