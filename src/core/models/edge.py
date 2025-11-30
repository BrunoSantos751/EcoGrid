class PowerLine:
    """
    Representa uma linha de transmissão (Aresta) baseada em física.
    Usado para cálculo de perdas reais (P = I²R).
    """
    def __init__(self, source_id: int, target_id: int, distance_km: float, resistance_ohm: float, efficiency: float = 0.99):
        self.source = source_id
        self.target = target_id
        self.distance = distance_km
        self.resistance = resistance_ohm
        self.efficiency = efficiency
        self.current_flow = 0.0
    
    def calculate_power_loss(self, current_amperes: float) -> float:
        """Calcula perda real de potência usando P = I²R."""
        if current_amperes <= 0:
            return 0.0
        return (current_amperes ** 2) * self.resistance

    @property
    def weight(self) -> float:
        """Calcula o custo energético da aresta (para roteamento A*)."""
        if self.efficiency <= 0:
            return float('inf')
        return (self.distance * self.resistance) / self.efficiency

    def __repr__(self):
        return f"Linha {self.source}<->{self.target} (Flow: {self.current_flow})"