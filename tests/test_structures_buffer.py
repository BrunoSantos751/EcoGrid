import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.structures.circular_buffer import CircularBuffer

def test_circular_buffer_logic():
    print("--- Iniciando Teste do Buffer Circular (Issue #6) ---")
    
    # 1. Criar buffer pequeno para facilitar teste (Capacidade 3)
    buf = CircularBuffer(capacity=3)
    
    # 2. Encher o buffer
    buf.add(10)
    buf.add(20)
    buf.add(30)
    
    print(f"Buffer cheio: {buf.get_ordered()}")
    assert buf.get_ordered() == [10, 20, 30], "Ordem inicial incorreta"
    assert buf.is_full is True
    
    # 3. Sobrescrever (O momento crucial)
    print("Adicionando 40 (deve remover o 10)...")
    buf.add(40)
    
    atual = buf.get_ordered()
    print(f"Estado atual: {atual}")
    
    # Validação: O 10 deve ter sumido, e a ordem deve ser 20, 30, 40
    assert atual == [20, 30, 40], "Falha na rotação do buffer!"
    assert buf.get_latest() == 40, "O último valor inserido está errado"
    
    print(">> SUCESSO: Buffer rotacionou corretamente.")

if __name__ == "__main__":
    test_circular_buffer_logic()