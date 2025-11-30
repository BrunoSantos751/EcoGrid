from typing import List, Dict, Tuple, Optional
from src.core.models.graph import EcoGridGraph
from src.core.models.node import PowerNode, NodeType
from src.core.structures.avl_tree import AVLTree
from src.core.algorithms.heuristics import EnergyHeuristics


class LoadRedistributor:
    """
    Responsável pela redistribuição de cargas quando transformadores ficam sobrecarregados.
    Monitora transformadores com uso > 60% e redistribui para outros transformadores.
    """
    
    THRESHOLD_PERCENTAGE = 0.60
    TARGET_PERCENTAGE = 0.50
    MIN_REDISTRIBUTION_AMOUNT = 10.0
    SAFETY_MARGIN_PERCENTAGE = 0.05
    STABILITY_HYSTERESIS = 0.10
    MIN_LOAD_DIFFERENCE = 0.15
    MAX_REDISTRIBUTION_PER_CYCLE_PCT = 0.20
    
    def __init__(self, graph: EcoGridGraph, avl_index: AVLTree):
        self.graph = graph
        self.avl = avl_index
        self.recently_reactivated = set()
    
    def check_and_redistribute(self, current_tick: int = -1) -> List[str]:
        """
        Verifica todos os transformadores e redistribui cargas se necessário.
        Processa transformadores em ordem de sobrecarga (mais sobrecarregado primeiro).
        """
        logs = []
        
        to_remove = set()
        for transformer_id in self.recently_reactivated:
            transformer = self.graph.get_node(transformer_id)
            if not transformer or not transformer.active:
                to_remove.add(transformer_id)
                continue
            
            if current_tick >= 0 and hasattr(transformer, 'last_reactivation_tick'):
                if current_tick - transformer.last_reactivation_tick >= 9:
                    to_remove.add(transformer_id)
                    continue
            
            if transformer.current_load > transformer.max_capacity * 0.05:
                to_remove.add(transformer_id)
        
        self.recently_reactivated -= to_remove
        
        transformers = [
            node for node in self.graph.nodes.values()
            if node.active and node.type == NodeType.TRANSFORMER
        ]
        
        overloaded_transformers = [
            t for t in transformers 
            if t.load_percentage > self.THRESHOLD_PERCENTAGE
        ]
        overloaded_transformers.sort(key=lambda t: t.load_percentage, reverse=True)
        
        max_redistributions_per_cycle = min(3, len(overloaded_transformers))
        
        for transformer in overloaded_transformers[:max_redistributions_per_cycle]:
            load_percentage = transformer.load_percentage
            logs.append(
                f"[REDISTRIBUIÇÃO] Transformador {transformer.id} com {load_percentage*100:.1f}% de uso "
                f"({transformer.current_load:.1f}kW / {transformer.max_capacity:.1f}kW)"
            )
            redistribution_logs = self._redistribute_transformer_load(transformer)
            logs.extend(redistribution_logs)
        
        cleanup_logs = self._cleanup_old_redistributions()
        if cleanup_logs:
            logs.extend(cleanup_logs)
        
        return logs
    
    def _redistribute_transformer_load(self, overloaded_transformer: PowerNode) -> List[str]:
        """
        Redistribui cargas de um transformador sobrecarregado.
        
        Args:
            overloaded_transformer: Transformador com uso > 60%
            
        Returns:
            Lista de mensagens sobre as redistribuições realizadas
        """
        logs = []
        connected_consumers = self._get_connected_consumers(overloaded_transformer.id)
        
        if not connected_consumers:
            logs.append(f"  Nenhum consumidor conectado ao transformador {overloaded_transformer.id}")
            return logs
        
        logs.append(f"  Encontrados {len(connected_consumers)} consumidor(es) conectado(s)")
        
        target_load = overloaded_transformer.max_capacity * self.TARGET_PERCENTAGE
        excess_load = overloaded_transformer.current_load - target_load
        
        if excess_load < self.MIN_REDISTRIBUTION_AMOUNT:
            logs.append(f"  Excesso muito pequeno ({excess_load:.1f}kW) - não redistribui")
            return logs
        
        available_transformers = self._get_available_transformers_for_stability(overloaded_transformer)
        if not available_transformers:
            logs.append(f"  Nenhum transformador disponível com carga significativamente menor - mantendo distribuição atual")
            return logs
        
        logs.append(f"  Excesso a redistribuir: {excess_load:.1f}kW")
        connected_consumers.sort(key=lambda c: c.current_load, reverse=True)
        
        max_redistribution_per_cycle = overloaded_transformer.max_capacity * self.MAX_REDISTRIBUTION_PER_CYCLE_PCT
        remaining_excess = min(excess_load, max_redistribution_per_cycle)
        
        if remaining_excess < self.MIN_REDISTRIBUTION_AMOUNT:
            logs.append(f"  Redistribuição limitada a {max_redistribution_per_cycle:.1f}kW por ciclo para estabilidade")
            return logs
        
        logs.append(f"  Redistribuindo até {remaining_excess:.1f}kW (limitado a {self.MAX_REDISTRIBUTION_PER_CYCLE_PCT*100:.0f}% da capacidade por ciclo)")
        
        for consumer in connected_consumers:
            if remaining_excess <= 0.1:
                break
            
            max_redistributable = min(
                consumer.current_load * 0.5,
                remaining_excess
            )
            
            if max_redistributable < self.MIN_REDISTRIBUTION_AMOUNT:
                continue
            
            alternative_transformers = self._find_alternative_transformers(
                consumer.id, 
                overloaded_transformer.id,
                consumer=consumer,
                source_transformer=overloaded_transformer,
                estimated_transfer_amount=max_redistributable
            )
            
            if not alternative_transformers:
                logs.append(f"  Consumidor {consumer.id} não tem transformadores alternativos")
                continue
            
            if alternative_transformers:
                best_transformer, best_capacity, best_score = alternative_transformers[0]
                logs.append(
                    f"  Melhor transformador para Cons{consumer.id}: T{best_transformer.id} "
                    f"(score: {best_score:.3f}, cap: {best_capacity:.1f}kW)"
                )
            
            redistribution_logs = self._redistribute_consumer_load(
                consumer,
                overloaded_transformer,
                alternative_transformers,
                max_redistributable
            )
            
            logs.extend(redistribution_logs)
            remaining_excess -= max_redistributable
        
        return logs
    
    def _get_connected_consumers(self, transformer_id: int) -> List[PowerNode]:
        """
        Retorna lista de consumidores conectados a um transformador.
        
        Args:
            transformer_id: ID do transformador
            
        Returns:
            Lista de nós consumidores conectados
        """
        consumers = []
        transformer = self.graph.get_node(transformer_id)
        
        if not transformer:
            return consumers
        
        # Busca nas arestas conectadas ao transformador
        edges = self.graph.get_neighbors(transformer_id)
        
        for edge in edges:
            # Determina qual nó é o vizinho
            neighbor_id = edge.target if edge.source == transformer_id else edge.source
            neighbor = self.graph.get_node(neighbor_id)
            
            if neighbor and neighbor.active and neighbor.type == NodeType.CONSUMER:
                if neighbor not in consumers:
                    consumers.append(neighbor)
        
        return consumers
    
    def _get_available_transformers_for_stability(self, source_transformer: PowerNode) -> List[PowerNode]:
        """
        Encontra transformadores disponíveis com carga significativamente menor.
        Usado para verificar estabilidade antes de redistribuir.
        
        Args:
            source_transformer: Transformador sobrecarregado
            
        Returns:
            Lista de transformadores com carga significativamente menor
        """
        available = []
        
        # Busca todos os transformadores ativos
        transformers = [
            node for node in self.graph.nodes.values()
            if node.active and node.type == NodeType.TRANSFORMER
            and node.id != source_transformer.id
            and node.id not in self.recently_reactivated
        ]
        
        for transformer in transformers:
            # Verifica se está abaixo do threshold
            if transformer.load_percentage > self.THRESHOLD_PERCENTAGE:
                continue
            
            # NOVO: Verifica se a diferença de carga é significativa
            load_difference = source_transformer.load_percentage - transformer.load_percentage
            if load_difference >= self.MIN_LOAD_DIFFERENCE:
                available.append(transformer)
        
        return available
    
    def _simulate_redistribution_efficiency(
        self,
        consumer: PowerNode,
        source_transformer: PowerNode,
        target_transformer: PowerNode,
        transfer_amount: float
    ) -> float:
        """
        Simula uma redistribuição e calcula a eficiência global esperada.
        Não altera o estado real do grafo - apenas simula temporariamente.
        """
        original_source_load = source_transformer.current_load
        original_target_load = target_transformer.current_load
        
        simulated_source_load = max(0.0, original_source_load - transfer_amount)
        simulated_target_load = original_target_load + transfer_amount
        source_transformer.current_load = simulated_source_load
        target_transformer.current_load = simulated_target_load
        
        efficiency = EnergyHeuristics.calculate_global_efficiency(self.graph)
        
        source_transformer.current_load = original_source_load
        target_transformer.current_load = original_target_load
        
        return efficiency
    
    def _calculate_transformer_score(
        self,
        transformer: PowerNode,
        consumer: PowerNode,
        transfer_amount: float,
        source_transformer: PowerNode
    ) -> float:
        """
        Calcula um score para um transformador candidato baseado em múltiplos fatores.
        Score considera: eficiência global (60%), eficiência do transformador (20%),
        eficiência da aresta (10%), capacidade disponível (10%).
        """
        global_efficiency = self._simulate_redistribution_efficiency(
            consumer, source_transformer, transformer, transfer_amount
        )
        normalized_global = min(global_efficiency / 1000.0, 1.0)
        global_score = normalized_global * 0.6
        
        transformer_efficiency = transformer.efficiency
        transformer_score = transformer_efficiency * 0.2
        
        edge = self.graph.get_edge_obj(transformer.id, consumer.id)
        edge_efficiency = edge.efficiency if edge else 0.95
        edge_score = edge_efficiency * 0.1
        
        available_capacity = transformer.available_capacity
        max_capacity = transformer.max_capacity
        capacity_ratio = min(available_capacity / max_capacity, 1.0) if max_capacity > 0 else 0.0
        capacity_score = capacity_ratio * 0.1
        
        return global_score + transformer_score + edge_score + capacity_score
    
    def _find_alternative_transformers(
        self, 
        consumer_id: int, 
        exclude_transformer_id: int,
        consumer: Optional[PowerNode] = None,
        source_transformer: Optional[PowerNode] = None,
        estimated_transfer_amount: float = 0.0
    ) -> List[Tuple[PowerNode, float, float]]:
        """
        Encontra outros transformadores que podem alimentar um consumidor.
        Agora usa heurística global de eficiência para ordenar os candidatos.
        
        Args:
            consumer_id: ID do consumidor
            exclude_transformer_id: ID do transformador a excluir (o sobrecarregado)
            consumer: Objeto do consumidor (opcional, para evitar busca)
            source_transformer: Transformador fonte (opcional, para cálculo de score)
            estimated_transfer_amount: Quantidade estimada a transferir (para cálculo de score)
            
        Returns:
            Lista de tuplas (transformador, capacidade_disponível, score_eficiência) 
            ordenada por score de eficiência (maior primeiro)
        """
        alternatives = []
        
        if not consumer:
            consumer = self.graph.get_node(consumer_id)
        
        if not consumer:
            return alternatives
        
        # Busca todos os transformadores conectados a este consumidor
        edges = self.graph.get_neighbors(consumer_id)
        
        for edge in edges:
            neighbor_id = edge.target if edge.source == consumer_id else edge.source
            neighbor = self.graph.get_node(neighbor_id)
            
            if (neighbor and 
                neighbor.active and 
                neighbor.type == NodeType.TRANSFORMER and
                neighbor.id != exclude_transformer_id):
                
                # CRÍTICO: Não redistribui para transformadores que já estão sobrecarregados (>60%)
                # Isso evita cascatas de redistribuições
                if neighbor.load_percentage > self.THRESHOLD_PERCENTAGE:
                    continue
                
                # CRÍTICO: Não redistribui para transformadores recém-reativados
                # Isso evita que todos os transformadores sobrecarregados tentem redistribuir simultaneamente
                # para um transformador que acabou de ser reativado
                if neighbor.id in self.recently_reactivated:
                    continue
                
                # NOVO: Verifica estabilidade - só redistribui se a diferença de carga for significativa
                # Isso evita oscilações entre transformadores com cargas similares
                load_difference = source_transformer.load_percentage - neighbor.load_percentage if source_transformer else 0.0
                if load_difference < self.MIN_LOAD_DIFFERENCE:
                    # Diferença muito pequena - não redistribui para evitar oscilações
                    continue
                
                # Calcula capacidade disponível (deixa margem de 20%)
                available_capacity = neighbor.available_capacity * 0.8
                
                if available_capacity > self.MIN_REDISTRIBUTION_AMOUNT:
                    # Calcula score de eficiência se temos informações suficientes
                    efficiency_score = 0.0
                    if source_transformer and estimated_transfer_amount > 0:
                        # Usa a quantidade estimada ou a capacidade disponível, o que for menor
                        transfer_for_score = min(estimated_transfer_amount, available_capacity)
                        efficiency_score = self._calculate_transformer_score(
                            neighbor, consumer, transfer_for_score, source_transformer
                        )
                    else:
                        # Se não temos informações, usa apenas eficiência do transformador
                        efficiency_score = neighbor.efficiency
                    
                    # NOVO: Prioriza transformadores mais vazios para estabilizar a distribuição
                    # Score de estabilidade: quanto mais vazio, melhor (inverso do load_percentage)
                    stability_score = (1.0 - neighbor.load_percentage) * 0.3  # 30% de peso na estabilidade
                    
                    # Combina eficiência (70%) com estabilidade (30%)
                    combined_score = efficiency_score * 0.7 + stability_score * 0.3
                    
                    alternatives.append((neighbor, available_capacity, combined_score))
        
        # Ordena por score combinado (maior primeiro) - prioriza eficiência E estabilidade
        alternatives.sort(key=lambda x: x[2], reverse=True)
        
        return alternatives
    
    def _redistribute_consumer_load(
        self,
        consumer: PowerNode,
        source_transformer: PowerNode,
        target_transformers: List[Tuple[PowerNode, float, float]],
        amount_to_redistribute: float
    ) -> List[str]:
        """
        Redistribui parte da carga de um consumidor de um transformador para outros.
        Agora prioriza transformadores com melhor score de eficiência global.
        
        Args:
            consumer: Consumidor cuja carga será redistribuída
            source_transformer: Transformador atual (sobrecarregado)
            target_transformers: Lista de tuplas (transformador, capacidade, score_eficiência)
            amount_to_redistribute: Quantidade de kW a redistribuir
            
        Returns:
            Lista de mensagens sobre a redistribuição
        """
        logs = []
        
        if not target_transformers:
            return logs
        
        logs = []
        total_score = sum(score for _, _, score in target_transformers)
        
        if total_score <= 0:
            total_capacity = sum(cap for _, cap, _ in target_transformers)
            if total_capacity <= 0:
                return logs
            
            remaining_amount = amount_to_redistribute
            for target_transformer, available_capacity, _ in target_transformers:
                if remaining_amount <= 0.1:
                    break
                
                proportion = available_capacity / total_capacity
                transfer_amount = min(
                    remaining_amount * proportion,
                    available_capacity,
                    remaining_amount
                )
                
                max_receive_per_cycle = target_transformer.max_capacity * self.MAX_REDISTRIBUTION_PER_CYCLE_PCT
                transfer_amount = min(transfer_amount, max_receive_per_cycle)
                
                simulated_load = target_transformer.current_load + transfer_amount
                simulated_percentage = simulated_load / target_transformer.max_capacity if target_transformer.max_capacity > 0 else 0.0
                if simulated_percentage > self.THRESHOLD_PERCENTAGE:
                    max_safe_load = target_transformer.max_capacity * self.THRESHOLD_PERCENTAGE
                    transfer_amount = min(transfer_amount, max_safe_load - target_transformer.current_load)
                
                if transfer_amount < self.MIN_REDISTRIBUTION_AMOUNT:
                    continue
                
                logs.extend(self._apply_redistribution(
                    consumer, source_transformer, target_transformer, transfer_amount
                ))
                remaining_amount -= transfer_amount
        else:
            remaining_amount = amount_to_redistribute
            
            for target_transformer, available_capacity, efficiency_score in target_transformers:
                if remaining_amount <= 0.1:
                    break
                
                proportion = efficiency_score / total_score
                transfer_amount = min(
                    remaining_amount * proportion,
                    available_capacity,
                    remaining_amount
                )
                
                max_receive_per_cycle = target_transformer.max_capacity * self.MAX_REDISTRIBUTION_PER_CYCLE_PCT
                transfer_amount = min(transfer_amount, max_receive_per_cycle)
                
                simulated_load = target_transformer.current_load + transfer_amount
                simulated_percentage = simulated_load / target_transformer.max_capacity if target_transformer.max_capacity > 0 else 0.0
                if simulated_percentage > self.THRESHOLD_PERCENTAGE:
                    max_safe_load = target_transformer.max_capacity * self.THRESHOLD_PERCENTAGE
                    transfer_amount = min(transfer_amount, max_safe_load - target_transformer.current_load)
                    if transfer_amount < self.MIN_REDISTRIBUTION_AMOUNT:
                        continue
                
                if transfer_amount < self.MIN_REDISTRIBUTION_AMOUNT:
                    continue
                
                apply_logs = self._apply_redistribution(
                    consumer, source_transformer, target_transformer, transfer_amount
                )
                logs.extend(apply_logs)
                remaining_amount -= transfer_amount
        
        return logs
    
    def _apply_redistribution(
        self,
        consumer: PowerNode,
        source_transformer: PowerNode,
        target_transformer: PowerNode,
        transfer_amount: float
    ) -> List[str]:
        """
        Aplica uma redistribuição de carga entre transformadores.
        """
        logs = []
        
        source_edge = self.graph.get_edge_obj(source_transformer.id, consumer.id)
        if source_edge:
            current_source_flow = source_edge.current_flow if source_edge.current_flow > 0 else consumer.current_load
            new_source_flow = max(0, current_source_flow - transfer_amount)
            
            if consumer.parent_id == source_transformer.id and new_source_flow < consumer.current_load * 0.1:
                new_source_flow = max(new_source_flow, consumer.current_load * 0.1)
            
            source_edge.current_flow = new_source_flow
        else:
            logs.append(
                f"    AVISO: Transformador {source_transformer.id} não tem aresta com consumidor {consumer.id}"
            )
            return logs
        
        target_edge = self.graph.get_edge_obj(target_transformer.id, consumer.id)
        if target_edge:
            current_target_flow = target_edge.current_flow if target_edge.current_flow > 0 else 0
            target_edge.current_flow = current_target_flow + transfer_amount
        else:
            logs.append(
                f"    AVISO: Transformador {target_transformer.id} não tem aresta direta com consumidor {consumer.id} - não pode redistribuir"
            )
            return logs
        
        logs.append(
            f"    Redistribuído {transfer_amount:.1f}kW do Consumidor {consumer.id} "
            f"de T{source_transformer.id} para T{target_transformer.id} "
            f"(eficiência global otimizada)"
        )
        
        return logs
    
    def _simulate_cleanup_impact(
        self, 
        parent_transformer: PowerNode, 
        consumer: PowerNode,
        redistributions_to_clean: List[Tuple[PowerNode, float]]
    ) -> Tuple[bool, float]:
        """
        Simula o impacto de limpar redistribuições para um consumidor.
        Calcula quanto de carga voltaria para o transformador pai e verifica se causaria sobrecarga.
        """
        total_flow_to_return = 0.0
        for transformer, flow_amount in redistributions_to_clean:
            total_flow_to_return += flow_amount
        
        simulated_load = parent_transformer.current_load + total_flow_to_return
        simulated_load_percentage = simulated_load / parent_transformer.max_capacity if parent_transformer.max_capacity > 0 else 0.0
        
        if parent_transformer.load_percentage < 0.40:
            safety_threshold = 0.50
        elif parent_transformer.load_percentage < 0.50:
            safety_threshold = self.THRESHOLD_PERCENTAGE - self.SAFETY_MARGIN_PERCENTAGE
        else:
            safety_threshold = 0.52
        
        is_safe = simulated_load_percentage < safety_threshold
        return (is_safe, simulated_load_percentage)
    
    def _cleanup_old_redistributions(self) -> List[str]:
        """
        Limpa redistribuições antigas quando transformadores voltam ao normal (<60%).
        Usa verificação preditiva para evitar loops de redistribuição.
        """
        logs = []
        
        consumers = [
            node for node in self.graph.nodes.values()
            if node.active and node.type == NodeType.CONSUMER
        ]
        
        for consumer in consumers:
            edges = self.graph.get_neighbors(consumer.id)
            transformers_with_flow = []
            
            for edge in edges:
                neighbor_id = edge.target if edge.source == consumer.id else edge.source
                neighbor = self.graph.get_node(neighbor_id)
                
                if neighbor and neighbor.active and neighbor.type == NodeType.TRANSFORMER:
                    transformer_to_consumer_edge = self.graph.get_edge_obj(neighbor.id, consumer.id)
                    
                    if transformer_to_consumer_edge and transformer_to_consumer_edge.current_flow > 10:
                        transformers_with_flow.append((neighbor, transformer_to_consumer_edge, transformer_to_consumer_edge.current_flow))
            
            if not transformers_with_flow:
                continue
            
            parent_transformer = None
            if consumer.parent_id:
                parent_node = self.graph.get_node(consumer.parent_id)
                if parent_node and parent_node.active and parent_node.type == NodeType.TRANSFORMER:
                    parent_transformer = parent_node
            
            if not parent_transformer:
                has_overloaded = any(t.load_percentage > self.THRESHOLD_PERCENTAGE for t, _, _ in transformers_with_flow)
                if not has_overloaded:
                    for transformer, edge, current_flow in transformers_with_flow:
                        if transformer.load_percentage <= self.THRESHOLD_PERCENTAGE:
                            old_flow = edge.current_flow
                            edge.current_flow = 0.0
                            logs.append(
                                f"[LIMPEZA] Sem pai hierárquico e nenhum transformador sobrecarregado - "
                                f"limpando redistribuição: T{transformer.id}→Cons{consumer.id} ({old_flow:.1f}kW → 0kW)"
                            )
                continue
            
            if parent_transformer.load_percentage < self.THRESHOLD_PERCENTAGE:
                still_overloaded_transformers = [
                    (t, e, cf) for t, e, cf in transformers_with_flow
                    if t.load_percentage > self.THRESHOLD_PERCENTAGE
                ]
                
                if parent_transformer.load_percentage < 0.40:
                    for transformer, edge, current_flow in transformers_with_flow:
                        if transformer.load_percentage <= self.THRESHOLD_PERCENTAGE:
                            old_flow = edge.current_flow
                            edge.current_flow = 0.0
                            logs.append(
                                f"[LIMPEZA AGRESSIVA] T{parent_transformer.id} está em {parent_transformer.load_percentage*100:.1f}% "
                                f"(muito abaixo de 60%) - limpando redistribuição: T{transformer.id}→Cons{consumer.id} "
                                f"({old_flow:.1f}kW → 0kW)"
                            )
                    continue
                
                redistributions_to_clean = []
                for transformer, edge, current_flow in transformers_with_flow:
                    if transformer.load_percentage <= self.THRESHOLD_PERCENTAGE:
                        redistributions_to_clean.append((transformer, current_flow))
                
                if redistributions_to_clean:
                    is_safe, simulated_percentage = self._simulate_cleanup_impact(
                        parent_transformer, consumer, redistributions_to_clean
                    )
                    
                    if not is_safe:
                        logs.append(
                            f"[VERIFICAÇÃO PREDITIVA] T{parent_transformer.id} está em {parent_transformer.load_percentage*100:.1f}%, "
                            f"mas limpar redistribuições levaria a {simulated_percentage*100:.1f}% - MANTENDO redistribuições ativas"
                        )
                        continue
                
                for transformer, edge, current_flow in transformers_with_flow:
                    if transformer.id != parent_transformer.id:
                        if transformer.load_percentage <= self.THRESHOLD_PERCENTAGE:
                            old_flow = edge.current_flow
                            edge.current_flow = 0.0
                            logs.append(
                                f"[LIMPEZA] T{parent_transformer.id} voltou ao normal ({parent_transformer.load_percentage*100:.1f}%) - "
                                f"revertendo redistribuição: T{transformer.id}→Cons{consumer.id} ({old_flow:.1f}kW → 0kW)"
                            )
                    else:
                        if len(still_overloaded_transformers) == 0:
                            old_flow = edge.current_flow
                            edge.current_flow = 0.0
                            logs.append(
                                f"[LIMPEZA] T{parent_transformer.id} voltou ao normal ({parent_transformer.load_percentage*100:.1f}%) - "
                                f"limpando fluxo para Cons{consumer.id} ({old_flow:.1f}kW → 0kW) - verificação preditiva: seguro"
                            )
        
        return logs

