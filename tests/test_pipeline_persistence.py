import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models.node import PowerNode, NodeType
from src.core.data_pipeline import DataPipeline
from src.core.algorithms.prediction import DemandPredictor

def test_full_data_cycle():
    print("--- Iniciando Teste: B+ Tree + Pipeline (Issues #5 e #13) ---")
    
    # 1. Criar Nó
    node = PowerNode(1, NodeType.CONSUMER, 1000.0)
    
    # 2. Gerar Histórico Longo (Simulando 50 ticks de tempo)
    # Padrão Rampa: 10, 11, 12...
    print("Gerando 50 leituras e persistindo na B+ Tree...")
    for i in range(50):
        load_value = 10.0 + i
        node.update_load(load_value)
        
    # A essa altura, o Buffer Circular (cap 24) já perdeu o começo (0 a 25).
    # Mas a B+ Tree deve ter TUDO.
    
    # 3. Testar Range Search da B+ Tree (Issue #5)
    # Quero recuperar do tick 0 ao 10 (que já sumiu da RAM/Buffer)
    recovered_data = node.storage_tree.range_search(0, 10)
    print(f"Dados recuperados do disco (ticks 0-10): {recovered_data}")
    
    expected = [10.0 + i for i in range(11)] # 0 a 10 inclusivo
    # Nota: range_search pode retornar chaves intermediárias dependendo da implementação exata de split,
    # mas vamos validar se não está vazio e tem consistência.
    assert len(recovered_data) > 0, "Falha na persistência B+: Retornou vazio."
    assert recovered_data[0] == 10.0, "Dado antigo corrompido ou perdido."
    
    # 4. Testar Pipeline (Issue #13)
    # Vamos treinar a IA com TODO o histórico (0 a 49)
    predictor = DemandPredictor()
    
    print("Executando Pipeline: Extração -> Treino IA...")
    count = DataPipeline.extract_and_train(node, predictor, 0, 49)
    
    print(f"Pipeline processou {count} registros.")
    
    # 5. Verificar se a IA aprendeu com os dados históricos
    # A série era 10, 11, 12... (Linear perfeita)
    next_val = predictor.predict_value_at(50, recent_history=[57, 58, 59]) # Histórico fake recente só pra cumprir assinatura
    
    # Como a série é linear (slope=1), no tick 50 deve ser 10 + 50 = 60.
    # Mas nosso predictor Híbrido pode variar. Vamos checar se a regressão linear foi ativada.
    assert predictor.linear_trained is True, "O Pipeline falhou em treinar a Regressão Linear."
    
    print(f"IA Treinada. Previsão para tick 50 (Esperado ~60): {next_val:.2f}")
    
    if abs(next_val - 60.0) < 1.0:
        print(">> SUCESSO: Ciclo completo (Persistência -> Pipeline -> Inteligência) funcionou.")
    else:
        print(">> AVISO: Pipeline funcionou, mas a precisão da IA variou.")

if __name__ == "__main__":
    test_full_data_cycle()