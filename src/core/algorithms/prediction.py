from typing import List
import random
import math
from src.core.algorithms.neural_net import SimpleMLP

class DemandPredictor:
    """
    Módulo Híbrido Inteligente: Regressão Linear + MLP.
    Seleciona dinamicamente o melhor modelo baseado no erro histórico (MSE).
    """
    def __init__(self):
        # Semente para garantir que testes sejam reprodutíveis
        random.seed(42)
        
        # Modelo 1: Regressão Linear
        self.slope = 0.0
        self.intercept = 0.0
        self.linear_error = float('inf') # Armazena quão ruim é o modelo linear
        self.linear_trained = False
        
        # Modelo 2: Rede Neural (MLP)
        self.mlp = SimpleMLP(input_size=3, hidden_size=8, learning_rate=0.05)
        self.mlp_error = float('inf')    # Armazena quão ruim é o modelo MLP
        self.mlp_trained = False

    def fit(self, historical_data: List[float]):
        """
        Treina ambos os modelos e calcula qual deles 'explica' melhor os dados (menor MSE).
        """
        if len(historical_data) < 4:
            return

        n = len(historical_data)

        # --- 1. Treino Linear ---
        sum_x = sum(range(n))
        sum_y = sum(historical_data)
        sum_xy = sum(i * val for i, val in enumerate(historical_data))
        sum_x_squared = sum(i**2 for i in range(n))
        
        denominator = (n * sum_x_squared) - (sum_x ** 2)
        if denominator != 0:
            self.slope = ((n * sum_xy) - (sum_x * sum_y)) / denominator
            self.intercept = (sum_y - (self.slope * sum_x)) / n
            self.linear_trained = True
            
            # Calcular erro médio (MSE) da Linear nos dados de treino
            sq_errors = []
            for i in range(n):
                pred = (self.slope * i) + self.intercept
                sq_errors.append((historical_data[i] - pred) ** 2)
            self.linear_error = sum(sq_errors) / n
            
        # --- 2. Treino da Rede Neural ---
        input_size = self.mlp.input_size
        
        # Escala para normalizar (ajuda a MLP a não explodir)
        # Usamos o max do histórico para normalizar dinamicamente
        max_val = max(historical_data) if max(historical_data) > 0 else 1.0
        scale = 1.0 / (max_val * 1.2) # Margem de 20% para extrapolação

        epochs = 2000
        
        # Dados preparados
        windows = []
        targets = []
        for i in range(n - input_size):
            windows.append([x * scale for x in historical_data[i : i+input_size]])
            targets.append(historical_data[i+input_size] * scale)

        if not windows:
            return

        # Loop de Treino
        for _ in range(epochs):
            # Shuffle simples ajuda a evitar mínimos locais
            combined = list(zip(windows, targets))
            random.shuffle(combined)
            
            for w, t in combined:
                self.mlp.train(w, t)
        
        self.mlp_trained = True

        # Calcular erro médio (MSE) da MLP nos dados de treino
        mlp_sq_errors = []
        for i in range(n - input_size):
            # Recalcula a previsão com a rede treinada
            # Precisamos pegar o input original
            raw_window = historical_data[i : i+input_size]
            scaled_input = [x * scale for x in raw_window]
            
            pred_scaled = self.mlp.forward(scaled_input)
            pred_real = pred_scaled / scale
            
            real_val = historical_data[i+input_size]
            mlp_sq_errors.append((real_val - pred_real) ** 2)
        
        if mlp_sq_errors:
            self.mlp_error = sum(mlp_sq_errors) / len(mlp_sq_errors)
        else:
            self.mlp_error = float('inf')

    def predict_value_at(self, x_index: int, recent_history: List[float] = None) -> float:
        """
        Retorna a previsão usando o MELHOR modelo (menor erro de treino).
        """
        val_linear = 0.0
        val_mlp = 0.0
        
        # Cálculo Linear
        if self.linear_trained:
            val_linear = (self.slope * x_index) + self.intercept
            
        # Cálculo MLP
        has_mlp_input = self.mlp_trained and recent_history and len(recent_history) >= 3
        if has_mlp_input:
            last_3 = recent_history[-3:]
            # Recalcula escala (mesma lógica do fit)
            max_val = max(recent_history) if max(recent_history) > 0 else 1.0
            scale = 1.0 / (max_val * 1.2)
            
            scaled_input = [x * scale for x in last_3]
            val_mlp = self.mlp.forward(scaled_input) / scale
        
        # --- Lógica de Decisão Inteligente ---
        
        # 1. Se não temos MLP input, só resta Linear
        if not has_mlp_input:
            return val_linear

        # 2. Comparação de Erros (Quem errou menos no passado?)
        adjusted_mlp_error = self.mlp_error * 1.2 
        
        # Se a Linear for muito precisa (Erro ~ 0), prefira Linear (Resolve o caso da Rampa)
        if self.linear_error < 1.0: 
            return val_linear
            
        # Se a MLP for significativamente melhor que a Linear, use MLP (Resolve o caso da Onda)
        if adjusted_mlp_error < self.linear_error:
            return val_mlp
        else:
            return val_linear