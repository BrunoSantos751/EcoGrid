import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.algorithms.prediction import DemandPredictor

def test_linear_regression():
    print("--- Iniciando Teste de Previsão (Issue #12) ---")
    
    predictor = DemandPredictor()
    
    # Cenário 1: Carga subindo constantemente (Rampa Perfeita)
    # 10, 20, 30, 40, 50 ... O próximo DEVE ser 60.
    history_ramp = [10.0, 20.0, 30.0, 40.0, 50.0]
    
    print(f"Treinando com histórico: {history_ramp}")
    predictor.fit(history_ramp)
    
    # O próximo índice é 5 (já que temos 0,1,2,3,4)
    predicted_val = predictor.predict_value_at(5)
    
    print(f"Valor previsto para o próximo passo: {predicted_val}")
    
    # Margem de erro pequena para float
    assert abs(predicted_val - 60.0) < 0.001, f"Erro: Esperado 60.0, obteve {predicted_val}"
    
    # Cenário 2: Carga estável
    # 100, 100, 100 ... Próximo deve ser 100.
    history_flat = [100.0, 100.0, 100.0,100.0]
    predictor.fit(history_flat)
    predicted_flat = predictor.predict_value_at(3)
    print(f"Previsão para estável (100...): {predicted_flat}")
    
    assert abs(predicted_flat - 100.0) < 0.001, "Erro na previsão estável"
    
    print(">> SUCESSO: Regressão Linear identificou as tendências.")

if __name__ == "__main__":
    test_linear_regression()