# src/core/algorithms/neural_net.py
import math
import random
from typing import List

class SimpleMLP:
    """
    Rede Neural (MLP) implementada do zero (Pure Python).
    Atende à especificação de 'Redes Neurais Simples' do projeto.
    Arquitetura: Input -> Hidden (Sigmoid) -> Output (Linear)
    """
    def __init__(self, input_size: int = 3, hidden_size: int = 4, learning_rate: float = 0.01):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.learning_rate = learning_rate
        
        # Inicialização de Pesos (Randomicos pequenos)
        # Pesos Input -> Hidden
        self.weights_ih = [[random.uniform(-0.5, 0.5) for _ in range(hidden_size)] for _ in range(input_size)]
        self.bias_h = [0.0] * hidden_size
        
        # Pesos Hidden -> Output
        self.weights_ho = [random.uniform(-0.5, 0.5) for _ in range(hidden_size)]
        self.bias_o = 0.0

    def _sigmoid(self, x: float) -> float:
        # Função de ativação Sigmoid: f(x) = 1 / (1 + e^-x)
        # Proteção contra overflow
        if x < -500: return 0.0
        if x > 500: return 1.0
        return 1.0 / (1.0 + math.exp(-x))

    def _sigmoid_derivative(self, sigmoid_x: float) -> float:
        # Derivada da Sigmoid: f'(x) = f(x) * (1 - f(x))
        return sigmoid_x * (1.0 - sigmoid_x)

    def forward(self, inputs: List[float]) -> float:
        """Calcula a previsão (Forward Pass)."""
        if len(inputs) != self.input_size:
            return 0.0 # Erro de dimensão

        # 1. Input -> Hidden
        self.hidden_outputs = []
        for j in range(self.hidden_size):
            activation = self.bias_h[j]
            for i in range(self.input_size):
                activation += inputs[i] * self.weights_ih[i][j]
            self.hidden_outputs.append(self._sigmoid(activation))
            
        # 2. Hidden -> Output (Linear para regressão)
        final_output = self.bias_o
        for j in range(self.hidden_size):
            final_output += self.hidden_outputs[j] * self.weights_ho[j]
            
        return final_output

    def train(self, inputs: List[float], target: float):
        """Ajusta os pesos com base no erro (Backpropagation)."""
        # 1. Forward Pass (precisamos dos valores intermediários)
        prediction = self.forward(inputs)
        
        # 2. Cálculo do Erro (Output Layer)
        error = target - prediction
        # Derivada da função Linear é 1, então o gradiente é apenas o erro * learning_rate
        
        # 3. Backward Pass (Hidden -> Output)
        delta_ho = [0.0] * self.hidden_size
        for j in range(self.hidden_size):
            # Gradiente = Erro * Output_Hidden[j]
            delta_ho[j] = error * self.hidden_outputs[j]
            
            # Atualiza peso HO
            self.weights_ho[j] += self.learning_rate * delta_ho[j]
            
        self.bias_o += self.learning_rate * error

        # 4. Backward Pass (Input -> Hidden)
        # Precisamos distribuir o erro para a camada oculta
        for j in range(self.hidden_size):
            # Erro propagado: Erro_Total * Peso_Conexão * Derivada_Sigmoid
            hidden_error = error * self.weights_ho[j] 
            derivative = self._sigmoid_derivative(self.hidden_outputs[j])
            gradient = hidden_error * derivative
            
            # Atualiza pesos IH
            for i in range(self.input_size):
                self.weights_ih[i][j] += self.learning_rate * gradient * inputs[i]
            
            self.bias_h[j] += self.learning_rate * gradient