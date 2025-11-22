import sys
import os
import time
from datetime import datetime

# Setup de importação
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importamos as novas definições atualizadas na Issue #8
from src.core.simulation.event_queue import FIFOEventQueue, GridEvent, EventType, PriorityLevel

def test_fifo_logic():
    print("--- Iniciando Teste da Fila FIFO (Issue #7 - Atualizado) ---")
    
    queue = FIFOEventQueue()
    
    # 1. Criando Eventos Simulados
    # Como é uma fila FIFO, a prioridade não importa para a ordenação, mas o objeto exige o campo.
    
    # Evento A
    evt1 = GridEvent(
        priority=PriorityLevel.LOW, 
        timestamp=datetime.now(), 
        event_type=EventType.LOAD_CHANGE, 
        node_id=1, 
        payload=500
    )
    time.sleep(0.01) 
    
    # Evento B
    evt2 = GridEvent(
        priority=PriorityLevel.CRITICAL, # Mesmo sendo CRITICAL, na FIFO ele deve respeitar a ordem de chegada
        timestamp=datetime.now(), 
        event_type=EventType.NODE_FAILURE, 
        node_id=2
    )
    time.sleep(0.01)
    
    # Evento C
    evt3 = GridEvent(
        priority=PriorityLevel.LOW, 
        timestamp=datetime.now(), 
        event_type=EventType.LOAD_CHANGE, 
        node_id=1, 
        payload=200
    )
    
    # 2. Enfileirando (A -> B -> C)
    print("Enfileirando eventos na FIFO...")
    queue.enqueue(evt1)
    queue.enqueue(evt2)
    queue.enqueue(evt3)
    
    assert queue.size() == 3, "Erro no tamanho da fila"
    
    # 3. Processando (Desenfileirando)
    # A FIFO deve ignorar a prioridade "CRITICAL" do evt2 e processá-lo apenas DEPOIS do evt1
    
    print("Processando fila...")
    
    # Primeiro deve ser o evt1 (Entrou primeiro)
    processed_1 = queue.dequeue()
    print(f"Processado 1: {processed_1}")
    assert processed_1.node_id == 1 and processed_1.payload == 500, "Quebra de ordem FIFO (1)"
    
    # Segundo deve ser o evt2 (Entrou em segundo)
    processed_2 = queue.dequeue()
    print(f"Processado 2: {processed_2}")
    assert processed_2.event_type == EventType.NODE_FAILURE, "Quebra de ordem FIFO (2)"
    
    # Terceiro deve ser o evt3
    processed_3 = queue.dequeue()
    print(f"Processado 3: {processed_3}")
    assert processed_3.payload == 200, "Quebra de ordem FIFO (3)"
    
    # Fila deve estar vazia
    assert queue.is_empty() is True, "Fila deveria estar vazia"
    
    print(">> SUCESSO: A ordem cronológica foi respeitada (Prioridade ignorada na FIFO).")

if __name__ == "__main__":
    test_fifo_logic()