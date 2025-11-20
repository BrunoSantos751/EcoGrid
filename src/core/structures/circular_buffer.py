from typing import List, Optional, Any

class CircularBuffer:
    """
    Estrutura de dados para armazenar séries temporais de leituras de sensores.
    Substitui os dados mais antigos quando a capacidade é atingida.
    """
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("A capacidade do buffer deve ser maior que zero.")
            
        self.capacity = capacity
        self.buffer: List[Optional[Any]] = [None] * capacity
        self.head = 0        # Onde o próximo item será escrito
        self.size = 0        # Quantos itens temos atualmente
        self.is_full = False # Flag para indicar se já demos a volta

    def add(self, item: Any):
        """
        Adiciona uma nova leitura. Se cheio, sobrescreve a mais antiga.
        Complexidade: O(1)
        """
        self.buffer[self.head] = item
        
        # Avança o ponteiro circularmente
        self.head = (self.head + 1) % self.capacity
        
        if not self.is_full:
            self.size += 1
            if self.size == self.capacity:
                self.is_full = True

    def get_latest(self) -> Optional[Any]:
        """Retorna o último item inserido (O(1))."""
        if self.size == 0:
            return None
        # O último inserido está na posição anterior ao head
        last_index = (self.head - 1 + self.capacity) % self.capacity
        return self.buffer[last_index]

    def get_ordered(self) -> List[Any]:
        """
        Retorna todos os itens em ordem cronológica (do mais antigo para o novo).
        Complexidade: O(n) na leitura.
        """
        if self.size == 0:
            return []
            
        if not self.is_full:
            return self.buffer[:self.head]
        
        # Se deu a volta, o mais antigo está em 'head' e vai até o fim,
        # concatenado com o início até 'head'
        return self.buffer[self.head:] + self.buffer[:self.head]

    def __repr__(self):
        return f"CircularBuffer(size={self.size}/{self.capacity}, data={self.get_ordered()})"