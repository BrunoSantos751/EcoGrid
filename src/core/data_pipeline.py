from typing import List
from src.core.models.node import PowerNode
from src.core.algorithms.prediction import DemandPredictor

class DataPipeline:
    """
    Conecta a Camada de Persistência (B+ Tree) à Camada de Inteligência (Prediction).
    """
    
    @staticmethod
    def extract_and_train(node: PowerNode, predictor: DemandPredictor, start_time: int, end_time: int):
        """
        1. Extrai histórico da B+ Tree do nó (Range Query).
        2. Alimenta o 'fit' do preditor.
        """
        
        # Supondo que o 'storage' do nó seja a B+ Tree (vamos integrar abaixo)
        if not hasattr(node, 'storage_tree'):
            print(f"Erro: Nó {node.id} não possui armazenamento persistente.")
            return

        historical_data = node.storage_tree.range_search(start_time, end_time)
        
        if len(historical_data) < 4:
            # Dados insuficientes para treino
            return
            
        # Treina o modelo (Linear + MLP) com os dados extraídos do "disco"
        predictor.fit(historical_data)
        
        return len(historical_data) # Retorna quantos pontos foram usados