import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.algorithms.prediction import DemandPredictor

def test_hybrid_prediction():
    print("--- Iniciando Teste Híbrido (Linear + MLP) ---")
    
    predictor = DemandPredictor()
    
    # Padrão Oscilatório Simples (Cargas de AC: 100 -> 500 -> 100 -> 500...)
    # A Regressão Linear seria ruim aqui (daria uma média reta de 300).
    # A Rede Neural deve capturar que depois de 100 vem 500.
    history = [100.0, 500.0, 100.0, 500.0, 100.0, 500.0, 100.0] 
    
    print(f"Histórico de treino: {history}")
    predictor.fit(history)
    
    # Prever o próximo dado os últimos 3: [100, 500, 100] -> Esperamos 500
    prediction = predictor.predict_value_at(
        x_index=len(history),
        recent_history=history
    )
    
    print(f"Previsão do Modelo: {prediction:.2f}")
    
    # Aceitamos uma margem maior pois a MLP é estocástica e simples
    erro = abs(prediction - 500.0)
    print(f"Erro absoluto: {erro:.2f}")
    
    if erro < 150.0: # Margem generosa, mas suficiente para provar aprendizado vs média(300)
        print(">> SUCESSO: A Rede Neural capturou o padrão oscilatório.")
    else:
        print(">> AVISO: A rede precisa de mais treino ou ajuste de hiperparâmetros.")

if __name__ == "__main__":
    test_hybrid_prediction()