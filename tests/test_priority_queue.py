import sys
import os
import time
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.simulation.event_queue import PriorityEventQueue, GridEvent, EventType, PriorityLevel

def test_priority_logic():
    print("--- Iniciando Teste do Heap de Prioridade (Issue #8) ---")
    
    pq = PriorityEventQueue()
    
    # 1. Criando Eventos
    # Evento de Rotina (Baixa Prioridade) - Criado PRIMEIRO
    evt_low = GridEvent(PriorityLevel.LOW, datetime.now(), EventType.LOAD_CHANGE, 1, "Rotina")
    
    time.sleep(0.01)
    
    # Evento Crítico (Alta Prioridade) - Criado DEPOIS
    evt_critical = GridEvent(PriorityLevel.CRITICAL, datetime.now(), EventType.NODE_FAILURE, 99, "EXPLOSÃO")
    
    # Evento Médio
    evt_medium = GridEvent(PriorityLevel.MEDIUM, datetime.now(), EventType.MAINTENANCE, 2, "Manutencao")

    # 2. Inserindo na ordem "errada" (Baixo -> Médio -> Crítico)
    print(f"Inserindo: 1.{evt_low} ... 2.{evt_medium} ... 3.{evt_critical}")
    pq.push(evt_low)
    pq.push(evt_medium)
    pq.push(evt_critical)
    
    # 3. Processando (O Heap deve reorganizar a saída)
    print("\nProcessando fila (Output esperado: CRITICAL -> MEDIUM -> LOW)...")
    
    first_out = pq.pop()
    print(f"Saiu 1º: {first_out}")
    
    second_out = pq.pop()
    print(f"Saiu 2º: {second_out}")
    
    third_out = pq.pop()
    print(f"Saiu 3º: {third_out}")
    
    # Validação
    assert first_out.priority == PriorityLevel.CRITICAL, "ERRO: Evento crítico deveria sair primeiro!"
    assert second_out.priority == PriorityLevel.MEDIUM, "ERRO: Evento médio deveria sair em segundo!"
    assert third_out.priority == PriorityLevel.LOW, "ERRO: Evento baixo deveria sair por último!"
    
    print("\n>> SUCESSO: O Heap furou a fila corretamente pela criticidade.")

if __name__ == "__main__":
    test_priority_logic()