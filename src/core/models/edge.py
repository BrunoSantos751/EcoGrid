class PowerLine:
    """
    Representa uma linha de transmissão (Aresta) baseada em física.
    """
    def __init__(self, source_id: int, target_id: int, distance_km: float, resistance_ohm: float, efficiency: float = 0.99):
        self.source = source_id
        self.target = target_id
        self.distance = distance_km
        self.resistance = resistance_ohm
        self.efficiency = efficiency # Eficiência de 0.0 a 1.0
        self.current_flow = 0.0

    @property
    def weight(self) -> float:
        """
        Calcula o custo energético da aresta.
        Fórmula: (Distância * Resistência) / Eficiência
        """
        if self.efficiency <= 0:
            return float('inf') # Evita divisão por zero
        
        # Quanto maior a resistência ou distância, maior o "custo" para passar energia
        return (self.distance * self.resistance) / self.efficiency

    def __repr__(self):
        return f"Linha {self.source}<->{self.target} (Flow: {self.current_flow})"