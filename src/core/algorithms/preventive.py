from typing import List, Optional
from datetime import datetime
from src.core.models.graph import EcoGridGraph
from src.core.algorithms.prediction import DemandPredictor
from src.core.simulation.event_queue import GridEvent, EventType, PriorityLevel

class PreventiveMonitor:
    """
    Monitora a rede usando IA para detectar falhas futuras.
    """
    def __init__(self, graph: EcoGridGraph):
        self.graph = graph
        self.predictor = DemandPredictor()
    
    def scan_for_risks(self) -> List[GridEvent]:
        """
        Analisa todos os nós ativos.
        Se a previsão (próximo tick) > Capacidade, gera Alerta Preventivo.
        """
        preventive_events = []
        
        for node in self.graph.nodes.values():
            if not node.active:
                continue
                
            # 1. Obter dados históricos do Buffer Circular (Issue #6)
            history = node.readings_buffer.get_ordered()
            
            # Precisamos de um mínimo de dados para prever
            if len(history) < 3:
                continue
                
            # 2. Treinar o modelo para este nó específico
            self.predictor.fit(history)
            
            # 3. Prever o futuro
            # Passamos o histórico recente para a MLP usar
            predicted_load = self.predictor.predict_value_at(
                x_index=len(history), 
                recent_history=history
            )
            
            # 4. Verificar Risco
            # Margem de segurança: Se previsão atingir 95% da capacidade
            risk_threshold = node.max_capacity * 0.95
            
            if predicted_load > risk_threshold:
                # Perigo detectado! Criar evento
                warning_msg = f"PREVISÃO: Carga vai atingir {predicted_load:.1f} kW (Limite: {node.max_capacity})"
                
                event = GridEvent(
                    priority=PriorityLevel.HIGH, # Alta prioridade, mas menor que CRITICAL real
                    event_type=EventType.OVERLOAD_WARNING,
                    node_id=node.id,
                    timestamp=datetime.now(),
                    payload={'predicted_load': predicted_load, 'msg': warning_msg}
                )
                preventive_events.append(event)
                
        return preventive_events