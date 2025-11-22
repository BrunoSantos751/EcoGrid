import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.simulation.simulator import GridSimulator

def test_simulation_run():
    print("--- Iniciando Teste do Maestro (Simulator) ---")
    
    sim = GridSimulator()
    sim.initialize_default_scenario()
    
    print("\nRodando 10 ticks de simulação...")
    for i in range(10):
        sim.step()
        metrics = sim.get_metrics()
        print(f"   > Métricas: E={metrics['efficiency']:.2f} | Carga Total={metrics['total_load']:.2f}")
        time.sleep(0.1)
        
    print("\nInjetando falha manual no Nó 10...")
    sim.inject_failure(10)
    
    print("Rodando mais 3 ticks para processar a falha...")
    for i in range(3):
        sim.step()

    print(">> SUCESSO: O Simulador integrou todos os módulos sem explodir.")

if __name__ == "__main__":
    test_simulation_run()