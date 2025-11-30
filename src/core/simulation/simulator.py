from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import random

from src.core.models.graph import EcoGridGraph
from src.core.models.node import NodeType, PowerNode
from src.core.structures.avl_tree import AVLTree
from src.core.persistence.manager import PersistenceManager
from src.core.simulation.event_queue import PriorityEventQueue, GridEvent, EventType, PriorityLevel
from src.core.algorithms.balancing import LoadBalancer
from src.core.algorithms.heuristics import EnergyHeuristics
from src.core.algorithms.load_redistribution import LoadRedistributor
from src.core.io.iot_simulator import IoTSensorNetwork

class GridSimulator:
    """
    O Maestro do EcoGrid+. 
    Centraliza todas as operações do backend, gerencia o tempo e a persistência.
    """
    def __init__(self):
        self.graph = EcoGridGraph()
        self.avl = AVLTree()
        self.event_queue = PriorityEventQueue()
        self.balancer = LoadBalancer(self.graph, self.avl)
        self.load_redistributor = LoadRedistributor(self.graph, self.avl)
        self.enable_noise = True
        self.iot_network = None
        self.time_tick = 0
        self.logs: List[str] = [] 

    def initialize_default_scenario(self):
        """
        Tenta carregar o estado anterior do disco. 
        Se não existir, cria o cenário padrão do zero.
        """
        self.log("Inicializando simulador...")
        topology_loaded = PersistenceManager.load_topology(self.graph)
        
        if topology_loaded:
            self.log("Topologia da rede carregada do disco.")
            self._sync_avl_from_graph()
        else:
            self.log("Nenhum snapshot encontrado. Criando cenário padrão...")
            self._create_hardcoded_scenario()
            PersistenceManager.save_topology(self.graph)
            self.log("Nova topologia salva no disco.")
        
        self.iot_network = IoTSensorNetwork(self.graph)
        self.log("Rede de sensores IoT inicializada.")

    def _sync_avl_from_graph(self):
        """Reinsere os nós do grafo carregado na árvore AVL para buscas rápidas."""
        self.log("Sincronizando AVL com o Grafo carregado...")
        self.avl = AVLTree()
        count = 0
        for node in self.graph.nodes.values():
            self.avl.insert(int(node.id), node)
            count += 1
        self.log(f"AVL Sincronizada: {count} nós indexados.")
    
    def _get_connected_transformers(self, node_id: int, active_only: bool = True) -> List[Tuple[PowerNode, Any]]:
        """
        Retorna lista de transformadores conectados a um nó.
        
        Args:
            node_id: ID do nó (geralmente um consumidor)
            active_only: Se True, retorna apenas transformadores ativos
            
        Returns:
            Lista de tuplas (transformador, aresta) conectados ao nó
        """
        transformers = []
        edges = self.graph.get_neighbors(node_id)
        
        for edge in edges:
            neighbor_id = edge.target if edge.source == node_id else edge.source
            neighbor = self.graph.get_node(neighbor_id)
            
            if neighbor and neighbor.type == NodeType.TRANSFORMER:
                if not active_only or neighbor.active:
                    transformers.append((neighbor, edge))
        
        return transformers
    
    def _get_transformer_consumer_edge(self, transformer_id: int, consumer_id: int) -> Optional[Any]:
        """
        Retorna a aresta na direção transformador → consumidor.
        O grafo é bidirecional, mas o LoadRedistributor atualiza apenas T→C.
        
        Args:
            transformer_id: ID do transformador
            consumer_id: ID do consumidor
            
        Returns:
            Aresta na direção T→C ou None se não existir
        """
        return self.graph.get_edge_obj(transformer_id, consumer_id)
    
    def _get_consumers_for_transformer(self, transformer_id: int, include_redistributed: bool = True) -> List[PowerNode]:
        """
        Retorna lista de consumidores que estão sendo alimentados por um transformador.
        
        Args:
            transformer_id: ID do transformador
            include_redistributed: Se True, inclui consumidores com redistribuição proporcional
            
        Returns:
            Lista de consumidores alimentados pelo transformador
        """
        consumers = []
        transformer = self.graph.get_node(transformer_id)
        
        if not transformer:
            return consumers
        
        # Busca via hierarquia (filhos diretos)
        children = self.graph.get_children(transformer_id)
        for child in children:
            if child.active and child.type == NodeType.CONSUMER:
                if child not in consumers:
                    consumers.append(child)
        
        # Busca via arestas (redistribuição proporcional)
        if include_redistributed:
            edges = self.graph.get_neighbors(transformer_id)
            for edge in edges:
                neighbor_id = edge.target if edge.source == transformer_id else edge.source
                neighbor = self.graph.get_node(neighbor_id)
                
                if (neighbor and neighbor.active and neighbor.type == NodeType.CONSUMER and
                    neighbor not in consumers):
                    # Verifica se este transformador está realmente alimentando este consumidor
                    transformer_to_consumer_edge = self._get_transformer_consumer_edge(transformer_id, neighbor.id)
                    if transformer_to_consumer_edge:
                        # Se há edge.current_flow > 0 ou se é o parent_id, está alimentando
                        if (transformer_to_consumer_edge.current_flow > 0 or 
                            neighbor.parent_id == transformer_id):
                            consumers.append(neighbor)
        
        return consumers

    def _create_hardcoded_scenario(self):
        """
        Criação manual do cenário mantendo hierarquia explícita.
        Hierarquia: SUBESTACAO → TRANSFORMADOR → CONSUMIDOR
        """
        self.add_node(1, NodeType.SUBSTATION, 10000, 50, 50, efficiency=1.0, parent_id=None)
        self.add_node(10, NodeType.TRANSFORMER, 1000, 150, 100, efficiency=0.95, parent_id=1)
        self.add_node(20, NodeType.TRANSFORMER, 1000, 150, 300, efficiency=0.95, parent_id=1)
        self.add_node(101, NodeType.CONSUMER, 100, 250, 80, efficiency=0.98, parent_id=10)
        self.add_node(102, NodeType.CONSUMER, 150, 280, 120, efficiency=0.98, parent_id=10)
        self.add_node(201, NodeType.CONSUMER, 120, 250, 320, efficiency=0.98, parent_id=20)
        
        self.graph.add_edge(1, 10, 10.0, 0.05, 0.99)
        self.graph.add_edge(1, 20, 12.0, 0.05, 0.99)
        self.graph.add_edge(10, 101, 0.5, 0.2, 0.95)
        self.graph.add_edge(10, 102, 0.8, 0.2, 0.95)
        self.graph.add_edge(20, 201, 0.6, 0.2, 0.95)
        self.graph.add_edge(10, 20, 5.0, 0.1, 0.98)

    def add_node(self, nid, ntype, cap, x, y, efficiency=0.98, parent_id=None):
        """
        Helper para adicionar no Grafo e na AVL ao mesmo tempo.
        Mantém hierarquia: parent_id define o nó pai.
        """
        node = self.graph.add_node(nid, ntype, cap, x, y, efficiency, parent_id)
        self.avl.insert(nid, node)
        if hasattr(self.balancer, 'load_avl'):
            self.balancer.load_avl.insert(node)
        if self.iot_network:
            self.iot_network.add_sensor(nid)
        return node

    def step(self):
        """
        Executa UM passo (tick) da simulação.
        Conforme especificação: dados provêm de sensores IoT.
        """
        self.time_tick += 1
        
        if self.enable_noise:
            redistributed_consumers_old_loads = {}
            for consumer in self.graph.nodes.values():
                if consumer.active and consumer.type == NodeType.CONSUMER:
                    # Verifica se este consumidor tem redistribuição ativa (edge.current_flow > 0)
                    edges = self.graph.get_neighbors(consumer.id)
                    has_redistribution = False
                    for edge in edges:
                        neighbor_id = edge.target if edge.source == consumer.id else edge.source
                        neighbor = self.graph.get_node(neighbor_id)
                        if neighbor and neighbor.type == NodeType.TRANSFORMER:
                            transformer_to_consumer_edge = self.graph.get_edge_obj(neighbor.id, consumer.id)
                            if transformer_to_consumer_edge and transformer_to_consumer_edge.current_flow > 0:
                                has_redistribution = True
                                break
                    
                    if has_redistribution:
                        redistributed_consumers_old_loads[consumer.id] = consumer.current_load
            
            if self.iot_network:
                iot_readings = self.iot_network.collect_readings(self.time_tick)
                # Os dados já foram atualizados nos nós via IoTSensorNetwork
            else:
                # Fallback: tenta reinicializar IoT, se falhar usa simulação corrigida
                try:
                    self.iot_network = IoTSensorNetwork(self.graph)
                    self.log("Rede IoT reinicializada durante simulação.")
                    iot_readings = self.iot_network.collect_readings(self.time_tick)
                except Exception as e:
                    self.log(f"Erro ao inicializar IoT, usando fallback: {e}")
                    self._simulate_random_fluctuations()
            
        self.time_tick += 1
        
        if self.enable_noise:
            redistributed_consumers_old_loads = {}
            for consumer in self.graph.nodes.values():
                if consumer.active and consumer.type == NodeType.CONSUMER:
                    edges = self.graph.get_neighbors(consumer.id)
                    has_redistribution = False
                    for edge in edges:
                        neighbor_id = edge.target if edge.source == consumer.id else edge.source
                        neighbor = self.graph.get_node(neighbor_id)
                        if neighbor and neighbor.type == NodeType.TRANSFORMER:
                            transformer_to_consumer_edge = self.graph.get_edge_obj(neighbor.id, consumer.id)
                            if transformer_to_consumer_edge and transformer_to_consumer_edge.current_flow > 0:
                                has_redistribution = True
                                break
                    
                    if has_redistribution:
                        redistributed_consumers_old_loads[consumer.id] = consumer.current_load
            
            if self.iot_network:
                iot_readings = self.iot_network.collect_readings(self.time_tick)
            else:
                try:
                    self.iot_network = IoTSensorNetwork(self.graph)
                    self.log("Rede IoT reinicializada durante simulação.")
                    iot_readings = self.iot_network.collect_readings(self.time_tick)
                except Exception as e:
                    self.log(f"Erro ao inicializar IoT, usando fallback: {e}")
                    self._simulate_random_fluctuations()
            
            needs_infrastructure_update = False
            for consumer_id, old_load in redistributed_consumers_old_loads.items():
                consumer = self.graph.get_node(consumer_id)
                if consumer and consumer.active and consumer.type == NodeType.CONSUMER:
                    if abs(consumer.current_load - old_load) > 0.1:
                        self._recalculate_proportional_distribution(consumer, old_load)
                        needs_infrastructure_update = True
            
            if needs_infrastructure_update:
                self._update_infrastructure_loads()
        else:
            self._update_infrastructure_loads()
        
        if self.time_tick % 3 == 0:
            if not hasattr(self, '_last_redistribution_tick'):
                self._last_redistribution_tick = -10
            
            cleanup_logs = self.load_redistributor._cleanup_old_redistributions()
            if cleanup_logs:
                for log_msg in cleanup_logs:
                    self.log(log_msg)
                self._update_infrastructure_loads()
            
            if self.time_tick - self._last_redistribution_tick >= 6:
                redistribution_logs = self.load_redistributor.check_and_redistribute(current_tick=self.time_tick)
                
                if redistribution_logs:
                    self._last_redistribution_tick = self.time_tick
                    for log_msg in redistribution_logs:
                        self.log(log_msg)
                    self._update_infrastructure_loads()
        
        if self.time_tick % 3 == 0:
            self._detect_overloads()
            self._check_and_deactivate_critical_nodes()

        if self.time_tick % 50 == 0:
            removed = self.event_queue.clear_old_events(max_age_seconds=300.0)
            if removed > 0:
                self.log(f"Limpeza automática: {removed} eventos antigos removidos da fila")

        processed_count = 0
        events_to_reinsert = []
        
        while not self.event_queue.is_empty() and processed_count < 5:
            event = self.event_queue.pop()
            should_keep = self._handle_event(event)
            if should_keep:
                events_to_reinsert.append(event)
            processed_count += 1
        
        for event in events_to_reinsert:
            self.event_queue.push(event, check_duplicates=False)

        for lines in self.graph.adj_list.values():
            for line in lines:
                source_node = self.graph.nodes.get(line.source)
                target_node = self.graph.nodes.get(line.target)
                
                if (source_node and target_node and
                    ((source_node.type == NodeType.TRANSFORMER and target_node.type == NodeType.CONSUMER) or
                     (source_node.type == NodeType.CONSUMER and target_node.type == NodeType.TRANSFORMER))):
                    if line.current_flow > 0:
                        continue
                elif line.current_flow > 1.0:
                    line.current_flow *= 0.7
                else:
                    line.current_flow = 0.0

        self._update_infrastructure_loads()

    def _update_infrastructure_loads(self):
        """
        Atualiza cargas de transformadores e subestações baseado nos filhos.
        Garante que TODOS os consumidores sejam contados exatamente uma vez.
        """
        self._ensure_all_consumers_have_transformer()
        self._validate_proportional_distributions()
        consumer_to_transformers = self._calculate_consumer_transformer_mapping()
        self._calculate_transformer_loads(consumer_to_transformers)
        self._calculate_substation_loads()
    
    def _calculate_consumer_transformer_mapping(self) -> Dict[int, List[Tuple[int, float, Any]]]:
        """
        Calcula o mapeamento de consumidores para transformadores.
        Determina exatamente qual parcela cada transformador fornece a cada consumidor.
        
        Returns:
            Dict {consumer_id: [(transformer_id, load_portion, edge)]}
        """
        consumer_to_transformers = {}
        
        for consumer in self.graph.nodes.values():
            if not consumer.active or consumer.type != NodeType.CONSUMER:
                continue
            
            consumer_load = consumer.current_load
            if consumer_load <= 0:
                continue
            
            transformers_serving = []  # Lista de (transformer_id, load_portion, edge)
            total_allocated = 0.0
            
            # Busca todos os transformadores conectados a este consumidor
            connected_transformers = self._get_connected_transformers(consumer.id)
            for transformer, edge in connected_transformers:
                transformer_to_consumer_edge = self._get_transformer_consumer_edge(transformer.id, consumer.id)
                
                if transformer_to_consumer_edge:
                    if transformer_to_consumer_edge.current_flow > 0:
                        load_portion = min(transformer_to_consumer_edge.current_flow, consumer_load)
                        transformers_serving.append((transformer.id, load_portion, transformer_to_consumer_edge))
                        total_allocated += load_portion
            
            if total_allocated < consumer_load * 0.99:
                parent_transformer = self.graph.get_node(consumer.parent_id) if consumer.parent_id else None
                
                if parent_transformer and parent_transformer.active:
                    parent_in_list = False
                    parent_index = -1
                    for i, (t_id, _, _) in enumerate(transformers_serving):
                        if t_id == parent_transformer.id:
                            parent_in_list = True
                            parent_index = i
                            break
                    
                    if parent_in_list:
                        _, old_portion, edge = transformers_serving[parent_index]
                        remaining = consumer_load - total_allocated
                        new_portion = old_portion + remaining
                        transformers_serving[parent_index] = (parent_transformer.id, new_portion, edge)
                        total_allocated = consumer_load
                    else:
                        parent_edge = self.graph.get_edge_obj(parent_transformer.id, consumer.id)
                        if parent_edge:
                            remaining = consumer_load - total_allocated
                            transformers_serving.append((parent_transformer.id, remaining, parent_edge))
                            total_allocated = consumer_load
            
            if abs(total_allocated - consumer_load) > 0.1:
                if total_allocated > 0:
                    scale_factor = consumer_load / total_allocated
                    transformers_serving = [(t_id, portion * scale_factor, edge) 
                                           for t_id, portion, edge in transformers_serving]
                else:
                    parent_transformer = self.graph.get_node(consumer.parent_id) if consumer.parent_id else None
                    if parent_transformer and parent_transformer.active:
                        parent_edge = self.graph.get_edge_obj(parent_transformer.id, consumer.id)
                        if parent_edge:
                            transformers_serving = [(parent_transformer.id, consumer_load, parent_edge)]
            
            consumer_to_transformers[consumer.id] = transformers_serving
        
        return consumer_to_transformers
    
    def _calculate_transformer_loads(self, consumer_to_transformers: Dict[int, List[Tuple[int, float, Any]]]):
        """
        Calcula e atualiza as cargas dos transformadores baseado nos consumidores que servem.
        
        Args:
            consumer_to_transformers: Mapeamento de consumidores para transformadores
        """
        for transformer in self.graph.nodes.values():
            if not transformer.active or transformer.type != NodeType.TRANSFORMER:
                continue
            
            total_children_load = 0.0
            cable_losses = 0.0
            
            for consumer_id, transformers_serving in consumer_to_transformers.items():
                consumer = self.graph.get_node(consumer_id)
                if not consumer or not consumer.active:
                    continue
                
                for t_id, load_portion, edge in transformers_serving:
                    if t_id == transformer.id:
                        load_portion = min(load_portion, consumer.current_load)
                        total_children_load += load_portion
                        current_amperes = load_portion / 220.0 if load_portion > 0 else 0.0
                        loss = edge.calculate_power_loss(current_amperes) / 1000.0
                        cable_losses += loss
                        break
            
            transformer_losses = total_children_load * 0.05 if total_children_load > 0 else 0.0
            calculated_load = total_children_load + transformer_losses + cable_losses
            
            old_load = transformer.current_load
            if abs(calculated_load - old_load) > 0.01:
                transformer.update_load(calculated_load)
                if abs(calculated_load - old_load) > 10.0:
                    self.log(f"[INFRA] T{transformer.id} atualizado: {calculated_load:.1f}kW (antes: {old_load:.1f}kW)")
    
    def _calculate_substation_loads(self):
        """
        Calcula e atualiza as cargas das subestações baseado nos transformadores filhos.
        """
        for substation in self.graph.nodes.values():
            if not substation.active or substation.type != NodeType.SUBSTATION:
                continue
            
            children = self.graph.get_children(substation.id)
            transformer_children = [c for c in children if c.active and c.type == NodeType.TRANSFORMER]
            
            seen_ids = set()
            unique_transformers = []
            for transformer in transformer_children:
                if transformer.id not in seen_ids:
                    unique_transformers.append(transformer)
                    seen_ids.add(transformer.id)
            
            total_children_load = sum(t.current_load for t in unique_transformers)
            calculated_load = total_children_load if total_children_load > 0 else substation.max_capacity * 0.05
            
            old_load = substation.current_load
            if abs(calculated_load - old_load) > 0.01:
                substation.update_load(calculated_load)
                if abs(calculated_load - old_load) > 10.0:
                    self.log(f"[INFRA] Sub{substation.id} atualizado: {calculated_load:.1f}kW (antes: {old_load:.1f}kW)")
    
    def _ensure_all_consumers_have_transformer(self):
        """
        Garante que TODOS os consumidores ativos tenham um transformador responsável.
        Se um consumidor não tem parent_id ou o parent_id não é válido, 
        escolhe o melhor transformador baseado em eficiência.
        """
        for consumer in self.graph.nodes.values():
            if not consumer.active or consumer.type != NodeType.CONSUMER:
                continue
            
            # Verifica se o consumidor já tem um transformador válido como parent_id
            has_valid_parent = False
            if consumer.parent_id:
                parent = self.graph.get_node(consumer.parent_id)
                if parent and parent.active and parent.type == NodeType.TRANSFORMER:
                    # Verifica se há conexão física
                    edge = self._get_transformer_consumer_edge(consumer.parent_id, consumer.id)
                    if edge:
                        has_valid_parent = True
            
            # Se não tem parent válido, busca o MELHOR transformador conectado baseado em eficiência
            if not has_valid_parent:
                connected_transformers = self._get_connected_transformers(consumer.id)
                
                if connected_transformers:
                    candidate_transformers = [
                        (transformer, transformer.efficiency * edge.efficiency, edge)
                        for transformer, edge in connected_transformers
                    ]
                    candidate_transformers.sort(key=lambda x: x[1], reverse=True)
                    best_transformer, best_score, _ = candidate_transformers[0]
                    consumer.parent_id = best_transformer.id
                    
                    if len(candidate_transformers) > 1:
                        self.log(
                            f"[OTIMIZAÇÃO] Consumidor {consumer.id} atribuído ao T{best_transformer.id} "
                            f"(eficiência: {best_transformer.efficiency:.3f}, score: {best_score:.3f})"
                        )
    
    def optimize_initial_transformer_assignment(self) -> List[str]:
        """
        Otimiza a atribuição inicial de consumidores aos transformadores baseado em eficiência global.
        Reatribui consumidores para os transformadores que maximizam a eficiência global da rede.
        
        Returns:
            Lista de mensagens sobre as otimizações realizadas
        """
        logs = []
        from src.core.algorithms.heuristics import EnergyHeuristics
        
        current_efficiency = EnergyHeuristics.calculate_global_efficiency(self.graph)
        logs.append(f"[OTIMIZAÇÃO INICIAL] Eficiência global atual: {current_efficiency:.2f}")
        
        optimized_count = 0
        for consumer in self.graph.nodes.values():
            if not consumer.active or consumer.type != NodeType.CONSUMER:
                continue
            
            candidate_transformers = []
            connected_transformers = self._get_connected_transformers(consumer.id)
            
            for transformer, edge in connected_transformers:
                old_parent_id = consumer.parent_id
                consumer.parent_id = transformer.id
                simulated_efficiency = EnergyHeuristics.calculate_global_efficiency(self.graph)
                consumer.parent_id = old_parent_id
                score = (simulated_efficiency / 1000.0) * 0.7 + (transformer.efficiency * edge.efficiency) * 0.3
                candidate_transformers.append((transformer, score, simulated_efficiency, edge))
            
            if not candidate_transformers:
                continue
            
            candidate_transformers.sort(key=lambda x: x[1], reverse=True)
            best_transformer, best_score, best_efficiency, best_edge = candidate_transformers[0]
            
            if consumer.parent_id != best_transformer.id:
                old_parent_id = consumer.parent_id
                consumer.parent_id = best_transformer.id
                optimized_count += 1
                
                logs.append(
                    f"  Consumidor {consumer.id}: T{old_parent_id} → T{best_transformer.id} "
                    f"(eficiência: {best_transformer.efficiency:.3f}, "
                    f"ef. global: {best_efficiency:.2f})"
                )
        
        new_efficiency = EnergyHeuristics.calculate_global_efficiency(self.graph)
        improvement = new_efficiency - current_efficiency
        
        logs.append(
            f"[OTIMIZAÇÃO INICIAL] {optimized_count} consumidor(es) otimizado(s). "
            f"Eficiência global: {current_efficiency:.2f} → {new_efficiency:.2f} "
            f"(melhoria: {improvement:+.2f})"
        )
        
        return logs
    
    def _optimize_all_consumers_for_transformer(self, newly_reactivated_transformer_id: int) -> List[str]:
        """
        Otimiza TODOS os consumidores da rede considerando o transformador recém-reativado.
        Isso garante que consumidores que não estavam conectados ao transformador reativado
        também possam ser reatribuídos se isso melhorar a eficiência global.
        
        Args:
            newly_reactivated_transformer_id: ID do transformador que foi reativado
            
        Returns:
            Lista de mensagens sobre as otimizações realizadas
        """
        logs = []
        from src.core.algorithms.heuristics import EnergyHeuristics
        
        newly_reactivated_transformer = self.graph.get_node(newly_reactivated_transformer_id)
        if not newly_reactivated_transformer or not newly_reactivated_transformer.active:
            return logs
        
        # Para cada consumidor ativo na rede, verifica se pode ser melhor atendido pelo transformador reativado
        optimized_count = 0
        for consumer in self.graph.nodes.values():
            if not consumer.active or consumer.type != NodeType.CONSUMER:
                continue
            
            # Verifica se o consumidor está conectado ao transformador reativado
            connected_transformers = self._get_connected_transformers(consumer.id)
            is_connected_to_new_transformer = any(
                t.id == newly_reactivated_transformer_id for t, _ in connected_transformers
            )
            
            if not is_connected_to_new_transformer:
                continue  # Consumidor não está conectado ao transformador reativado
            
            # Busca todos os transformadores conectados e ativos para este consumidor
            candidate_transformers = []
            
            for transformer, edge in connected_transformers:
                # Simula atribuir este consumidor a este transformador
                old_parent_id = consumer.parent_id
                consumer.parent_id = transformer.id
                
                # Calcula eficiência global com esta atribuição
                simulated_efficiency = EnergyHeuristics.calculate_global_efficiency(self.graph)
                
                # Restaura parent_id original
                consumer.parent_id = old_parent_id
                
                # Score considera eficiência global e eficiências individuais
                score = (simulated_efficiency / 1000.0) * 0.7 + (transformer.efficiency * edge.efficiency) * 0.3
                candidate_transformers.append((transformer, score, simulated_efficiency, edge))
            
            if not candidate_transformers:
                continue
            
            # Ordena por score (maior primeiro) - escolhe o melhor transformador
            candidate_transformers.sort(key=lambda x: x[1], reverse=True)
            best_transformer, best_score, best_efficiency, best_edge = candidate_transformers[0]
            
            # Se o melhor transformador é diferente do atual, reatribui
            if consumer.parent_id != best_transformer.id:
                old_parent_id = consumer.parent_id
                consumer.parent_id = best_transformer.id
                optimized_count += 1
                
                logs.append(
                    f"Consumidor {consumer.id}: T{old_parent_id} → T{best_transformer.id} "
                    f"(eficiência: {best_transformer.efficiency:.3f}, "
                    f"ef. global: {best_efficiency:.2f})"
                )
        
        return logs
    
    def _validate_proportional_distributions(self):
        """
        Valida e corrige distribuições proporcionais para evitar duplicação de cargas.
        """
        # Para cada consumidor ativo, verifica se há distribuição proporcional
        for consumer in self.graph.nodes.values():
            if not consumer.active or consumer.type != NodeType.CONSUMER:
                continue
            
            consumer_load = consumer.current_load
            # Busca todos os transformadores conectados a este consumidor
            connected_transformers = self._get_connected_transformers(consumer.id)
            
            if consumer_load <= 0:
                # Zera todos os edge.current_flow para consumidores sem carga
                for transformer, _ in connected_transformers:
                    transformer_to_consumer_edge = self._get_transformer_consumer_edge(transformer.id, consumer.id)
                    if transformer_to_consumer_edge:
                        transformer_to_consumer_edge.current_flow = 0.0
                continue
            transformers_with_flow = []  # Lista de (transformer_id, edge, current_flow)
            total_flow = 0.0
            
            for transformer, _ in connected_transformers:
                # Busca a aresta na direção transformador → consumidor
                transformer_to_consumer_edge = self._get_transformer_consumer_edge(transformer.id, consumer.id)
                
                if transformer_to_consumer_edge and transformer_to_consumer_edge.current_flow > 0:
                    # Limita o current_flow ao máximo da carga do consumidor
                    transformer_to_consumer_edge.current_flow = min(
                        transformer_to_consumer_edge.current_flow, 
                        consumer_load
                    )
                    transformers_with_flow.append((transformer.id, transformer_to_consumer_edge, transformer_to_consumer_edge.current_flow))
                    total_flow += transformer_to_consumer_edge.current_flow
            
            # Se não há redistribuição (edge.current_flow), garante que o parent_id esteja correto
            if not transformers_with_flow:
                # Sem redistribuição, o transformador pai deve fornecer toda a carga
                parent_transformer = self.graph.get_node(consumer.parent_id) if consumer.parent_id else None
                
                if not parent_transformer or not parent_transformer.active:
                    # Se não tem parent válido, busca o primeiro transformador conectado
                    connected_transformers = self._get_connected_transformers(consumer.id)
                    if connected_transformers:
                        consumer.parent_id = connected_transformers[0][0].id
                        break
            else:
                # Há redistribuição proporcional - valida se a soma está correta
                # Tolerância de 1% para erros de ponto flutuante
                tolerance = max(consumer_load * 0.01, 0.1)  # Mínimo de 0.1kW
                if abs(total_flow - consumer_load) > tolerance:
                    # Se a soma está maior que a carga, reduz proporcionalmente
                    if total_flow > consumer_load:
                        scale_factor = consumer_load / total_flow if total_flow > 0 else 0.0
                        for transformer_id, edge, old_flow in transformers_with_flow:
                            new_flow = old_flow * scale_factor
                            edge.current_flow = new_flow
                    
                    # Se a soma está menor que a carga, o transformador pai hierárquico deve fornecer o restante
                    elif total_flow < consumer_load:
                        # Encontra o transformador pai hierárquico
                        parent_transformer = self.graph.get_node(consumer.parent_id) if consumer.parent_id else None
                        
                        if parent_transformer and parent_transformer.active:
                            # Verifica se o pai já está na lista de redistribuição
                            parent_in_list = any(t_id == parent_transformer.id for t_id, _, _ in transformers_with_flow)
                            
                            if not parent_in_list:
                                # Ajusta o edge.current_flow do transformador pai para incluir a diferença
                                parent_edge = self.graph.get_edge_obj(parent_transformer.id, consumer.id)
                                if parent_edge:
                                    remaining_load = consumer_load - total_flow
                                    parent_edge.current_flow = remaining_load
                            else:
                                # Pai já está na lista, ajusta proporcionalmente
                                # Encontra a entrada do pai na lista
                                for i, (t_id, edge, flow) in enumerate(transformers_with_flow):
                                    if t_id == parent_transformer.id:
                                        remaining_load = consumer_load - total_flow
                                        edge.current_flow = flow + remaining_load
                                        break
    
    def _simulate_random_fluctuations(self):
        """
        Gera dados para os sensores (FALLBACK - não deve ser usado se IoT estiver ativo).
        CORRIGIDO: Valores mais realistas.
        """
        for node in self.graph.nodes.values():
            if not node.active:
                continue

            if node.type == NodeType.CONSUMER:
                if node.manual_load:
                    continue  # Não sobrescreve carga manual
                
                hour = self.time_tick % 24
                if 6 <= hour <= 22:  # Dia
                    base = node.max_capacity * random.uniform(0.4, 0.8)
                else:  # Noite
                    base = node.max_capacity * random.uniform(0.1, 0.3)
                
                # Aplica pequena variação
                variation = random.uniform(0.95, 1.05)
                new_load = base * variation
                node.update_load(new_load)
        
        # Atualiza infraestrutura após atualizar consumidores
        self._update_infrastructure_loads()

    def _detect_overloads(self):
        """
        Detecta automaticamente sobrecargas em transformadores e subestações.
        Cria eventos na fila de prioridade quando detecta sobrecarga.
        Também remove eventos de nós que não estão mais sobrecarregados.
        """
        events_to_remove = []
        for event in self.event_queue.get_all_events():
            if event.event_type == EventType.OVERLOAD_WARNING:
                node = self.graph.get_node(event.node_id)
                if node and node.type in [NodeType.TRANSFORMER, NodeType.SUBSTATION]:
                    if not node.is_overloaded:
                        events_to_remove.append((event.node_id, event.event_type))
                        self.log(f"[AUTO] Removendo evento: {node.type} {event.node_id} não está mais sobrecarregado (carga: {node.current_load:.1f}/{node.max_capacity:.1f}kW)")
        
        for node_id, event_type in events_to_remove:
            self.event_queue.remove_event(node_id, event_type)
        
        for node in self.graph.nodes.values():
            if not node.active or node.type not in [NodeType.TRANSFORMER, NodeType.SUBSTATION]:
                continue
            
            if node.is_overloaded:
                overload_ratio = node.current_load / node.max_capacity if node.max_capacity > 0 else 1.0
                
                if overload_ratio >= 1.5:
                    priority = PriorityLevel.CRITICAL
                    severity_msg = "CRÍTICA"
                elif overload_ratio >= 1.2:
                    priority = PriorityLevel.HIGH
                    severity_msg = "ALTA"
                elif overload_ratio >= 1.0:
                    priority = PriorityLevel.MEDIUM
                    severity_msg = "MÉDIA"
                else:
                    continue
                
                existing_event = None
                for event in self.event_queue.get_all_events():
                    if event.node_id == node.id and event.event_type == EventType.OVERLOAD_WARNING:
                        existing_event = event
                        break
                
                if existing_event:
                    if existing_event.priority != priority:
                        self.event_queue.update_priority(node.id, EventType.OVERLOAD_WARNING, priority)
                        self.log(f"[AUTO] Prioridade atualizada: {node.type} {node.id} agora {severity_msg} ({overload_ratio*100:.1f}%)")
                else:
                    evt = GridEvent(
                        priority=priority,
                        timestamp=datetime.now(),
                        event_type=EventType.OVERLOAD_WARNING,
                        node_id=node.id,
                        payload={
                            'predicted_load': node.current_load,
                            'msg': f'Sobrecarga Automática em {node.type} ({severity_msg}: {overload_ratio*100:.1f}%)',
                            'overload_ratio': overload_ratio,
                            'node_type': str(node.type)
                        }
                    )
                    inserted = self.event_queue.push(evt, check_duplicates=True)
                    if inserted:
                        self.log(f"[AUTO] Evento {severity_msg} criado: {node.type} {node.id} sobrecarregado ({overload_ratio*100:.1f}%)")

    def _check_and_deactivate_critical_nodes(self):
        """
        Verifica se algum consumidor com consumo anormal está deixando transformadores em estágio crítico (150% de uso)
        e desativa automaticamente APENAS esse consumidor específico para proteger a infraestrutura.
        """
        CRITICAL_THRESHOLD = 1.5  # 150% de uso
        
        # Primeiro, identifica transformadores que estão em ou acima de 150% de uso
        critical_transformers = []
        for transformer in self.graph.nodes.values():
            if not transformer.active or transformer.type != NodeType.TRANSFORMER:
                continue
            
            load_percentage = transformer.load_percentage
            if load_percentage >= CRITICAL_THRESHOLD:
                critical_transformers.append((transformer, load_percentage))
        
        # Se não há transformadores críticos, não precisa fazer nada
        if not critical_transformers:
            return
        
        # Para cada transformador crítico, identifica qual consumidor está causando o problema
        # e desativa APENAS esse consumidor específico
        nodes_to_deactivate = []
        processed_consumers = set()  # Evita processar o mesmo consumidor múltiplas vezes
        
        for transformer, transformer_load_pct in critical_transformers:
            # Busca todos os consumidores que este transformador alimenta usando helper
            consumers_fed_by_transformer = self._get_consumers_for_transformer(transformer.id, include_redistributed=True)
            
            # Identifica o consumidor com maior carga anormal (consumo anormal)
            # Um consumidor tem consumo anormal se sua carga é muito alta em relação à sua capacidade
            # ou se está contribuindo significativamente para a sobrecarga do transformador
            candidate_consumer = None
            max_abnormal_ratio = 0.0
            
            for consumer in consumers_fed_by_transformer:
                if consumer.id in processed_consumers:
                    continue
                
                consumer_load = consumer.current_load
                if consumer_load <= 0:
                    continue
                
                # Calcula a parcela que este consumidor contribui para o transformador
                transformer_to_consumer_edge = self._get_transformer_consumer_edge(transformer.id, consumer.id)
                load_portion = 0.0
                
                if transformer_to_consumer_edge:
                    if transformer_to_consumer_edge.current_flow > 0:
                        load_portion = transformer_to_consumer_edge.current_flow
                    elif consumer.parent_id == transformer.id:
                        load_portion = consumer_load
                
                if load_portion <= 0:
                    continue
                
                current_amperes = load_portion / 220.0 if load_portion > 0 else 0.0
                cable_loss = 0.0
                if transformer_to_consumer_edge:
                    cable_loss = transformer_to_consumer_edge.calculate_power_loss(current_amperes) / 1000.0
                transformer_loss = load_portion * 0.05
                total_impact = load_portion + transformer_loss + cable_loss
                impact_percentage = (total_impact / transformer.max_capacity) * 100 if transformer.max_capacity > 0 else 0.0
                consumer_overload_ratio = consumer_load / consumer.max_capacity if consumer.max_capacity > 0 else 0.0
                abnormal_score = (consumer_overload_ratio * 0.6) + (impact_percentage / 100.0 * 0.4)
                
                if consumer_overload_ratio > 1.0 or impact_percentage > 20.0:
                    if abnormal_score > max_abnormal_ratio:
                        max_abnormal_ratio = abnormal_score
                        candidate_consumer = (consumer, transformer, transformer_load_pct, impact_percentage, consumer_overload_ratio)
            
            # Se encontrou um consumidor anormal, marca para desativação
            if candidate_consumer:
                consumer, transformer, transformer_load_pct, impact_pct, consumer_overload_ratio = candidate_consumer
                if consumer.id not in processed_consumers:
                    nodes_to_deactivate.append((consumer, transformer, transformer_load_pct, impact_pct, consumer_overload_ratio))
                    processed_consumers.add(consumer.id)
                    self.log(
                        f"[PROTEÇÃO CRÍTICA] Consumidor {consumer.id} identificado como anormal: "
                        f"carga {consumer.current_load:.1f}kW ({consumer_overload_ratio*100:.1f}% da capacidade), "
                        f"impacto em T{transformer.id}: {impact_pct:.1f}% "
                        f"(T{transformer.id} está em {transformer_load_pct*100:.1f}% de uso)"
                    )
        
        # Desativa APENAS os consumidores identificados como anormais
        for consumer, transformer, transformer_load_pct, impact_pct, consumer_overload_ratio in nodes_to_deactivate:
            if consumer.active:  # Verifica novamente antes de desativar
                self._deactivate_consumer(consumer)
                self.log(
                    f"[AUTO-DESATIVAÇÃO] Consumidor {consumer.id} desativado automaticamente "
                    f"(carga anormal: {consumer.current_load:.1f}kW, {consumer_overload_ratio*100:.1f}% da capacidade) "
                    f"para proteger T{transformer.id} (estava em {transformer_load_pct*100:.1f}% de uso, "
                    f"impacto deste consumidor: {impact_pct:.1f}%)"
                )
                
                # Cria evento para notificar a desativação automática
                evt = GridEvent(
                    priority=PriorityLevel.CRITICAL,
                    timestamp=datetime.now(),
                    event_type=EventType.NODE_FAILURE,
                    node_id=consumer.id,
                    payload={
                        'node_type': str(consumer.type),
                        'msg': f'Desativação automática: Consumidor {consumer.id} (consumo anormal: {consumer.current_load:.1f}kW) desativado para proteger T{transformer.id} (150% de uso)',
                        'auto_deactivated': True,
                        'protected_transformer_id': transformer.id,
                        'transformer_load_percentage': transformer_load_pct * 100,
                        'consumer_load': consumer.current_load,
                        'consumer_overload_ratio': consumer_overload_ratio * 100,
                        'impact_percentage': impact_pct
                    }
                )
                self.event_queue.push(evt, check_duplicates=True)
        
        # Atualiza cargas da infraestrutura após desativações
        if nodes_to_deactivate:
            self._update_infrastructure_loads()

    def _handle_event(self, event: GridEvent) -> bool:
        """
        Roteador de lógica de eventos.
        
        Returns:
            True se o evento deve ser mantido na fila (problema ainda existe)
            False se o evento pode ser removido (problema resolvido ou evento único)
        """
        self.log(f"Evento: {event}")
        
        if event.event_type == EventType.OVERLOAD_WARNING:
            # IA Detectou risco -> Tentar balancear
            node = self.graph.get_node(event.node_id)
            if node:
                logs = self.balancer.update_node_load(event.node_id, event.payload.get('predicted_load', node.current_load))
                for l in logs: self.log(l)
                
                # Verifica se o problema ainda existe (sobrecarga)
                # Mantém o evento na fila se o nó ainda está sobrecarregado
                if node.is_overloaded:
                    return True  # Mantém na fila - problema ainda existe
                else:
                    self.log(f"Problema resolvido: Nó {event.node_id} não está mais sobrecarregado")
                    return False  # Remove da fila - problema resolvido
            return False
            
        elif event.event_type == EventType.NODE_FAILURE:
            # Falha crítica -> Verifica se o nó ainda está inativo
            node = self.graph.get_node(event.node_id)
            if node:
                # Se o nó já está desativado, apenas loga (já foi processado antes)
                if not node.active:
                    # Mantém o evento na fila enquanto o nó estiver inativo
                    return True  # Mantém na fila - problema ainda existe (nó inativo)
                else:
                    self.log(f"Problema resolvido: Nó {event.node_id} foi reativado")
                    return False  # Remove da fila - problema resolvido (nó reativado)
            return False  # Nó não existe mais - remove evento
            
        elif event.event_type == EventType.MAINTENANCE:
            # Eventos de manutenção são únicos - processa e remove
            return False
            
        else:
            # Outros tipos de eventos são únicos - processa e remove
            return False

    def inject_failure(self, node_id: int):
        """
        Desativa um nó da rede elétrica respeitando a hierarquia.
        """
        node = self.graph.get_node(node_id)
        
        # Se já está morto, não faz nada
        if not node or not node.active:
            return

        node_type = node.type
        
        if node_type == NodeType.CONSUMER:
            self._deactivate_consumer(node)
        elif node_type == NodeType.TRANSFORMER:
            self._deactivate_transformer(node)
        elif node_type == NodeType.SUBSTATION:
            self._deactivate_substation(node)
        else:
            # Tipo desconhecido - apenas desativa
            node.active = False
            node.current_load = 0.0
            self.log(f"ALERTA: Nó {node.id} (tipo desconhecido) desativado.")
        
        # Criar evento CRITICAL na fila para notificar a falha
        evt = GridEvent(
            priority=PriorityLevel.CRITICAL,
            timestamp=datetime.now(),
            event_type=EventType.NODE_FAILURE,
            node_id=node_id,
            payload={'node_type': str(node_type), 'msg': f'Falha crítica no nó {node_id}'}
        )
        inserted = self.event_queue.push(evt, check_duplicates=True)
        if inserted:
            self.log(f"Evento CRITICAL criado: Falha no nó {node_id} (fila tem {self.event_queue.size()} eventos)")
        else:
            self.log(f"ERRO: Evento CRITICAL não foi inserido na fila para nó {node_id}")
        
        # Atualiza cargas da infraestrutura após desativação
        self._update_infrastructure_loads()
    
    def reactivate_node(self, node_id: int):
        """
        Reativa um nó da rede elétrica, limpando redistribuições anteriores.
        """
        node = self.graph.get_node(node_id)
        
        # Se já está ativo, não faz nada
        if not node or node.active:
            return
        
        node_type = node.type
        
        if node_type == NodeType.CONSUMER:
            self._reactivate_consumer(node)
        elif node_type == NodeType.TRANSFORMER:
            self._reactivate_transformer(node)
        elif node_type == NodeType.SUBSTATION:
            self._reactivate_substation(node)
        else:
            # Tipo desconhecido - apenas reativa
            node.active = True
            node.current_load = 0.0
            self.log(f"Nó {node.id} (tipo desconhecido) reativado.")
        
        # Remove evento de falha se existir (nó foi reativado)
        removed = self.event_queue.remove_event(node_id, EventType.NODE_FAILURE)
        if removed:
            self.log(f"Evento CRITICAL removido: Nó {node_id} foi reativado")
        
        # Criar evento MEDIUM na fila para notificar a reativação/manutenção
        evt = GridEvent(
            priority=PriorityLevel.MEDIUM,
            timestamp=datetime.now(),
            event_type=EventType.MAINTENANCE,
            node_id=node_id,
            payload={'node_type': str(node_type), 'msg': f'Nó {node_id} reativado'}
        )
        self.event_queue.push(evt, check_duplicates=True)
        self.log(f"Evento MEDIUM criado: Reativação do nó {node_id}")
        
        # Atualiza cargas da infraestrutura após reativação
        self._update_infrastructure_loads()
    
    def _reactivate_consumer(self, consumer: PowerNode):
        """Reativa um consumidor."""
        consumer.active = True
        # A carga será restaurada pelo IoT ou mantida se for manual
        self.log(f"CONSUMIDOR {consumer.id} reativado.")
    
    def _optimize_consumer_assignment(self, consumer: PowerNode) -> Tuple[PowerNode, bool]:
        """
        Otimiza a atribuição de um consumidor para o melhor transformador disponível.
        
        Args:
            consumer: Consumidor a ser otimizado
            
        Returns:
            Tupla (melhor_transformador, foi_otimizado)
        """
        from src.core.algorithms.heuristics import EnergyHeuristics
        
        connected_transformers = self._get_connected_transformers(consumer.id)
        candidate_transformers = []
        
        for transformer, edge in connected_transformers:
            # Simula atribuir este consumidor a este transformador
            old_parent_id = consumer.parent_id
            old_parent = self.graph.get_node(old_parent_id) if old_parent_id else None
            
            # Salva cargas atuais dos transformadores
            old_neighbor_load = transformer.current_load
            old_parent_load = old_parent.current_load if old_parent and old_parent.active else 0.0
            
            # Simula a atribuição
            consumer.parent_id = transformer.id
            
            # Atualiza temporariamente as cargas dos transformadores
            if old_parent and old_parent.active and old_parent.type == NodeType.TRANSFORMER:
                simulated_old_parent_load = max(0.0, old_parent_load - consumer.current_load * 1.05)
                old_parent.current_load = simulated_old_parent_load
            
            simulated_neighbor_load = old_neighbor_load + consumer.current_load * 1.05
            transformer.current_load = simulated_neighbor_load
            
            # Calcula eficiência global com esta atribuição
            simulated_efficiency = EnergyHeuristics.calculate_global_efficiency(self.graph)
            
            # Restaura estado original
            consumer.parent_id = old_parent_id
            transformer.current_load = old_neighbor_load
            if old_parent and old_parent.active:
                old_parent.current_load = old_parent_load
            
            # Score considera eficiência global e eficiências individuais
            score = (simulated_efficiency / 1000.0) * 0.7 + (transformer.efficiency * edge.efficiency) * 0.3
            candidate_transformers.append((transformer, score, simulated_efficiency, edge))
        
        if not candidate_transformers:
            return None, False
        
        # Ordena por score (maior primeiro) - escolhe o melhor transformador
        candidate_transformers.sort(key=lambda x: x[1], reverse=True)
        best_transformer, best_score, best_efficiency, _ = candidate_transformers[0]
        
        # Atribui ao melhor transformador
        old_parent_id = consumer.parent_id
        consumer.parent_id = best_transformer.id
        
        was_optimized = old_parent_id != best_transformer.id
        if was_optimized:
            self.log(
                f"  Consumidor {consumer.id}: T{old_parent_id} → T{best_transformer.id} "
                f"(eficiência: {best_transformer.efficiency:.3f}, ef. global: {best_efficiency:.2f})"
            )
        
        return best_transformer, was_optimized
    
    def _clear_redistribution_flows(self, consumer_id: int, keep_transformer_id: int):
        """
        Limpa edge.current_flow de todos os transformadores conectados a um consumidor,
        exceto o transformador especificado.
        
        Args:
            consumer_id: ID do consumidor
            keep_transformer_id: ID do transformador que deve manter o fluxo
        """
        connected_transformers = self._get_connected_transformers(consumer_id)
        
        for transformer, _ in connected_transformers:
            if transformer.id != keep_transformer_id and transformer.active:
                transformer_to_consumer_edge = self._get_transformer_consumer_edge(transformer.id, consumer_id)
                if transformer_to_consumer_edge and transformer_to_consumer_edge.current_flow > 0:
                    transformer_to_consumer_edge.current_flow = 0.0
    
    def _reactivate_transformer(self, transformer: PowerNode):
        """
        Reativa um transformador e otimiza atribuição de consumidores baseado em eficiência global.
        """
        from src.core.algorithms.heuristics import EnergyHeuristics
        
        transformer_id = transformer.id
        transformer.active = True
        
        self.log(f"TRANSFORMADOR {transformer_id} reativado. Otimizando atribuição de consumidores...")
        
        # Busca TODOS os consumidores conectados a este transformador usando helper
        all_consumers = self._get_consumers_for_transformer(transformer_id, include_redistributed=True)
        self.log(f"  T{transformer_id}: {len(all_consumers)} consumidor(es) conectado(s) para otimizar")
        
        # considerando TODOS os transformadores ativos, não apenas o reativado
        optimized_count = 0
        
        for consumer in all_consumers:
            # Se o consumidor está inativo, reativa apenas se não há outros transformadores ativos
            if not consumer.active:
                connected_transformers = self._get_connected_transformers(consumer.id)
                has_active_transformer = any(t.active for t, _ in connected_transformers)
                
                if not has_active_transformer:
                    consumer.active = True
                    self.log(f"  Consumidor {consumer.id} reativado (dependia de T{transformer_id}).")
                else:
                    continue  # Há outros transformadores ativos, será otimizado depois
            
            # Otimiza atribuição deste consumidor
            best_transformer, was_optimized = self._optimize_consumer_assignment(consumer)
            if not best_transformer:
                continue  # Não há transformadores disponíveis
            
            if was_optimized:
                optimized_count += 1
            
            # Limpa edge.current_flow de outros transformadores para este consumidor
            self._clear_redistribution_flows(consumer.id, best_transformer.id)
        
        # Calcula carga inicial do transformador reativado baseado nos consumidores atribuídos a ele
        initial_load = 0.0
        for consumer in all_consumers:
            if consumer.active and consumer.parent_id == transformer_id:
                initial_load += consumer.current_load
        
        # Adiciona perdas do transformador (5%)
        initial_load = initial_load * 1.05 if initial_load > 0 else 0.0
        
        # Define a carga inicial do transformador
        transformer.current_load = initial_load
        
        transformer.last_reactivation_tick = self.time_tick
        self.load_redistributor.recently_reactivated.add(transformer_id)
        
        edges = self.graph.get_neighbors(transformer_id)
        for edge in edges:
            edge.current_flow = 0.0
        
        global_optimization_logs = self._optimize_all_consumers_for_transformer(transformer_id)
        global_optimized = len([log for log in global_optimization_logs if "→" in log])
        final_efficiency = EnergyHeuristics.calculate_global_efficiency(self.graph)
        
        total_optimized = optimized_count + global_optimized
        
        self.log(
            f"  T{transformer_id} reativado: {total_optimized} consumidor(es) otimizado(s) "
            f"({optimized_count} diretos + {global_optimized} globais), "
            f"carga inicial: {initial_load:.1f}kW, eficiência global: {final_efficiency:.2f}"
        )
        
        if global_optimization_logs:
            for log_msg in global_optimization_logs:
                self.log(f"    {log_msg}")
    
    def _reactivate_substation(self, substation: PowerNode):
        """
        Reativa uma subestação e restaura transformadores que dependiam dela.
        """
        substation_id = substation.id
        substation.active = True
        substation.current_load = 0.0
        
        self.log(f"SUBESTAÇÃO {substation_id} reativada. Restaurando transformadores...")
        
        children = self.graph.get_children(substation_id)
        transformer_children = [c for c in children if c.type == NodeType.TRANSFORMER]
        
        for transformer in transformer_children:
            if not transformer.active:
                edges = self.graph.get_neighbors(transformer.id)
                has_active_substation = False
                for edge in edges:
                    neighbor_id = edge.target if edge.source == transformer.id else edge.source
                    neighbor = self.graph.get_node(neighbor_id)
                    if neighbor and neighbor.active and neighbor.type == NodeType.SUBSTATION:
                        has_active_substation = True
                        break
                
                if not has_active_substation:
                    transformer.active = True
                    transformer.current_load = 0.0
                    self.log(f"  Transformador {transformer.id} reativado (dependia de Sub{substation_id}).")
                    
                    consumer_children = self.graph.get_children(transformer.id)
                    for consumer in consumer_children:
                        if consumer.type == NodeType.CONSUMER and not consumer.active:
                            consumer.active = True
                            self.log(f"    Consumidor {consumer.id} reativado (dependia de T{transformer.id}).")
            
            if transformer.parent_id != substation_id:
                transformer.parent_id = substation_id
                self.log(f"  Transformador {transformer.id} restaurado para Sub{substation_id}.")
        
        edges = self.graph.get_neighbors(substation_id)
        for edge in edges:
            edge.current_flow = 0.0
    
    def _deactivate_consumer(self, consumer: PowerNode):
        """
        Desativa um consumidor: apenas remove da rede, sem redistribuir carga.
        Também remove eventos de sobrecarga da fila de prioridade.
        """
        consumer_load = consumer.current_load
        consumer.active = False
        consumer.current_load = 0.0
        
        # Remove eventos de sobrecarga da fila de prioridade (nó desativado não pode estar sobrecarregado)
        removed_overload = self.event_queue.remove_event(consumer.id, EventType.OVERLOAD_WARNING)
        if removed_overload:
            self.log(f"Evento de sobrecarga removido: Consumidor {consumer.id} foi desativado")
        
        # Zera fluxos nas arestas conectadas
        edges = self.graph.get_neighbors(consumer.id)
        for edge in edges:
            edge.current_flow = 0.0
        
        self.log(f"CONSUMIDOR {consumer.id} desativado. Carga de {consumer_load:.1f}kW removida da rede.")
    
    def _deactivate_transformer(self, transformer: PowerNode):
        """
        Desativa um transformador: redistribui consumidores para outros transformadores.
        Se não houver alternativas, desativa os consumidores também.
        Também remove eventos de sobrecarga da fila de prioridade.
        """
        transformer_id = transformer.id
        transformer.active = False
        transformer.current_load = 0.0
        
        # Remove eventos de sobrecarga da fila de prioridade (nó desativado não pode estar sobrecarregado)
        removed_overload = self.event_queue.remove_event(transformer_id, EventType.OVERLOAD_WARNING)
        if removed_overload:
            self.log(f"Evento de sobrecarga removido: Transformador {transformer_id} foi desativado")
        
        self.log(f"TRANSFORMADOR {transformer_id} desativado. Redistribuindo consumidores...")
        
        # Encontra todos os consumidores que estavam sendo alimentados por este transformador
        connected_consumers = self._get_consumers_for_transformer(transformer_id, include_redistributed=True)
        
        if not connected_consumers:
            self.log(f"  Nenhum consumidor conectado ao transformador {transformer_id}.")
            return
        
        self.log(f"  Encontrados {len(connected_consumers)} consumidor(es) para redistribuir.")
        
        # Para cada consumidor, tenta encontrar outro transformador
        for consumer in connected_consumers:
            # Encontra transformadores alternativos conectados a este consumidor
            alternative_transformers = self._find_alternative_transformers_for_consumer(
                consumer.id, transformer_id
            )
            
            if alternative_transformers:
                # Redistribui para o primeiro transformador disponível (ou distribui proporcionalmente)
                self._redistribute_consumer_to_transformers(
                    consumer, transformer_id, alternative_transformers
                )
                self.log(f"  Consumidor {consumer.id} redistribuído para outros transformadores.")
            else:
                # Não há transformadores alternativos - desativa o consumidor
                self._deactivate_consumer(consumer)
                self.log(f"  Consumidor {consumer.id} desativado (sem transformadores alternativos).")
        
        # Zera fluxos nas arestas do transformador
        edges = self.graph.get_neighbors(transformer_id)
        for edge in edges:
            edge.current_flow = 0.0
        
        # CRÍTICO: Atualiza cargas da infraestrutura imediatamente após redistribuição
        # Isso garante que transformadores que receberam consumidores redistribuídos tenham suas cargas atualizadas
        self._update_infrastructure_loads()
        self.log(f"  Cargas da infraestrutura atualizadas após redistribuição do Transformador {transformer_id}.")
    
    def _deactivate_substation(self, substation: PowerNode):
        """
        Desativa uma subestação: redistribui para outras subestações conectadas.
        Se não houver alternativas, desativa toda a rede alimentada por ela.
        Também remove eventos de sobrecarga da fila de prioridade.
        """
        substation_id = substation.id
        substation.active = False
        substation.current_load = 0.0
        
        # Remove eventos de sobrecarga da fila de prioridade (nó desativado não pode estar sobrecarregado)
        removed_overload = self.event_queue.remove_event(substation_id, EventType.OVERLOAD_WARNING)
        if removed_overload:
            self.log(f"Evento de sobrecarga removido: Subestação {substation_id} foi desativada")
        
        self.log(f"SUBESTAÇÃO {substation_id} desativada. Verificando alternativas...")
        
        # Encontra outras subestações ativas conectadas à rede
        alternative_substations = self._find_alternative_substations(substation_id)
        
        if alternative_substations:
            # Redistribui transformadores para outras subestações
            self.log(f"  Encontradas {len(alternative_substations)} subestação(ões) alternativa(s).")
            
            # Encontra todos os transformadores que dependem desta subestação
            dependent_transformers = self._get_transformers_fed_by_substation(substation_id)
            
            if dependent_transformers:
                self.log(f"  Redistribuindo {len(dependent_transformers)} transformador(es)...")
                
                for transformer in dependent_transformers:
                    # Tenta reconectar o transformador a outra subestação
                    if self._reconnect_transformer_to_substation(
                        transformer, substation_id, alternative_substations
                    ):
                        self.log(f"  Transformador {transformer.id} reconectado a outra subestação.")
                    else:
                        # Não conseguiu reconectar - desativa o transformador e seus consumidores
                        self.log(f"  Transformador {transformer.id} não pode ser reconectado. Desativando...")
                        self._deactivate_transformer(transformer)
            else:
                self.log(f"  Nenhum transformador conectado a esta subestação.")
        else:
            # Não há outras subestações - desativa toda a rede alimentada por esta subestação
            self.log(f"  Nenhuma subestação alternativa encontrada. Desativando toda a rede alimentada por {substation_id}...")
            
            # Desativa todos os transformadores que dependem desta subestação
            dependent_transformers = self._get_transformers_fed_by_substation(substation_id)
            
            for transformer in dependent_transformers:
                self._deactivate_transformer(transformer)
            
            self.log(f"  BLACKOUT: Toda a rede alimentada por {substation_id} foi desativada.")
        
        # Zera fluxos nas arestas da subestação
        edges = self.graph.get_neighbors(substation_id)
        for edge in edges:
            edge.current_flow = 0.0
    
    def _get_consumers_fed_by_transformer(self, transformer_id: int) -> List[PowerNode]:
        """Retorna lista de consumidores que estavam sendo alimentados por um transformador."""
        consumers = []
        transformer = self.graph.get_node(transformer_id)
        
        if not transformer:
            return consumers
        
        # Busca consumidores conectados via arestas
        edges = self.graph.get_neighbors(transformer_id)
        
        for edge in edges:
            neighbor_id = edge.target if edge.source == transformer_id else edge.source
            neighbor = self.graph.get_node(neighbor_id)
            
            if neighbor and neighbor.type == NodeType.CONSUMER:
                # Verifica se este consumidor estava sendo alimentado por este transformador
                # (seja por hierarquia ou por edge.current_flow > 0)
                if (neighbor.parent_id == transformer_id or 
                    (edge.current_flow > 0 and edge.source == transformer_id)):
                    if neighbor not in consumers:
                        consumers.append(neighbor)
        
        return consumers
    
    def _find_alternative_transformers_for_consumer(
        self, consumer_id: int, exclude_transformer_id: int
    ) -> List[PowerNode]:
        """Encontra transformadores alternativos que podem alimentar um consumidor."""
        alternatives = []
        consumer = self.graph.get_node(consumer_id)
        
        if not consumer:
            return alternatives
        
        # Busca transformadores conectados a este consumidor usando helper
        connected_transformers = self._get_connected_transformers(consumer_id)
        
        for transformer, _ in connected_transformers:
            if transformer.id != exclude_transformer_id:
                # Verifica se o transformador tem capacidade disponível
                if transformer.available_capacity > consumer.current_load * 0.1:  # Pelo menos 10% da carga
                    alternatives.append(transformer)
        
        return alternatives
    
    def _redistribute_consumer_to_transformers(
        self, consumer: PowerNode, old_transformer_id: int, new_transformers: List[PowerNode]
    ):
        """
        Redistribui um consumidor de um transformador para outros transformadores.
        """
        if not new_transformers:
            return
        
        consumer_load = consumer.current_load
        
        # Se há apenas um transformador alternativo, transfere toda a carga
        if len(new_transformers) == 1:
            new_transformer = new_transformers[0]
            
            # Atualiza parent_id do consumidor
            consumer.parent_id = new_transformer.id
            
            # Atualiza edge.current_flow
            old_edge = self.graph.get_edge_obj(old_transformer_id, consumer.id)
            if old_edge:
                old_edge.current_flow = 0.0
            
            new_edge = self.graph.get_edge_obj(new_transformer.id, consumer.id)
            if new_edge:
                new_edge.current_flow = consumer_load
            else:
                self.log(f"    AVISO: Aresta entre T{new_transformer.id} e Cons{consumer.id} não encontrada.")
        else:
            # Múltiplos transformadores - distribui proporcionalmente
            total_capacity = sum(t.available_capacity for t in new_transformers)
            
            if total_capacity <= 0:
                return
            
            # Distribui proporcionalmente
            remaining_load = consumer_load
            for i, new_transformer in enumerate(new_transformers):
                if remaining_load <= 0.1:
                    break
                
                proportion = new_transformer.available_capacity / total_capacity
                transfer_amount = min(remaining_load * proportion, new_transformer.available_capacity)
                
                if transfer_amount < 1.0:  # Mínimo de 1kW
                    continue
                
                # Atualiza edge.current_flow
                new_edge = self.graph.get_edge_obj(new_transformer.id, consumer.id)
                if new_edge:
                    current_flow = new_edge.current_flow if new_edge.current_flow > 0 else 0
                    new_edge.current_flow = current_flow + transfer_amount
                
                remaining_load -= transfer_amount
            
            # Zera o edge do transformador antigo
            old_edge = self.graph.get_edge_obj(old_transformer_id, consumer.id)
            if old_edge:
                old_edge.current_flow = 0.0
            
            # Se o consumidor ainda tem parent_id no transformador antigo, atualiza para o primeiro novo
            if consumer.parent_id == old_transformer_id and new_transformers:
                consumer.parent_id = new_transformers[0].id
    
    def _find_alternative_substations(self, exclude_substation_id: int) -> List[PowerNode]:
        """Encontra outras subestações ativas na rede."""
        alternatives = []
        
        for node in self.graph.nodes.values():
            if (node.active and 
                node.type == NodeType.SUBSTATION and 
                node.id != exclude_substation_id):
                alternatives.append(node)
        
        return alternatives
    
    def _get_transformers_fed_by_substation(self, substation_id: int) -> List[PowerNode]:
        """Retorna lista de transformadores que dependem de uma subestação."""
        transformers = []
        substation = self.graph.get_node(substation_id)
        
        if not substation:
            return transformers
        
        # Busca transformadores conectados via arestas ou hierarquia
        edges = self.graph.get_neighbors(substation_id)
        
        for edge in edges:
            neighbor_id = edge.target if edge.source == substation_id else edge.source
            neighbor = self.graph.get_node(neighbor_id)
            
            if neighbor and neighbor.type == NodeType.TRANSFORMER:
                # Verifica se este transformador depende desta subestação
                if (neighbor.parent_id == substation_id or 
                    (edge.current_flow > 0 and edge.source == substation_id)):
                    if neighbor not in transformers:
                        transformers.append(neighbor)
        
        return transformers
    
    def _reconnect_transformer_to_substation(
        self, transformer: PowerNode, old_substation_id: int, new_substations: List[PowerNode]
    ) -> bool:
        """
        Tenta reconectar um transformador a outra subestação.
        Retorna True se conseguiu reconectar.
        """
        if not new_substations:
            return False
        
        # Procura uma subestação que tenha conexão física com este transformador
        for new_substation in new_substations:
            # Verifica se há aresta entre o transformador e a nova subestação
            edge = self.graph.get_edge_obj(transformer.id, new_substation.id)
            if edge:
                # Reconecta: atualiza parent_id e edge.current_flow
                transformer.parent_id = new_substation.id
                
                # Transfere o fluxo da aresta antiga para a nova
                old_edge = self.graph.get_edge_obj(old_substation_id, transformer.id)
                if old_edge and old_edge.current_flow > 0:
                    edge.current_flow = old_edge.current_flow
                    old_edge.current_flow = 0.0
                else:
                    # Se não havia fluxo definido, usa a carga atual do transformador
                    edge.current_flow = transformer.current_load
                
                return True
        
        # Se não encontrou conexão física direta, não pode reconectar
        return False

    def _recalculate_proportional_distribution(self, consumer: PowerNode, old_load: float):
        """
        Recalcula os valores de edge.current_flow proporcionalmente quando a carga de um
        consumidor muda, mas ele já está sendo alimentado por múltiplos transformadores.
        Mantém a proporção existente entre os transformadores.
        
        Args:
            consumer: O nó consumidor cuja carga mudou
            old_load: A carga anterior do consumidor (antes da mudança)
        """
        if consumer.type != NodeType.CONSUMER:
            return
        
        # Busca transformadores conectados usando helper
        connected_transformers = self._get_connected_transformers(consumer.id)
        transformers_with_flow = []  # Lista de (edge, transformer_id, current_flow)
        total_old_flow = 0.0
        
        for transformer, _ in connected_transformers:
            # Busca a aresta na direção TRANSFORMADOR → CONSUMIDOR
            # porque é essa que tem o current_flow definido pelo LoadRedistributor
            transformer_to_consumer_edge = self._get_transformer_consumer_edge(transformer.id, consumer.id)
            
            if transformer_to_consumer_edge and transformer_to_consumer_edge.current_flow > 0:
                transformers_with_flow.append((transformer_to_consumer_edge, transformer.id, transformer_to_consumer_edge.current_flow))
                total_old_flow += transformer_to_consumer_edge.current_flow
        
        # Se não há distribuição proporcional definida, não precisa recalcular
        if not transformers_with_flow or total_old_flow <= 0:
            return
        
        # Calcula o fator de escala baseado na nova carga vs carga anterior
        new_load = consumer.current_load
        
        # Usa a carga antiga do consumidor como referência para calcular o fator de escala
        # Isso garante que a proporção seja mantida corretamente
        if old_load > 0 and abs(new_load - old_load) > 0.1:
            scale_factor = new_load / old_load
            
            # Atualiza cada edge.current_flow mantendo a proporção
            for edge, transformer_id, old_flow in transformers_with_flow:
                new_flow = old_flow * scale_factor
                edge.current_flow = max(0.0, new_flow)
            
            # Verifica se a soma dos novos fluxos está próxima da nova carga
            new_total_flow = sum(edge.current_flow for edge, _, _ in transformers_with_flow)
            if abs(new_total_flow - new_load) > 10.0:
                self.log(f"[REDIST] AVISO: Soma dos fluxos ({new_total_flow:.1f}kW) difere da carga do consumidor ({new_load:.1f}kW)")

    def inject_manual_load(self, node_id: int, new_load: float):
        """
        Aplica uma carga manualmente via interface.
        Atualiza o estado físico imediatamente, mas deixa a LÓGICA (Balanceamento) para o loop.
        """
        node = self.graph.get_node(node_id)
        if node:
            old_load = node.current_load
            
            # 1. Atualização Física (Visual)
            # O nó vai ficar vermelho na UI imediatamente se passar do limite
            node.update_load(new_load)
            # Marca como carga manual para que o IoT não sobrescreva
            node.manual_load = True
            
            # 2. CRÍTICO: Verifica e recalcula distribuição proporcional se necessário
            # Verifica DEPOIS de atualizar a carga, mas usa old_load para calcular a proporção
            if node.type == NodeType.CONSUMER:
                # Verifica se há distribuição proporcional ativa (transformadores com edge.current_flow > 0)
                connected_transformers = self._get_connected_transformers(node_id)
                transformers_with_flow = []
                
                for transformer, _ in connected_transformers:
                    transformer_to_consumer_edge = self._get_transformer_consumer_edge(transformer.id, node_id)
                    if transformer_to_consumer_edge and transformer_to_consumer_edge.current_flow > 0:
                        transformers_with_flow.append((transformer.id, transformer_to_consumer_edge.current_flow))
                
                # Se há pelo menos um transformador com current_flow > 0, há redistribuição proporcional
                if transformers_with_flow:
                    self._recalculate_proportional_distribution(node, old_load)
                    # Atualiza imediatamente as cargas da infraestrutura para refletir os novos valores
                    self._update_infrastructure_loads()
                    self.log(f"MANUAL: Carga do Nó {node_id} alterada de {old_load:.1f}kW para {new_load:.1f}kW. Redistribuição proporcional recalculada.")
                else:
                    self.log(f"MANUAL: Carga do Nó {node_id} definida para {new_load:.1f}kW. (Aguardando Simulação...)")
            else:
                self.log(f"MANUAL: Carga do Nó {node_id} definida para {new_load:.1f}kW. (Aguardando Simulação...)")
            
            # 3. Agendamento Lógico
            # Cria um evento e põe na fila.
            # O balanceador SÓ vai rodar quando o step() processar esse evento.
            
            # Determina prioridade baseada na severidade da sobrecarga
            overload_ratio = new_load / node.max_capacity if node.max_capacity > 0 else 1.0
            
            if overload_ratio >= 1.5:  # 150% ou mais - CRITICAL
                priority = PriorityLevel.CRITICAL
                severity_msg = "CRÍTICA"
            elif overload_ratio >= 1.2:  # 120% ou mais - HIGH
                priority = PriorityLevel.HIGH
                severity_msg = "ALTA"
            elif overload_ratio >= 1.0:  # 100% ou mais - MEDIUM
                priority = PriorityLevel.MEDIUM
                severity_msg = "MÉDIA"
            else:  # Menos de 100% - LOW
                priority = PriorityLevel.LOW
                severity_msg = "NORMAL"
            
            evt = GridEvent(
                priority=priority,
                timestamp=datetime.now(),
                event_type=EventType.OVERLOAD_WARNING, # Tratamos como um alerta de sobrecarga
                node_id=node_id,
                payload={
                    'predicted_load': new_load, 
                    'msg': f'Sobrecarga Manual ({severity_msg}: {overload_ratio*100:.1f}%)',
                    'overload_ratio': overload_ratio
                }
            )
            # Usa check_duplicates=True para evitar múltiplos alertas do mesmo nó
            inserted = self.event_queue.push(evt, check_duplicates=True)
            if not inserted:
                self.log(f"Evento descartado: fila cheia ou evento duplicado para nó {node_id}")
            else:
                self.log(f"Evento {severity_msg} criado para nó {node_id} (carga: {overload_ratio*100:.1f}% da capacidade, fila tem {self.event_queue.size()} eventos)")

    def save_state_manual(self):
        """Salva tudo forçado (Botão Salvar)."""
        PersistenceManager.save_topology(self.graph)
        self.log("Estado completo salvo manualmente.")
    
    def load_state_manual(self) -> bool:
        """
        Carrega o snapshot completo (topologia) do disco.
        
        Returns:
            bool: True se conseguiu carregar pelo menos a topologia, False caso contrário
        """
        self.log("Carregando snapshot do disco...")
        
        # 1. Limpa o grafo atual antes de carregar
        self.graph.nodes.clear()
        self.graph.adj_list.clear()
        
        # 2. Carrega a topologia
        topology_loaded = PersistenceManager.load_topology(self.graph)
        
        if not topology_loaded:
            self.log("Erro: Não foi possível carregar a topologia. Snapshot pode estar corrompido ou não existir.")
            return False
        
        self.log(f"Topologia carregada: {len(self.graph.nodes)} nós restaurados.")
        
        # 3. Reconstrói o índice AVL (que é volátil/memória)
        self._sync_avl_from_graph()
        
        # 4. Reinicializa a rede IoT com os nós carregados
        self.iot_network = IoTSensorNetwork(self.graph)
        self.log("Rede de sensores IoT reinicializada com nós carregados.")
        
        self.log("Snapshot carregado com sucesso!")
        return True
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas da fila de eventos.
        Útil para monitoramento e diagnóstico.
        """
        return self.event_queue.get_statistics()

    def get_metrics(self) -> Dict[str, float]:
        """Dados para o Dashboard."""
        eff = EnergyHeuristics.calculate_global_efficiency(self.graph)
        total_load = sum(n.current_load for n in self.graph.nodes.values())
        
        # Diagnóstico melhorado: calcula valores hierárquicos e detecta inconsistências
        total_consumer_load = sum(n.current_load for n in self.graph.nodes.values() 
                                  if n.active and n.type == NodeType.CONSUMER)
        total_transformer_load = sum(n.current_load for n in self.graph.nodes.values() 
                                    if n.active and n.type == NodeType.TRANSFORMER)
        total_substation_load = sum(n.current_load for n in self.graph.nodes.values() 
                                   if n.active and n.type == NodeType.SUBSTATION)
        
        # CRÍTICO: Verifica consistência hierárquica
        # Os transformadores DEVEM ter carga >= consumidores (incluem consumidores + 5% perdas transformador + perdas cabos)
        # As subestações DEVEM ter carga >= transformadores (incluem transformadores, sem perdas adicionais)
        has_inconsistency = False
        
        # Verifica se transformadores têm carga menor que consumidores (inconsistência)
        # Considera: consumidores + 5% perdas transformador + perdas cabos (estimado em ~2-5% adicional)
        # Tolerância mínima: 1.05 (consumidores + 5% perdas transformador)
        # Tolerância realista: 1.07-1.10 (incluindo perdas de cabos)
        if total_consumer_load > 0:
            min_transformer_load = total_consumer_load * 1.05  # Mínimo: consumidores + 5% perdas transformador
            if total_transformer_load < min_transformer_load * 0.95:  # Tolerância de 5% para variações
                has_inconsistency = True
        
        # Verifica se subestações têm carga muito menor que transformadores (inconsistência)
        # As subestações devem ter carga igual à soma dos transformadores (sem perdas adicionais)
        # Tolerância: 95% (permite pequenas variações devido a arredondamentos)
        if total_transformer_load > 0:
            min_substation_load = total_transformer_load * 0.95  # Tolerância de 5%
            if total_substation_load < min_substation_load:
                has_inconsistency = True
        
        # Loga diagnóstico apenas se houver inconsistência ou a cada 10 ticks para monitoramento
        if has_inconsistency or self.time_tick % 10 == 0:
            expected_transformer_min = total_consumer_load * 1.05  # Consumidores + 5% perdas
            expected_substation_min = total_transformer_load  # Subestações = soma transformadores
            
            # Calcula razões para entender o problema
            transformer_ratio = total_transformer_load / total_consumer_load if total_consumer_load > 0 else 0
            substation_ratio = total_substation_load / total_transformer_load if total_transformer_load > 0 else 0
            
            status = "[INCONSISTENCIA]" if has_inconsistency else "[DIAGNOSTICO]"
            self.log(f"{status} Cons: {total_consumer_load:.1f}kW | Trans: {total_transformer_load:.1f}kW (esperado: >={expected_transformer_min:.1f}kW, razao: {transformer_ratio:.2f}) | Sub: {total_substation_load:.1f}kW (esperado: >={expected_substation_min:.1f}kW, razao: {substation_ratio:.2f})")
        
        return {
            "efficiency": eff,
            "total_load": total_load,
            "tick": self.time_tick
        }

    def normalize_node(self, node_id: int):
        """
        Normaliza um nó que estava em sobrecarga manual, removendo a flag manual_load
        e ajustando a carga para um valor normal dentro da capacidade máxima.
        """
        node = self.graph.get_node(node_id)
        if not node:
            self.log(f"ERRO: Nó {node_id} não encontrado para normalização.")
            return
        
        if not node.active:
            self.log(f"Nó {node_id} está inativo. Reative-o primeiro antes de normalizar.")
            return
        
        # Guarda a carga antiga e verifica se estava sobrecarregado
        old_load = node.current_load
        was_overloaded = node.is_overloaded
        
        # Remove a flag de carga manual
        was_manual = node.manual_load
        node.manual_load = False
        was_overloaded = node.is_overloaded
        
        # Se estava sobrecarregado, ajusta a carga para um valor normal (dentro da capacidade)
        if was_overloaded:
            # Define carga para 60% da capacidade máxima (valor normal com margem de segurança)
            normal_load = node.max_capacity * 0.6
            node.update_load(normal_load)
            self.log(f"Nó {node_id} normalizado: carga ajustada para {normal_load:.1f}kW (60% da capacidade).")
            
            # Remove eventos de sobrecarga da fila (problema resolvido)
            removed = self.event_queue.remove_event(node_id, EventType.OVERLOAD_WARNING)
            if removed:
                self.log(f"Evento de sobrecarga removido: Nó {node_id} foi normalizado")
        elif was_manual:
            # Se não estava sobrecarregado mas tinha carga manual, apenas remove a flag
            # O IoT vai atualizar a carga normalmente no próximo tick
            self.log(f"Nó {node_id} normalizado: removida flag de carga manual. O IoT agora pode atualizar normalmente.")
            
            # Verifica se há eventos de sobrecarga e remove (pode ter sido criado antes)
            removed = self.event_queue.remove_event(node_id, EventType.OVERLOAD_WARNING)
            if removed:
                self.log(f"Evento de sobrecarga removido: Nó {node_id} foi normalizado")
        
        # Limpa o current_flow de todas as arestas conectadas a este nó
        # Isso remove qualquer indicação visual de fluxo alto ou redistribuição
        # IMPORTANTE: Fazemos isso SEMPRE após normalizar, independente do estado anterior
        edges = self.graph.get_neighbors(node_id)
        cleared_count = 0
        for edge in edges:
            neighbor_id = edge.target if edge.source == node_id else edge.source
            
            # Limpa o current_flow em ambas as direções (grafo não direcionado)
            edge_obj_forward = self.graph.get_edge_obj(node_id, neighbor_id)
            edge_obj_reverse = self.graph.get_edge_obj(neighbor_id, node_id)
            
            if edge_obj_forward and edge_obj_forward.current_flow > 0:
                edge_obj_forward.current_flow = 0.0
                cleared_count += 1
            if edge_obj_reverse and edge_obj_reverse.current_flow > 0:
                edge_obj_reverse.current_flow = 0.0
        
        if cleared_count > 0:
            self.log(f"Nó {node_id}: Limpados {cleared_count} fluxos de arestas conectadas (arestas não ficarão mais azuis).")
        
        # Cria evento de manutenção para notificar a normalização
        evt = GridEvent(
            priority=PriorityLevel.MEDIUM,
            timestamp=datetime.now(),
            event_type=EventType.MAINTENANCE,
            node_id=node_id,
            payload={
                'node_type': str(node.type),
                'msg': f'Nó {node_id} normalizado (carga ajustada para {node.current_load:.1f}kW)',
                'old_load': old_load,
                'new_load': node.current_load
            }
        )
        self.event_queue.push(evt, check_duplicates=True)
        self.log(f"Evento MEDIUM criado: Normalização do nó {node_id}")
        
        # Atualiza a infraestrutura para refletir as mudanças
        self._update_infrastructure_loads()
        
        # Limpa rotas calculadas se houver (para consumidores sobrecarregados)
        # Isso será feito automaticamente quando a carga voltar ao normal

    def log(self, msg: str):
        print(msg)
        self.logs.append(msg)
        # Mantém apenas os últimos 50 logs na memória da UI
        if len(self.logs) > 50:
            self.logs.pop(0)