import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models.graph import EcoGridGraph
from src.core.models.node import NodeType
from src.core.algorithms.preventive import PreventiveMonitor
from src.core.simulation.event_queue import PriorityLevel, EventType

def test_preventive_alert():
    print("--- Iniciando Teste de Monitoramento Preventivo (Issue #15) ---")
    
    # 1. Setup
    graph = EcoGridGraph()
    monitor = PreventiveMonitor(graph)
    
    # Nó com capacidade 100
    node = graph.add_node(1, NodeType.CONSUMER, max_capacity=100.0)
    
    # 2. Simular histórico de subida perigosa
    # O nó está seguro (90), mas a tendência é de alta
    history_data = [75.0, 80.0, 85.0, 90.0, 95.0]
    
    print(f"Injetando histórico de subida: {history_data}")
    for load in history_data:
        node.update_load(load)
        
    # A Regressão Linear vai ver que sobe +5 a cada passo.
    # Próximo passo previsto: 95 + 5 = 100.0
    # 100.0 > 95% de 100.0 -> Deve disparar alerta.
    
    # 3. Executar Scan
    print("Executando Scan de Riscos...")
    events = monitor.scan_for_risks()
    
    # 4. Validação
    if len(events) > 0:
        evt = events[0]
        print(f"Evento Gerado: {evt}")
        
        assert evt.node_id == 1, "ID do nó incorreto"
        assert evt.priority == PriorityLevel.HIGH, "Prioridade deveria ser HIGH"
        assert evt.event_type == EventType.OVERLOAD_WARNING, "Tipo de evento incorreto"
        assert evt.payload['predicted_load'] >= 100.0, "A previsão deveria ser >= 100"
        print(evt.payload['predicted_load'])
        
        print(">> SUCESSO: O sistema previu a sobrecarga e gerou um alerta preventivo.")
    else:
        print(f"FALHA: Nenhum evento gerado. Previsão falhou. Carga atual: {node.current_load}")
        # Debug manual da previsão
        monitor.predictor.fit(node.readings_buffer.get_ordered())
        pred = monitor.predictor.predict_value_at(len(history_data))
        print(f"Debug: Valor previsto foi {pred}")
        assert False, "Teste falhou na detecção."

if __name__ == "__main__":
    test_preventive_alert()