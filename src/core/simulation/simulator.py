from typing import List, Dict, Any
import random

# Imports de todas as classes necessárias
from src.core.models.graph import EcoGridGraph
from src.core.models.node import NodeType
from src.core.structures.avl_tree import AVLTree
from src.core.simulation.event_queue import PriorityEventQueue, GridEvent, EventType, PriorityLevel
from src.core.algorithms.balancing import LoadBalancer
from src.core.algorithms.preventive import PreventiveMonitor
from src.core.algorithms.heuristics import EnergyHeuristics
from src.core.persistence.manager import PersistenceManager

class GridSimulator:
    """
    O Maestro do EcoGrid+. 
    Centraliza todas as operações do backend e expõe uma API simples para a UI.
    """
    def __init__(self):
        # 1. Infraestrutura
        self.graph = EcoGridGraph()
        self.avl = AVLTree()
        self.event_queue = PriorityEventQueue()
        
        # 2. Inteligência
        self.balancer = LoadBalancer(self.graph, self.avl)
        self.monitor = PreventiveMonitor(self.graph)
        
        # 3. Estado da Simulação
        self.time_tick = 0
        self.is_running = False
        self.logs: List[str] = [] # Para mostrar na UI depois

    def initialize_default_scenario(self):
        """Cria um cenário inicial padrão para não começarmos com a tela vazia."""
        self.log("Inicializando cenário padrão...")
        
        # Criação de Nós (Subestação, Transformadores, Casas)
        # Usando posições (x,y) para o mapa
        s1 = self.add_node(1, NodeType.SUBSTATION, 10000, 50, 50)
        
        t1 = self.add_node(10, NodeType.TRANSFORMER, 1000, 150, 100)
        t2 = self.add_node(20, NodeType.TRANSFORMER, 1000, 150, 300)
        
        c1 = self.add_node(101, NodeType.CONSUMER, 100, 250, 80)
        c2 = self.add_node(102, NodeType.CONSUMER, 150, 280, 120)
        c3 = self.add_node(201, NodeType.CONSUMER, 120, 250, 320)
        
        # Conexões Físicas
        self.graph.add_edge(1, 10, 10.0, 0.05) # Sub -> Transf 1
        self.graph.add_edge(1, 20, 12.0, 0.05) # Sub -> Transf 2
        self.graph.add_edge(10, 101, 0.5, 0.2) # Transf 1 -> Casa 1
        self.graph.add_edge(10, 102, 0.8, 0.2) # Transf 1 -> Casa 2
        self.graph.add_edge(20, 201, 0.6, 0.2) # Transf 2 -> Casa 3
        
        # Redundância (Caminho alternativo entre transformadores)
        self.graph.add_edge(10, 20, 5.0, 0.1) 
        PersistenceManager.load_all(self.graph)

    def add_node(self, nid, ntype, cap, x, y):
        """Helper para adicionar no Grafo e na AVL ao mesmo tempo."""
        node = self.graph.add_node(nid, ntype, cap, x, y)
        self.avl.insert(nid, node)
        return node

    def step(self):
        """
        Executa UM passo da simulação (1 tick).
        Chamado pelo loop da UI (ex: a cada 1 segundo).
        """
        self.time_tick += 1
        self.log(f"--- Tick {self.time_tick} ---")
        
        # 1. Gerar Flutuações Aleatórias de Carga (Simular vida real)
        self._simulate_random_fluctuations()
        
        # 2. IA Preventiva (Issue #15) verifica riscos
        # Roda a cada 5 ticks para não ficar pesado
        if self.time_tick % 5 == 0:
            warnings = self.monitor.scan_for_risks()
            for w in warnings:
                self.log(f"[IA] {w.payload['msg']}")
                self.event_queue.push(w)

        # 3. Processar Eventos da Fila (Issue #8)
        # Processa até 3 eventos por tick para não travar
        processed_count = 0
        while not self.event_queue.is_empty() and processed_count < 3:
            event = self.event_queue.pop()
            self._handle_event(event)
            processed_count += 1
            
        # Salva TUDO em UM arquivo a cada 10 ticks 
        if self.time_tick % 10 == 0:
            PersistenceManager.save_all(self.graph)

    def _simulate_random_fluctuations(self):
        """Altera levemente a carga dos consumidores para gerar histórico."""
        for node in self.graph.nodes.values():
            if node.type == NodeType.CONSUMER and node.active:
                # Variação aleatória +/- 5%
                variation = random.uniform(0.95, 1.05)
                new_load = max(0, node.current_load * variation)
                
                # Se estava zerado, dá um empurrãozinho
                if new_load == 0: new_load = random.uniform(10, 20)
                
                # Atualiza sem gerar log excessivo
                node.update_load(new_load)
                
                # Se sobrecarregar "naturalmente", o LoadBalancer pegará no update

    def _handle_event(self, event: GridEvent):
        """Roteador de eventos: Decide quem resolve o problema."""
        self.log(f"Processando Evento: {event}")
        
        if event.event_type == EventType.OVERLOAD_WARNING:
            # IA avisou! Tentar balancear preventivamente
            node_id = event.node_id
            # Chama o balanceador para tentar aliviar
            logs = self.balancer.update_node_load(node_id, event.payload['predicted_load'])
            for l in logs: self.log(l)
            
        elif event.event_type == EventType.NODE_FAILURE:
            # Nó caiu!
            node = self.graph.get_node(event.node_id)
            if node:
                node.active = False
                self.log(f"ALERTA MÁXIMO: Nó {node.id} OFF-LINE!")
                # Futuro: Recalcular rotas A* para isolar área

    def get_metrics(self) -> Dict[str, float]:
        """Retorna dados para o Dashboard da UI."""
        eff = EnergyHeuristics.calculate_global_efficiency(self.graph)
        total_load = sum(n.current_load for n in self.graph.nodes.values())
        return {
            "efficiency": eff,
            "total_load": total_load,
            "queue_size": self.event_queue.event_queue_len() if hasattr(self.event_queue, 'event_queue_len') else 0 # Ajuste conforme sua impl
        }

    def log(self, msg: str):
        """Centraliza logs para poder enviar para a UI depois."""
        print(msg) # No terminal
        self.logs.append(msg) # Na lista (para a UI ler)

    def inject_failure(self, node_id: int):
        """Método para o botão 'Simular Falha' da UI chamar."""
        event = GridEvent(PriorityLevel.CRITICAL, EventType.NODE_FAILURE, node_id, "Simulação Manual")
        self.event_queue.push(event)