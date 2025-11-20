import sys
import os
import time

# Setup de importação
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.simulation.event_queue import FIFOEventQueue, GridEvent, EventType

def test_fifo_logic():
    print("--- Iniciando Teste da Fila FIFO (Issue #7) ---")
    
    queue = FIFOEventQueue()
    
    # 1. Criando Eventos Simulados
    # Evento A: Nó 1 aumentou carga
    evt1 = GridEvent(EventType.LOAD_CHANGE, node_id=1, payload=500)
    time.sleep(1) # Pequeno delay para diferenciar timestamps
    
    # Evento B: Nó 2 falhou
    evt2 = GridEvent(EventType.NODE_FAILURE, node_id=2)
    time.sleep(1)
    
    # Evento C: Nó 1 diminuiu carga
    evt3 = GridEvent(EventType.LOAD_CHANGE, node_id=1, payload=200)
    
    # 2. Enfileirando (A -> B -> C)
    print("Enfileirando eventos...")
    queue.enqueue(evt1)
    queue.enqueue(evt2)
    queue.enqueue(evt3)
    
    assert queue.size() == 3, "Erro no tamanho da fila"
    
    # 3. Processando (Desenfileirando)
    print("Processando fila...")
    
    # Primeiro deve ser o evt1
    processed_1 = queue.dequeue()
    print(f"Processado: {processed_1}")
    assert processed_1.type == EventType.LOAD_CHANGE and processed_1.payload == 500, "Quebra de ordem FIFO (1)"
    
    # Segundo deve ser o evt2
    processed_2 = queue.dequeue()
    print(f"Processado: {processed_2}")
    assert processed_2.type == EventType.NODE_FAILURE, "Quebra de ordem FIFO (2)"
    
    # Terceiro deve ser o evt3
    processed_3 = queue.dequeue()
    print(f"Processado: {processed_3}")
    assert processed_3.node_id == 1 and processed_3.payload == 200, "Quebra de ordem FIFO (3)"
    
    # Fila deve estar vazia
    assert queue.is_empty() is True, "Fila deveria estar vazia"
    
    print(">> SUCESSO: A ordem cronológica foi respeitada.")

if __name__ == "__main__":
    test_fifo_logic()