import sys
import os
import shutil
import random
import numpy as np
import matplotlib.pyplot as plt 

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.simulation.simulator import GridSimulator
from src.core.models.node import NodeType

def clean_persistence():
    path = "data"
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
        except Exception:
            pass

def create_complex_mesh_topology(sim: GridSimulator):
    """Cria uma rede tipo 'Grid' 5x6 (30 nós)."""
    sim.graph.nodes.clear()
    sim.graph.adj_list.clear()
    
    from src.core.structures.avl_tree import AVLTree
    sim.avl = AVLTree() 
    sim.balancer.avl = sim.avl

    for i in range(30):
        ntype = NodeType.SUBSTATION if i < 5 else NodeType.CONSUMER
        cap = 5000 if ntype == NodeType.SUBSTATION else 1000
        sim.add_node(i, ntype, cap, x=i*10, y=i*10, efficiency=0.98)

    rows, cols = 5, 6
    for r in range(rows):
        for c in range(cols):
            node_id = r * cols + c
            if c < cols - 1:
                neighbor = r * cols + (c + 1)
                sim.graph.add_edge(node_id, neighbor, 1.0, 0.05, 0.99)
            if r < rows - 1:
                neighbor = (r + 1) * cols + c
                sim.graph.add_edge(node_id, neighbor, 1.0, 0.05, 0.99)

def inject_distributed_stress(sim: GridSimulator, tick: int):
    """Cenário: Pico de consumo na Zona Central."""
    if 10 <= tick <= 30:
        stress_nodes = [14, 15, 20, 21]
        for nid in stress_nodes:
            node = sim.graph.get_node(nid)
            if node:
                # Adiciona ruído para realismo
                noise = random.uniform(-50, 50)
                overload = 1300.0 + noise
                
                node.update_load(overload)
                sim.balancer.update_node_load(nid, overload)

def plot_results(baseline_hist, optimized_hist):
    """Gera o gráfico comparativo final."""
    plt.figure(figsize=(10, 6))
    
    ticks = range(len(baseline_hist))
    
    plt.plot(ticks, baseline_hist, color='red', linestyle='--', label='Baseline (Sem IA)')
    plt.plot(ticks, optimized_hist, color='green', linewidth=2, label='EcoGrid+ (Com IA)')
    
    # Destaque para a zona de estresse
    plt.axvspan(10, 30, color='yellow', alpha=0.2, label='Período de Sobrecarga')
    
    plt.xlabel('Tempo (Ticks)')
    plt.ylabel('Eficiência Global (E)')
    plt.title('Comparativo de Resiliência: Baseline vs EcoGrid+')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Garante a pasta
    if not os.path.exists("data"):
        os.makedirs("data")
        
    save_path = "data/validation_efficiency_chart.png"
    plt.savefig(save_path)
    print(f"\n>> Gráfico salvo em: {save_path}")
    plt.show()

def run_realistic_validation():
    # Semente aleatória para garantir variedade, mas consistência interna
    MASTER_SEED = random.randint(0, 1000000)
    print(f"--- INICIANDO VALIDAÇÃO CIENTÍFICA (Seed: {MASTER_SEED}) ---")
    
    TICKS = 45 

    # ==========================================
    # 1. SIMULAÇÃO BASELINE
    # ==========================================
    clean_persistence()
    print("1. Rodando Baseline...")
    random.seed(MASTER_SEED) 
    
    sim_base = GridSimulator()
    create_complex_mesh_topology(sim_base)
    sim_base.balancer.update_node_load = lambda nid, l: [] 
    
    eff_base_history = []
    
    for t in range(TICKS):
        inject_distributed_stress(sim_base, t)
        sim_base.step()
        for node in sim_base.graph.nodes.values():
            if node.is_overloaded: node.efficiency = 0.6 
            else: node.efficiency = 0.98
        eff_base_history.append(sim_base.get_metrics()['efficiency'])

    avg_base = np.mean(eff_base_history)
    print(f"   -> Média Baseline: {avg_base:.4f}")

    # ==========================================
    # 2. SIMULAÇÃO ECOGRID+
    # ==========================================
    clean_persistence()
    print("\n2. Rodando EcoGrid+...")
    random.seed(MASTER_SEED)
    
    sim_opt = GridSimulator()
    create_complex_mesh_topology(sim_opt)
    
    eff_opt_history = []
    
    for t in range(TICKS):
        inject_distributed_stress(sim_opt, t)
        sim_opt.step()
        for node in sim_opt.graph.nodes.values():
            if node.is_overloaded: node.efficiency = 0.6
            else: node.efficiency = 0.98
        eff_opt_history.append(sim_opt.get_metrics()['efficiency'])

    avg_opt = np.mean(eff_opt_history)
    print(f"   -> Média Otimizada: {avg_opt:.4f}")

    # ==========================================
    # 3. RESULTADOS
    # ==========================================
    print("\n--- RELATÓRIO FINAL ---")
    improvement = ((avg_opt - avg_base) / avg_base) * 100
    print(f"Melhoria de Eficiência: {improvement:+.2f}%")
    
    if improvement > 5.0:
        print(">> SUCESSO: O sistema demonstrou robustez superior.")
    else:
        print(">> AVISO: Diferença pequena.")
        
    # GERA O GRÁFICO
    plot_results(eff_base_history, eff_opt_history)

if __name__ == "__main__":
    run_realistic_validation()