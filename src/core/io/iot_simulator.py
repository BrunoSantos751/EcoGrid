"""
Simulador de Sensores IoT para coleta de dados.
Conforme especificação: "Os dados do sistema provêm de medições IoT,
sensores de corrente e tensão instalados em cada nó."
"""
import random
import math
from typing import Dict, List
from datetime import datetime
from src.core.models.node import PowerNode, NodeType
from src.core.models.graph import EcoGridGraph

class IoTSensor:
    """
    Simula um sensor IoT instalado em um nó.
    Mede corrente, tensão e potência em tempo real.
    """
    def __init__(self, node: PowerNode):
        self.node = node
        self.node_id = node.id
        self.last_reading_time = datetime.now()
        
        # Parâmetros do sensor (realismo)
        self.measurement_noise = 0.02  # 2% de ruído
        self.sampling_rate = 1.0  # 1 leitura por segundo
    
    def read_voltage(self) -> float:
        """Lê tensão do sensor (com ruído simulado)."""
        base_voltage = self.node.voltage
        noise = random.uniform(-self.measurement_noise, self.measurement_noise)
        return base_voltage * (1 + noise)
    
    def read_current(self) -> float:
        """Lê corrente do sensor (com ruído simulado)."""
        base_current = self.node.current
        noise = random.uniform(-self.measurement_noise, self.measurement_noise)
        return max(0.0, base_current * (1 + noise))
    
    def read_power(self) -> float:
        """Calcula potência: P = V * I"""
        voltage = self.read_voltage()
        current = self.read_current()
        return voltage * current / 1000.0  # Converte para kW

class IoTSensorNetwork:
    """
    Rede de sensores IoT que coleta dados mantendo a hierarquia.
    Respeita a estrutura: SUBESTACAO → TRANSFORMADOR → CONSUMIDOR
    """
    def __init__(self, graph: EcoGridGraph):
        self.graph = graph
        self.sensors: Dict[int, IoTSensor] = {}
        
        # Inicializa sensores para todos os nós ativos
        self._initialize_sensors()
    
    def _initialize_sensors(self):
        """Inicializa sensores IoT para todos os nós da rede."""
        for node_id, node in self.graph.nodes.items():
            if node.active:
                self.sensors[node_id] = IoTSensor(node)
    
    def collect_readings(self, tick: int) -> Dict[int, dict]:
        """
        Coleta leituras de todos os sensores IoT mantendo a hierarquia.
        PROCESSAMENTO: Folhas → Raiz (consumidores primeiro, depois agregam para pais)
        Retorna dicionário: {node_id: {'voltage': V, 'current': I, 'power': P}}
        """
        readings = {}
        
        # CORREÇÃO: Processa de BAIXO para CIMA (folhas → raiz)
        # 1. Processa CONSUMIDORES primeiro (folhas da árvore - geram a demanda real)
        for node_id, node in self.graph.nodes.items():
            if node.active and node.type == NodeType.CONSUMER:
                if node_id not in readings:
                    self._collect_from_node_hierarchical(node_id, readings, tick, process_children_first=False)
        
        # 2. Processa TRANSFORMADORES (agora os filhos consumidores já têm carga)
        for node_id, node in self.graph.nodes.items():
            if node.active and node.type == NodeType.TRANSFORMER:
                if node_id not in readings:
                    self._collect_from_node_hierarchical(node_id, readings, tick, process_children_first=False)
        
        # 3. Processa SUBESTAÇÕES por último (agora todos os filhos têm carga)
        for root_id in self.graph.root_nodes:
            if root_id not in readings:
                self._collect_from_node_hierarchical(root_id, readings, tick, process_children_first=False)
        
        # 4. Nós órfãos (sem pai definido) - processa como consumidores
        for node_id, node in self.graph.nodes.items():
            if node.active and node_id not in readings:
                if node.parent_id is None:
                    self._collect_from_node_hierarchical(node_id, readings, tick, process_children_first=False)
        
        return readings
    
    def _collect_from_node_hierarchical(self, node_id: int, readings: dict, tick: int, process_children_first: bool = False):
        """
        Coleta leituras seguindo a hierarquia.
        
        Args:
            process_children_first: Se True, processa filhos antes (não usado mais, 
                                   pois processamos por tipo de nó na ordem correta)
        """
        if node_id in readings or node_id not in self.sensors:
            return
        
        sensor = self.sensors[node_id]
        node = self.graph.get_node(node_id)
        
        if not node or not node.active:
            return
        
        # Calcula a carga (agora os filhos já foram processados se necessário)
        base_load = self._calculate_base_load(node, tick)
        
        # Aplica variação temporal apenas para CONSUMIDORES (não para infraestrutura)
        if node.type == NodeType.CONSUMER:
            # Para consumidores, aplica variação temporal suave (padrão diário)
            time_variation = self._get_time_variation(tick)
            # Limita a variação para não reduzir demais (mínimo 0.8x, máximo 1.2x)
            time_variation = max(0.8, min(1.2, time_variation))
            simulated_load = base_load * time_variation
        else:
            # Infraestrutura (transformadores/subestações) não tem variação temporal
            # A carga já é calculada como soma dos filhos (já inclui variação dos consumidores)
            simulated_load = base_load
        
        # Lê do sensor IoT (com ruído)
        voltage = sensor.read_voltage()
        current = sensor.read_current()
        
        # CORREÇÃO: Para transformadores e subestações, não sobrescreve a carga
        # se ela foi ajustada pelo balanceador recentemente. A carga deles deve
        # refletir a demanda real dos filhos, mas não deve "voltar" imediatamente
        # após o balanceamento, pois isso cria a ilusão de que a energia está fluindo
        # para cima na hierarquia.
        
        # Para consumidores: atualiza normalmente (eles são a fonte primária de demanda)
        # MAS: respeita cargas manuais (não sobrescreve se foi definida manualmente)
        if node.type == NodeType.CONSUMER:
            # Se a carga foi definida manualmente, NÃO sobrescreve
            if node.manual_load:
                # Mantém a carga manual, apenas atualiza leituras do sensor
                pass
            elif abs(simulated_load - node.current_load) > 0.1:
                node.update_load(simulated_load)
                if voltage > 0:
                    node.current = simulated_load / voltage
        else:
            # Para transformadores/subestações: usa uma média ponderada para suavizar
            # MAS: se há redistribuição ativa (edge.current_flow > 0), usa o valor calculado diretamente
            # para evitar oscilações e garantir que a redistribuição funcione corretamente
            
            # Verifica se há redistribuição ativa (consumidores com edge.current_flow > 0)
            has_active_redistribution = False
            if node.type == NodeType.TRANSFORMER:
                edges = self.graph.get_neighbors(node.id)
                for edge in edges:
                    neighbor_id = edge.target if edge.source == node.id else edge.source
                    neighbor = self.graph.get_node(neighbor_id)
                    if neighbor and neighbor.type == NodeType.CONSUMER:
                        # CRÍTICO: Sempre busca a aresta na direção correta (transformador → consumidor)
                        transformer_to_consumer_edge = self.graph.get_edge_obj(node.id, neighbor_id)
                        if transformer_to_consumer_edge and transformer_to_consumer_edge.current_flow > 0:
                            has_active_redistribution = True
                            break
            
            if abs(simulated_load - node.current_load) > 0.1:
                if has_active_redistribution:
                    # Se há redistribuição ativa, usa o valor calculado diretamente (sem suavização)
                    # Isso garante que a redistribuição funcione corretamente sem oscilações
                    node.update_load(simulated_load)
                    if voltage > 0:
                        node.current = simulated_load / voltage
                else:
                    # Suaviza a atualização: 70% da carga atual + 30% da nova carga calculada
                    # Isso permite que a carga se ajuste gradualmente sem "pular"
                    smoothed_load = node.current_load * 0.7 + simulated_load * 0.3
                    node.update_load(smoothed_load)
                    if voltage > 0:
                        node.current = smoothed_load / voltage
        
        readings[node_id] = {
            'voltage': voltage,
            'current': current,
            'power': sensor.read_power(),
            'timestamp': tick
        }
    
    def _calculate_base_load(self, node: PowerNode, tick: int) -> float:
        """
        Calcula carga base baseada no tipo de nó e hierarquia.
        CORREÇÃO: Agora os filhos já foram processados quando este método é chamado.
        """
        if node.type == NodeType.SUBSTATION:
            # Subestação: soma TODA a carga dos filhos (transformadores)
            children = self.graph.get_children(node.id)
            total_children_load = sum(c.current_load for c in children if c.active)
            # Se não há filhos ou carga, mantém carga mínima (não 50%!)
            # A subestação só deve ter carga se houver demanda real dos filhos
            result = total_children_load if total_children_load > 0 else node.max_capacity * 0.05
            return result
        
        elif node.type == NodeType.TRANSFORMER:
            # Transformador: soma carga dos filhos (consumidores) + perdas no transformador
            # CRÍTICO: Evita duplicação - apenas conta consumidores onde este transformador é o pai hierárquico
            # OU onde edge.current_flow está definido (distribuição proporcional após redistribuição)
            
            # 1. Busca consumidores que são filhos hierárquicos deste transformador
            children = self.graph.get_children(node.id)
            hierarchical_consumers = [c for c in children if c.active and c.type == NodeType.CONSUMER and c.parent_id == node.id]
            
            # 2. Busca consumidores conectados via arestas que têm edge.current_flow definido
            # (estes são consumidores que foram redistribuídos e estão sendo alimentados por múltiplos transformadores)
            edges = self.graph.get_neighbors(node.id)
            redistributed_consumers = []
            processed_consumer_ids = set()  # Para evitar processar o mesmo consumidor duas vezes
            
            # CRÍTICO: Primeiro, marca todos os consumidores hierárquicos como processados
            # para evitar duplicação quando também têm edge.current_flow definido
            for consumer in hierarchical_consumers:
                processed_consumer_ids.add(consumer.id)
            
            for edge in edges:
                neighbor_id = edge.target if edge.source == node.id else edge.source
                neighbor = self.graph.get_node(neighbor_id)
                if neighbor and neighbor.active and neighbor.type == NodeType.CONSUMER:
                    # CRÍTICO: Sempre busca a aresta na direção correta (transformador → consumidor)
                    # O current_flow é definido na aresta transformer→consumer pelo LoadRedistributor
                    transformer_to_consumer_edge = self.graph.get_edge_obj(node.id, neighbor_id)
                    
                    if transformer_to_consumer_edge and transformer_to_consumer_edge.current_flow > 0:
                        # Se edge.current_flow > 0, este consumidor está sendo alimentado por múltiplos transformadores
                        # e este transformador fornece uma parcela específica
                        # CRÍTICO: Se o consumidor não é filho hierárquico deste transformador,
                        # adiciona como redistribuído (independentemente do parent_id apontar para transformador ativo ou inativo)
                        if neighbor.id not in processed_consumer_ids:
                            redistributed_consumers.append((neighbor, transformer_to_consumer_edge))
                            processed_consumer_ids.add(neighbor.id)
            
            total_children_load = 0.0
            
            # Processa consumidores hierárquicos (filhos diretos)
            for consumer in hierarchical_consumers:
                consumer_load_portion = consumer.current_load  # Por padrão, usa carga total
                
                # CRÍTICO: Sempre busca a aresta na direção correta (transformador → consumidor)
                transformer_to_consumer_edge = self.graph.get_edge_obj(node.id, consumer.id)
                
                if transformer_to_consumer_edge:
                    # CRÍTICO: Se edge.current_flow está definido (> 0), usa apenas essa parcela
                    # Isso permite distribuição proporcional entre múltiplos transformadores (após redistribuição)
                    if transformer_to_consumer_edge.current_flow > 0:
                        consumer_load_portion = transformer_to_consumer_edge.current_flow
                    # Se edge.current_flow é 0, este transformador é o pai hierárquico e fornece a carga total
                    # Adiciona a parcela (não a carga total se houver distribuição proporcional)
                    total_children_load += consumer_load_portion
            
            # Processa consumidores redistribuídos (não são filhos hierárquicos, mas têm edge.current_flow definido)
            for consumer, edge in redistributed_consumers:
                consumer_load_portion = edge.current_flow  # Usa a parcela definida
                total_children_load += consumer_load_portion
            
            # Adiciona 5% de perdas no transformador (eficiência ~95%)
            # Se não há filhos com carga, transformador não deve ter carga
            result = total_children_load * 1.05 if total_children_load > 0 else 0.0
            return result
        
        else:  # CONSUMER
            # Consumidor: gera carga baseada em padrão de consumo real
            # Simula padrão diário (ciclo de 24 ticks = 1 dia)
            hour = tick % 24
            if 6 <= hour <= 22:  # Dia (maior consumo) - 6h às 22h
                # Durante o dia: 40% a 80% da capacidade
                base = node.max_capacity * random.uniform(0.4, 0.8)
            else:  # Noite (menor consumo) - 22h às 6h
                # Durante a noite: 10% a 30% da capacidade
                base = node.max_capacity * random.uniform(0.1, 0.3)
            
            return base
    
    def _get_time_variation(self, tick: int) -> float:
        """Simula variação temporal (padrões diários/sazonais)."""
        # Ciclo diário (24 ticks)
        hour = tick % 24
        
        # Padrão senoidal para simular ciclo diário
        # Pico às 14h (meio-dia), mínimo às 3h (madrugada)
        hour_rad = (hour - 3) * (2 * math.pi / 24)
        daily_factor = 0.5 + 0.5 * math.sin(hour_rad + math.pi/2)
        
        # Adiciona ruído aleatório
        noise = random.uniform(0.95, 1.05)
        
        return daily_factor * noise
    
    def add_sensor(self, node_id: int):
        """Adiciona um novo sensor quando um nó é criado."""
        node = self.graph.get_node(node_id)
        if node and node.active:
            self.sensors[node_id] = IoTSensor(node)
    
    def remove_sensor(self, node_id: int):
        """Remove sensor quando um nó é desativado."""
        if node_id in self.sensors:
            del self.sensors[node_id]

