from datetime import datetime
from typing import List, Dict, Any
import random

# --- Imports de Infraestrutura e Dados ---
from src.core.models.graph import EcoGridGraph
from src.core.models.node import NodeType
from src.core.structures.avl_tree import AVLTree
from src.core.persistence.manager import PersistenceManager

# --- Imports de Simulação ---
from src.core.simulation.event_queue import PriorityEventQueue, GridEvent, EventType, PriorityLevel

# --- Imports de Inteligência e Algoritmos ---
from src.core.algorithms.balancing import LoadBalancer
from src.core.algorithms.preventive import PreventiveMonitor
from src.core.algorithms.heuristics import EnergyHeuristics

class GridSimulator:
    """
    O Maestro do EcoGrid+. 
    Centraliza todas as operações do backend, gerencia o tempo e a persistência.
    """
    def __init__(self):
        # 1. Infraestrutura
        self.graph = EcoGridGraph()
        self.avl = AVLTree()
        self.event_queue = PriorityEventQueue()
        
        # 2. Inteligência (Instanciados após carregar o grafo)
        self.balancer = LoadBalancer(self.graph, self.avl)
        self.monitor = PreventiveMonitor(self.graph)
        self.enable_noise = True
        
        # 3. Estado da Simulação
        self.time_tick = 0
        self.logs: List[str] = [] 

    def initialize_default_scenario(self):
        """
        Tenta carregar o estado anterior do disco. 
        Se não existir, cria o cenário padrão do zero.
        """
        self.log("Inicializando simulador...")

        # 1. Tenta carregar a TOPOLOGIA (O Mapa)
        topology_loaded = PersistenceManager.load_topology(self.graph)
        
        if topology_loaded:
            self.log("Topologia da rede carregada do disco.")
            
            # 2. Se tem mapa, tenta carregar o HISTÓRICO (Os Dados)
            PersistenceManager.load_history(self.graph)
            self.log("Histórico de dados restaurado.")
            
            # 3. Reconstrói o índice AVL (que é volátil/memória)
            self._sync_avl_from_graph()
            
        else:
            self.log("Nenhum snapshot encontrado. Criando cenário padrão...")
            self._create_hardcoded_scenario()
            
            # Salva a topologia imediatamente para uso futuro
            PersistenceManager.save_topology(self.graph)
            self.log("Nova topologia salva no disco.")

    def _sync_avl_from_graph(self):
        """Reinsere os nós do grafo carregado na árvore AVL para buscas rápidas."""
        self.log("Sincronizando AVL com o Grafo carregado...")
        self.avl = AVLTree() # Limpa a árvore atual
        count = 0
        for node in self.graph.nodes.values():
            self.avl.insert(int(node.id), node)
            count += 1
        self.log(f"AVL Sincronizada: {count} nós indexados.")

    def _create_hardcoded_scenario(self):
        """Criação manual do cenário (executado apenas na primeira vez)."""
        # Subestação
        self.add_node(1, NodeType.SUBSTATION, 10000, 50, 50, efficiency=1.0)
        
        # Transformadores
        self.add_node(10, NodeType.TRANSFORMER, 1000, 150, 100, efficiency=0.95)
        self.add_node(20, NodeType.TRANSFORMER, 1000, 150, 300, efficiency=0.95)
        
        # Consumidores (Casas/Indústrias)
        self.add_node(101, NodeType.CONSUMER, 100, 250, 80, efficiency=0.98)
        self.add_node(102, NodeType.CONSUMER, 150, 280, 120, efficiency=0.98)
        self.add_node(201, NodeType.CONSUMER, 120, 250, 320, efficiency=0.98)
        
        # Conexões Físicas (Topologia)
        # Sub -> Transf
        self.graph.add_edge(1, 10, 10.0, 0.05, 0.99)
        self.graph.add_edge(1, 20, 12.0, 0.05, 0.99)
        
        # Transf -> Consumidores
        self.graph.add_edge(10, 101, 0.5, 0.2, 0.95)
        self.graph.add_edge(10, 102, 0.8, 0.2, 0.95)
        self.graph.add_edge(20, 201, 0.6, 0.2, 0.95)
        
        # Redundância (Caminho alternativo entre transformadores)
        self.graph.add_edge(10, 20, 5.0, 0.1, 0.98)

    def add_node(self, nid, ntype, cap, x, y, efficiency=0.98):
        """Helper para adicionar no Grafo e na AVL ao mesmo tempo."""
        node = self.graph.add_node(nid, ntype, cap, x, y, efficiency)
        self.avl.insert(nid, node)
        return node

    def step(self):
        """
        Executa UM passo (tick) da simulação.
        """
        self.time_tick += 1
        # self.log(f"--- Tick {self.time_tick} ---") # Comentei para não poluir o log visual
        
        # 1. Simular o Mundo (Cargas variando)
        if self.enable_noise:
            self._simulate_random_fluctuations()
        
        # 2. IA Preventiva (Roda a cada 5 ticks)
        if self.time_tick % 5 == 0:
            warnings = self.monitor.scan_for_risks()
            for w in warnings:
                self.log(f"[IA] {w.payload['msg']}")
                self.event_queue.push(w)

        # 3. Processar Eventos (Até 5 por tick)
        processed_count = 0
        while not self.event_queue.is_empty() and processed_count < 5:
            event = self.event_queue.pop()
            self._handle_event(event)
            processed_count += 1

        for lines in self.graph.adj_list.values():
            for line in lines:
                if line.current_flow > 1.0:
                    line.current_flow *= 0.7 # Reduz 30% a cada tick
                else:
                    line.current_flow = 0.0

        # 4. Persistência Automática (Apenas histórico, a cada 10 ticks)
        #if self.time_tick % 10 == 0:
            #PersistenceManager.save_history(self.graph)

    def _simulate_random_fluctuations(self):
        """Gera dados para os sensores."""
        for node in self.graph.nodes.values():
            if not node.active:
                continue

            if node.type == NodeType.CONSUMER:
                variation = random.uniform(0.95, 1.05)
                new_load = max(0, node.current_load * variation)
                # Kickstart apenas se estiver ativo e zerado
                if new_load == 0 and node.active: 
                    new_load = random.uniform(10, 20)
                node.update_load(new_load)
            
            else:
                # Infraestrutura
                fake_base = 500 if node.type == NodeType.TRANSFORMER else 5000
                # Se carga atual for 0 (mas ativo), usa base. Se tiver carga (recebida de vizinho), varia ela.
                current = node.current_load if node.current_load > 0 else fake_base
                variation = random.uniform(0.99, 1.01)
                node.update_load(current * variation)

    def _handle_event(self, event: GridEvent):
        """Roteador de lógica de eventos."""
        self.log(f"Evento: {event}")
        
        if event.event_type == EventType.OVERLOAD_WARNING:
            # IA Detectou risco -> Tentar balancear
            logs = self.balancer.update_node_load(event.node_id, event.payload['predicted_load'])
            for l in logs: self.log(l)
            
        elif event.event_type == EventType.NODE_FAILURE:
            # Falha crítica -> Desativar nó
            node = self.graph.get_node(event.node_id)
            if node:
                node.active = False
                self.log(f"ALERTA: Nó {node.id} OFF-LINE! Recalculando rotas...")

    def inject_failure(self, node_id: int):
        """
        Simula uma falha manual com Failover.
        CORRIGIDO: Zera a carga do nó morto preventivamente para evitar loops.
        """
        node = self.graph.get_node(node_id)
        
        # Se já está morto, não faz nada (evita double-kill e duplicação de carga)
        if not node or not node.active:
            return

        # 1. Captura a carga ANTES de matar
        orphan_load = node.current_load
        
        # 2. Mata o nó IMEDIATAMENTE
        node.active = False
        node.current_load = 0.0 # Zera para garantir que ninguém leia valor velho
        
        self.log(f"ALERTA CRÍTICO: Nó {node.id} falhou! {orphan_load:.1f}kW buscando caminho...")

        # 3. Redistribuição (Failover)
        neighbors_edges = self.graph.get_neighbors(node_id)
        active_neighbors = []
        
        for edge in neighbors_edges:
            nid = edge.target if edge.source == node_id else edge.source
            neighbor = self.graph.get_node(nid)
            if neighbor and neighbor.active:
                active_neighbors.append(neighbor)
        
        if active_neighbors:
            # Divide a carga entre os sobreviventes
            split_load = orphan_load / len(active_neighbors)
            
            for nb in active_neighbors:
                # Aumenta a carga do vizinho
                nb.update_load(nb.current_load + split_load)
                
                self.log(f" > Vizinho {nb.id} absorveu {split_load:.1f}kW (Novo total: {nb.current_load:.1f})")
                
                # Gera evento de alerta para o vizinho se reequilibrar depois
                evt = GridEvent(
                    priority=PriorityLevel.CRITICAL,
                    timestamp=datetime.now(),
                    event_type=EventType.OVERLOAD_WARNING,
                    node_id=nb.id,
                    payload={'predicted_load': nb.current_load, 'msg': 'Sobrecarga por Falha Vizinha'}
                )
                self.event_queue.push(evt)
        else:
            self.log(f"BLACKOUT LOCAL: Nó {node.id} isolado. Carga perdida.")

    def inject_manual_load(self, node_id: int, new_load: float):
        """
        Aplica uma carga manualmente via interface.
        Atualiza o estado físico imediatamente, mas deixa a LÓGICA (Balanceamento) para o loop.
        """
        node = self.graph.get_node(node_id)
        if node:
            # 1. Atualização Física (Visual)
            # O nó vai ficar vermelho na UI imediatamente se passar do limite
            node.update_load(new_load)
            
            self.log(f"MANUAL: Carga do Nó {node_id} definida para {new_load:.1f}kW. (Aguardando Simulação...)")
            
            # 2. Agendamento Lógico
            # Cria um evento e põe na fila.
            # O balanceador SÓ vai rodar quando o step() processar esse evento.
            evt = GridEvent(
                priority=PriorityLevel.HIGH,
                timestamp=datetime.now(),
                event_type=EventType.OVERLOAD_WARNING, # Tratamos como um alerta de sobrecarga
                node_id=node_id,
                payload={'predicted_load': new_load, 'msg': 'Sobrecarga Manual'}
            )
            self.event_queue.push(evt)

    def save_state_manual(self):
        """Salva tudo forçado (Botão Salvar)."""
        PersistenceManager.save_topology(self.graph)
        PersistenceManager.save_history(self.graph)
        self.log("Estado completo salvo manualmente.")

    def get_metrics(self) -> Dict[str, float]:
        """Dados para o Dashboard."""
        eff = EnergyHeuristics.calculate_global_efficiency(self.graph)
        total_load = sum(n.current_load for n in self.graph.nodes.values())
        return {
            "efficiency": eff,
            "total_load": total_load,
            "tick": self.time_tick
        }

    def log(self, msg: str):
        print(msg)
        self.logs.append(msg)
        # Mantém apenas os últimos 50 logs na memória da UI
        if len(self.logs) > 50:
            self.logs.pop(0)