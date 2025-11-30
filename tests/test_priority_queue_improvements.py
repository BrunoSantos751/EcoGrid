"""
Testes para as melhorias implementadas na fila de prioridade.
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.simulation.event_queue import (
    PriorityEventQueue, GridEvent, EventType, PriorityLevel
)

def test_duplicate_prevention():
    """Testa a prevenção de duplicatas."""
    print("--- Teste: Prevenção de Duplicatas ---")
    pq = PriorityEventQueue()
    
    # Cria dois eventos idênticos (mesmo node_id e event_type)
    evt1 = GridEvent(
        PriorityLevel.HIGH,
        datetime.now(),
        EventType.OVERLOAD_WARNING,
        10,
        "Primeiro"
    )
    
    evt2 = GridEvent(
        PriorityLevel.HIGH,
        datetime.now(),
        EventType.OVERLOAD_WARNING,
        10,  # Mesmo node_id
        "Segundo"  # Payload diferente, mas deve ser removido
    )
    
    pq.push(evt1, check_duplicates=True)
    assert pq.size() == 1, "Deve ter 1 evento após primeira inserção"
    
    pq.push(evt2, check_duplicates=True)
    assert pq.size() == 1, "Deve manter 1 evento (duplicata removida)"
    
    # Verifica que o evento restante é o mais recente
    remaining = pq.pop()
    assert remaining.payload == "Segundo", "Deve manter o evento mais recente"
    
    print("[OK] Prevencao de duplicatas funcionando corretamente")

def test_max_size_limit():
    """Testa o limite de tamanho da fila."""
    print("\n--- Teste: Limite de Tamanho ---")
    pq = PriorityEventQueue(max_size=3)
    
    # Insere eventos LOW até encher
    for i in range(5):
        evt = GridEvent(PriorityLevel.LOW, datetime.now(), EventType.LOAD_CHANGE, i, f"Evento {i}")
        inserted = pq.push(evt, check_duplicates=False)
        if i < 3:
            assert inserted, f"Evento {i} deveria ser inserido"
        else:
            assert not inserted, f"Evento {i} deveria ser descartado (fila cheia)"
    
    assert pq.size() == 3, "Fila deve ter no máximo 3 eventos"
    
    # Insere evento CRITICAL - deve remover um LOW
    critical = GridEvent(PriorityLevel.CRITICAL, datetime.now(), EventType.NODE_FAILURE, 99, "Crítico")
    inserted = pq.push(critical, check_duplicates=False)
    assert inserted, "Evento crítico deve ser inserido mesmo com fila cheia"
    assert pq.size() == 3, "Fila deve manter tamanho máximo"
    
    # Verifica que o evento crítico está no topo
    top = pq.pop()
    assert top.priority == PriorityLevel.CRITICAL, "Evento crítico deve sair primeiro"
    
    print("[OK] Limite de tamanho funcionando corretamente")

def test_update_priority():
    """Testa a atualização de prioridade de eventos."""
    print("\n--- Teste: Atualização de Prioridade ---")
    pq = PriorityEventQueue()
    
    # Insere evento com prioridade MEDIUM
    evt = GridEvent(
        PriorityLevel.MEDIUM,
        datetime.now(),
        EventType.OVERLOAD_WARNING,
        10,
        "Alerta"
    )
    pq.push(evt, check_duplicates=False)
    
    # Atualiza para CRITICAL
    updated = pq.update_priority(10, EventType.OVERLOAD_WARNING, PriorityLevel.CRITICAL)
    assert updated, "Prioridade deve ser atualizada"
    assert pq.size() == 1, "Deve manter 1 evento"
    
    # Verifica que a prioridade foi atualizada
    top = pq.pop()
    assert top.priority == PriorityLevel.CRITICAL, "Prioridade deve ser CRITICAL"
    assert top.node_id == 10, "Node ID deve ser mantido"
    
    print("[OK] Atualizacao de prioridade funcionando corretamente")

def test_remove_event():
    """Testa a remoção de eventos específicos."""
    print("\n--- Teste: Remoção de Eventos ---")
    pq = PriorityEventQueue()
    
    # Insere vários eventos
    for i in range(5):
        evt = GridEvent(PriorityLevel.MEDIUM, datetime.now(), EventType.LOAD_CHANGE, i, f"Evento {i}")
        pq.push(evt, check_duplicates=False)
    
    assert pq.size() == 5, "Deve ter 5 eventos"
    
    # Remove evento específico
    removed = pq.remove_event(2, EventType.LOAD_CHANGE)
    assert removed, "Evento deve ser removido"
    assert pq.size() == 4, "Deve ter 4 eventos após remoção"
    
    # Tenta remover evento inexistente
    removed = pq.remove_event(99, EventType.NODE_FAILURE)
    assert not removed, "Evento inexistente não deve ser removido"
    assert pq.size() == 4, "Tamanho deve permanecer 4"
    
    print("[OK] Remocao de eventos funcionando corretamente")

def test_clear_old_events():
    """Testa a limpeza de eventos antigos."""
    print("\n--- Teste: Limpeza de Eventos Antigos ---")
    pq = PriorityEventQueue()
    
    # Cria eventos com timestamps diferentes
    now = datetime.now()
    old_time = now - timedelta(seconds=400)  # 400 segundos atrás
    recent_time = now - timedelta(seconds=100)  # 100 segundos atrás
    
    old_evt = GridEvent(PriorityLevel.LOW, old_time, EventType.LOAD_CHANGE, 1, "Antigo")
    recent_evt = GridEvent(PriorityLevel.HIGH, recent_time, EventType.OVERLOAD_WARNING, 2, "Recente")
    
    pq.push(old_evt, check_duplicates=False)
    pq.push(recent_evt, check_duplicates=False)
    
    assert pq.size() == 2, "Deve ter 2 eventos"
    
    # Limpa eventos com mais de 300 segundos
    removed = pq.clear_old_events(max_age_seconds=300.0)
    assert removed == 1, "Deve remover 1 evento antigo"
    assert pq.size() == 1, "Deve ter 1 evento restante"
    
    remaining = pq.pop()
    assert remaining.node_id == 2, "Evento recente deve permanecer"
    
    print("[OK] Limpeza de eventos antigos funcionando corretamente")

def test_statistics():
    """Testa as estatísticas da fila."""
    print("\n--- Teste: Estatísticas ---")
    pq = PriorityEventQueue()
    
    # Insere eventos de diferentes tipos e prioridades
    events = [
        GridEvent(PriorityLevel.CRITICAL, datetime.now(), EventType.NODE_FAILURE, 1, "Crítico 1"),
        GridEvent(PriorityLevel.CRITICAL, datetime.now(), EventType.NODE_FAILURE, 2, "Crítico 2"),
        GridEvent(PriorityLevel.HIGH, datetime.now(), EventType.OVERLOAD_WARNING, 3, "Alto"),
        GridEvent(PriorityLevel.MEDIUM, datetime.now(), EventType.MAINTENANCE, 4, "Médio"),
        GridEvent(PriorityLevel.LOW, datetime.now(), EventType.LOAD_CHANGE, 5, "Baixo"),
    ]
    
    for evt in events:
        pq.push(evt, check_duplicates=False)
    
    stats = pq.get_statistics()
    
    assert stats['total'] == 5, "Total deve ser 5"
    assert stats['by_priority']['CRITICAL'] == 2, "Deve ter 2 eventos CRITICAL"
    assert stats['by_priority']['HIGH'] == 1, "Deve ter 1 evento HIGH"
    assert stats['by_type'][EventType.NODE_FAILURE] == 2, "Deve ter 2 eventos NODE_FAILURE"
    assert stats['oldest_timestamp'] is not None, "Deve ter timestamp mais antigo"
    assert stats['newest_timestamp'] is not None, "Deve ter timestamp mais recente"
    
    print("[OK] Estatisticas funcionando corretamente")
    print(f"  Total: {stats['total']}")
    print(f"  Por prioridade: {stats['by_priority']}")
    print(f"  Por tipo: {stats['by_type']}")

def test_get_events_by_priority():
    """Testa a obtenção de eventos por prioridade."""
    print("\n--- Teste: Eventos por Prioridade ---")
    pq = PriorityEventQueue()
    
    # Insere eventos de diferentes prioridades
    pq.push(GridEvent(PriorityLevel.CRITICAL, datetime.now(), EventType.NODE_FAILURE, 1, "C1"), check_duplicates=False)
    pq.push(GridEvent(PriorityLevel.CRITICAL, datetime.now(), EventType.NODE_FAILURE, 2, "C2"), check_duplicates=False)
    pq.push(GridEvent(PriorityLevel.HIGH, datetime.now(), EventType.OVERLOAD_WARNING, 3, "H1"), check_duplicates=False)
    pq.push(GridEvent(PriorityLevel.LOW, datetime.now(), EventType.LOAD_CHANGE, 4, "L1"), check_duplicates=False)
    
    critical_events = pq.get_events_by_priority(PriorityLevel.CRITICAL)
    assert len(critical_events) == 2, "Deve ter 2 eventos CRITICAL"
    
    high_events = pq.get_events_by_priority(PriorityLevel.HIGH)
    assert len(high_events) == 1, "Deve ter 1 evento HIGH"
    
    print("[OK] Obtencao de eventos por prioridade funcionando corretamente")

def test_get_events_by_node():
    """Testa a obtenção de eventos por nó."""
    print("\n--- Teste: Eventos por Nó ---")
    pq = PriorityEventQueue()
    
    # Insere eventos de diferentes nós
    pq.push(GridEvent(PriorityLevel.MEDIUM, datetime.now(), EventType.LOAD_CHANGE, 10, "Nó 10 - 1"), check_duplicates=False)
    pq.push(GridEvent(PriorityLevel.HIGH, datetime.now(), EventType.OVERLOAD_WARNING, 10, "Nó 10 - 2"), check_duplicates=False)
    pq.push(GridEvent(PriorityLevel.MEDIUM, datetime.now(), EventType.LOAD_CHANGE, 20, "Nó 20"), check_duplicates=False)
    
    node_10_events = pq.get_events_by_node(10)
    assert len(node_10_events) == 2, "Nó 10 deve ter 2 eventos"
    
    node_20_events = pq.get_events_by_node(20)
    assert len(node_20_events) == 1, "Nó 20 deve ter 1 evento"
    
    print("[OK] Obtencao de eventos por no funcionando corretamente")

def test_has_event():
    """Testa a verificação de existência de eventos."""
    print("\n--- Teste: Verificação de Existência ---")
    pq = PriorityEventQueue()
    
    pq.push(GridEvent(PriorityLevel.HIGH, datetime.now(), EventType.OVERLOAD_WARNING, 10, "Teste"), check_duplicates=False)
    
    assert pq.has_event(10, EventType.OVERLOAD_WARNING), "Deve encontrar evento existente"
    assert not pq.has_event(10, EventType.NODE_FAILURE), "Não deve encontrar evento inexistente"
    assert not pq.has_event(99, EventType.OVERLOAD_WARNING), "Não deve encontrar evento de nó diferente"
    
    print("[OK] Verificacao de existencia funcionando corretamente")

def test_clear_by_priority():
    """Testa a limpeza por prioridade."""
    print("\n--- Teste: Limpeza por Prioridade ---")
    pq = PriorityEventQueue()
    
    # Insere eventos de diferentes prioridades
    pq.push(GridEvent(PriorityLevel.CRITICAL, datetime.now(), EventType.NODE_FAILURE, 1, "C1"), check_duplicates=False)
    pq.push(GridEvent(PriorityLevel.LOW, datetime.now(), EventType.LOAD_CHANGE, 2, "L1"), check_duplicates=False)
    pq.push(GridEvent(PriorityLevel.LOW, datetime.now(), EventType.LOAD_CHANGE, 3, "L2"), check_duplicates=False)
    
    assert pq.size() == 3, "Deve ter 3 eventos"
    
    # Remove todos os eventos LOW
    removed = pq.clear_by_priority(PriorityLevel.LOW)
    assert removed == 2, "Deve remover 2 eventos LOW"
    assert pq.size() == 1, "Deve ter 1 evento restante"
    
    remaining = pq.pop()
    assert remaining.priority == PriorityLevel.CRITICAL, "Evento CRITICAL deve permanecer"
    
    print("[OK] Limpeza por prioridade funcionando corretamente")

if __name__ == "__main__":
    print("=" * 60)
    print("TESTES DAS MELHORIAS DA FILA DE PRIORIDADE")
    print("=" * 60)
    
    try:
        test_duplicate_prevention()
        test_max_size_limit()
        test_update_priority()
        test_remove_event()
        test_clear_old_events()
        test_statistics()
        test_get_events_by_priority()
        test_get_events_by_node()
        test_has_event()
        test_clear_by_priority()
        
        print("\n" + "=" * 60)
        print("[OK] TODOS OS TESTES PASSARAM!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n[ERRO] ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n[ERRO] ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()

