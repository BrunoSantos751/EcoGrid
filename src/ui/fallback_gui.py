# src/ui/fallback_gui.py
import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog, messagebox
import sys
import os
import random
import math

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.core.simulation.simulator import GridSimulator
from src.core.models.node import NodeType
from src.core.simulation.event_queue import PriorityLevel, EventType

class EcoGridApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EcoGrid+ Simulator (Cenário Urbano Realista)")
        # Responsividade: tamanho mínimo e inicial
        self.root.minsize(1200, 700)
        self.root.geometry("1366x768")
        # Permite redimensionamento
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        self.sim = GridSimulator()
        
        # Variável para armazenar rotas calculadas (para visualização)
        self.calculated_routes = {}  # {node_id: [lista de nós na rota]}
        
        # --- CENÁRIO PARA DEMONSTRAÇÃO DE ROTAS INTELIGENTES ---
        # Carrega uma topologia otimizada para observar rotas A*
        self.setup_routing_demo_scenario() 
        
        self.is_running = False
        self.simulation_speed = 100
        
        # Modos de Interação
        self.interaction_mode = "VIEW" 
        self.pending_node_data = None 
        self.selected_node_id = None
        
        self.create_layout()
        self.draw_network()
        self.update_dashboard()

    def create_layout(self):
        # --- 1. BARRA DE FERRAMENTAS ---
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED, bg="#f0f0f0")
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        btn_opts = {'side': tk.LEFT, 'padx': 5, 'pady': 5}
        
        # Simulação
        self.btn_start = tk.Button(toolbar, text="▶ Iniciar", command=self.toggle_simulation, bg="#ddffdd", width=10)
        self.btn_start.pack(**btn_opts)
        self.btn_noise = tk.Button(toolbar, text="🔊 Ruído ON", command=self.toggle_noise, bg="#ccffcc")
        self.btn_noise.pack(**btn_opts)
        tk.Button(toolbar, text="⏯ Passo", command=self.step_once).pack(**btn_opts)
        
        tk.Label(toolbar, text="|", bg="#f0f0f0", fg="#999").pack(side=tk.LEFT, padx=10)
        
        # Edição
        tk.Button(toolbar, text="➕ Criar Nó", command=self.open_add_node_dialog, bg="#eebbff").pack(**btn_opts)
        
        tk.Label(toolbar, text="|", bg="#f0f0f0", fg="#999").pack(side=tk.LEFT, padx=10)
        
        # Falhas e Reparos
        tk.Button(toolbar, text="🔥 Sobrecarga", command=self.start_stress_mode, bg="#ffccaa").pack(**btn_opts)
        tk.Button(toolbar, text="💀 Desativar", command=self.start_kill_mode, bg="#ffaaaa").pack(**btn_opts)
        tk.Button(toolbar, text="♻️ Reativar", command=self.start_revive_mode, bg="#aaffaa").pack(**btn_opts)
        tk.Button(toolbar, text="✨ Normalizar", command=self.start_normalize_mode, bg="#aaccff").pack(**btn_opts)
        
        # Reset
        tk.Button(toolbar, text="✋ Cancelar", command=self.reset_mode).pack(side=tk.LEFT, padx=20)
        
        # Persistência
        tk.Button(toolbar, text="📂 Carregar", command=self.load_snapshot).pack(side=tk.RIGHT, padx=5, pady=5)
        tk.Button(toolbar, text="💾 Snapshot", command=self.save_snapshot).pack(side=tk.RIGHT, padx=5, pady=5)

        # --- 2. ÁREA PRINCIPAL (Responsiva) ---
        main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=5, sashrelief=tk.RAISED)
        main_pane.pack(fill=tk.BOTH, expand=True)
        
        # Canvas (Responsivo) - PRIMEIRO para garantir que ocupe o espaço principal
        self.canvas_frame = tk.Frame(main_pane, bg="white")
        self.canvas_frame.columnconfigure(0, weight=1)
        self.canvas_frame.rowconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#ffffff", cursor="arrow")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.reset_mode)
        
        # Adiciona canvas PRIMEIRO com tamanho maior (garante que ocupe espaço principal)
        main_pane.add(self.canvas_frame, minsize=900)
        
        # Dashboard Lateral (Responsivo) - SEGUNDO para não sobrepor
        sidebar = tk.Frame(main_pane, width=350, bg="#e8e8e8")
        sidebar.columnconfigure(0, weight=1)
        # Adiciona sidebar SEGUNDO com tamanho fixo
        main_pane.add(sidebar, minsize=300)
        self._create_dashboard_widgets(sidebar)
        
        # Força o PanedWindow a respeitar os tamanhos iniciais e ajusta o divisor
        self.root.update_idletasks()
        # Ajusta a posição do sash (divisor) para garantir que o canvas tenha espaço adequado
        # Calcula posição baseada no tamanho da janela menos a largura do sidebar
        try:
            window_width = self.root.winfo_width()
            if window_width > 350:
                # Posiciona o divisor deixando 350px para o sidebar
                main_pane.sashpos(0, window_width - 350)
        except:
            pass  # Se falhar, deixa o padrão do PanedWindow

    def _create_dashboard_widgets(self, parent):
        # Container principal com scroll se necessário
        parent.columnconfigure(0, weight=1)
        
        # Frame interno para scroll
        inner_frame = tk.Frame(parent, bg="#e8e8e8")
        inner_frame.pack(fill=tk.BOTH, expand=True)
        inner_frame.columnconfigure(0, weight=1)
        
        tk.Label(inner_frame, text="EcoGrid+ Dashboard", font=("Segoe UI", 14, "bold"), bg="#e8e8e8").pack(pady=10)
        
        # Métricas (Responsivo)
        frame_metrics = tk.LabelFrame(inner_frame, text="Métricas Globais", bg="#e8e8e8", font=("Arial", 9, "bold"))
        frame_metrics.pack(fill=tk.X, padx=10, pady=5)
        frame_metrics.columnconfigure(0, weight=1)
        
        self.lbl_efficiency = tk.Label(frame_metrics, text="E: 0.00", font=("Segoe UI", 18, "bold"), fg="#0055aa", bg="#e8e8e8")
        self.lbl_efficiency.pack(pady=5)
        
        self.lbl_load = tk.Label(frame_metrics, text="Carga Total: 0 kW", font=("Consolas", 10), bg="#e8e8e8")
        self.lbl_load.pack(anchor="w", padx=5)
        self.lbl_tick = tk.Label(frame_metrics, text="Tick: 0", font=("Consolas", 10), bg="#e8e8e8")
        self.lbl_tick.pack(anchor="w", padx=5)

        # Inspetor (Responsivo)
        frame_inspector = tk.LabelFrame(inner_frame, text="Inspetor de Nó", bg="#e8e8e8", font=("Arial", 9, "bold"))
        frame_inspector.pack(fill=tk.X, padx=10, pady=10)
        frame_inspector.columnconfigure(0, weight=1)
        
        self.insp_id = tk.Label(frame_inspector, text="Selecione um nó...", font=("Arial", 10, "italic"), bg="#e8e8e8", fg="#666")
        self.insp_id.pack(anchor="w", padx=5, pady=2)
        self.insp_type = tk.Label(frame_inspector, text="", font=("Arial", 9), bg="#e8e8e8")
        self.insp_type.pack(anchor="w", padx=5)
        self.insp_load = tk.Label(frame_inspector, text="", font=("Arial", 9), bg="#e8e8e8")
        self.insp_load.pack(anchor="w", padx=5)
        self.insp_eff = tk.Label(frame_inspector, text="", font=("Arial", 9), bg="#e8e8e8")
        self.insp_eff.pack(anchor="w", padx=5)
        self.insp_status = tk.Label(frame_inspector, text="", font=("Arial", 9, "bold"), bg="#e8e8e8")
        self.insp_status.pack(anchor="w", padx=5)
        self.insp_neighbors = tk.Label(frame_inspector, text="", font=("Arial", 8), bg="#e8e8e8", justify=tk.LEFT, wraplength=300)
        self.insp_neighbors.pack(anchor="w", padx=5, pady=5)

        # Fila de Prioridade (Nova Feature)
        frame_queue = tk.LabelFrame(inner_frame, text="Fila de Prioridade", bg="#e8e8e8", font=("Arial", 9, "bold"))
        frame_queue.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        frame_queue.columnconfigure(0, weight=1)
        frame_queue.rowconfigure(0, weight=1)
        
        # Label com contador de eventos
        self.queue_count_label = tk.Label(frame_queue, text="Eventos: 0", font=("Arial", 8), bg="#e8e8e8", fg="#555")
        self.queue_count_label.pack(anchor="w", padx=5, pady=2)
        
        # Treeview para mostrar eventos ordenados
        queue_tree_frame = tk.Frame(frame_queue, bg="#e8e8e8")
        queue_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        queue_tree_frame.columnconfigure(0, weight=1)
        queue_tree_frame.rowconfigure(0, weight=1)
        
        # Scrollbar para a treeview
        queue_scrollbar = tk.Scrollbar(queue_tree_frame)
        queue_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview com colunas
        columns = ("Prioridade", "Tipo", "Nó", "Timestamp")
        self.queue_tree = ttk.Treeview(queue_tree_frame, columns=columns, show="headings", 
                                       yscrollcommand=queue_scrollbar.set, height=8)
        queue_scrollbar.config(command=self.queue_tree.yview)
        
        # Configurar colunas
        self.queue_tree.heading("Prioridade", text="Prioridade")
        self.queue_tree.heading("Tipo", text="Tipo de Evento")
        self.queue_tree.heading("Nó", text="Nó ID")
        self.queue_tree.heading("Timestamp", text="Timestamp")
        
        self.queue_tree.column("Prioridade", width=80, anchor="center")
        self.queue_tree.column("Tipo", width=120, anchor="w")
        self.queue_tree.column("Nó", width=60, anchor="center")
        self.queue_tree.column("Timestamp", width=100, anchor="w")
        
        self.queue_tree.pack(fill=tk.BOTH, expand=True)

        # Console (Responsivo)
        self.lbl_status = tk.Label(inner_frame, text="Modo: VISUALIZAÇÃO", font=("Arial", 10, "bold"), bg="#ddd", pady=5)
        self.lbl_status.pack(fill=tk.X, pady=(20, 0))
        tk.Label(inner_frame, text="Console de Eventos:", bg="#e8e8e8", anchor="w").pack(fill=tk.X, padx=10)
        
        # Frame para console com scroll
        console_frame = tk.Frame(inner_frame, bg="#e8e8e8")
        console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        
        self.log_console = scrolledtext.ScrolledText(console_frame, font=("Consolas", 8), state='normal', wrap=tk.WORD)
        self.log_console.grid(row=0, column=0, sticky="nsew")

    # --- SETUP CENÁRIO PARA DEMONSTRAÇÃO DE ROTAS INTELIGENTES ---
    def setup_routing_demo_scenario(self):
        """
        Cria um cenário otimizado para demonstrar o cálculo de rotas inteligentes (A*)
        seguindo a hierarquia: Subestação → Transformador → Consumidor.
        
        Estrutura:
        - 1 Subestação central
        - 4 Transformadores conectados à subestação
        - Consumidores distribuídos, alguns com múltiplas rotas possíveis via diferentes transformadores
        - Múltiplas rotas da subestação para desafogar transformadores sobrecarregados
        - Diferentes resistências nas arestas para o A* escolher rotas eficientes
        
        IMPORTANTE: Transformadores NÃO transferem carga entre si.
        A carga do transformador = soma dos consumidores + perdas dos cabos.
        """
        self.sim.graph.nodes.clear()
        self.sim.graph.adj_list.clear()
        self.sim.graph.root_nodes.clear()
        from src.core.structures.avl_tree import AVLTree
        from src.core.io.iot_simulator import IoTSensorNetwork
        self.sim.avl = AVLTree()
        self.sim.balancer.avl = self.sim.avl
        if hasattr(self.sim.balancer, 'load_avl'):
            self.sim.balancer._rebuild_load_avl()
        
        # --- 1. INFRAESTRUTURA (Backbone Hierárquico) ---
        # Subestação central (Nó 1) - Raiz da hierarquia
        self.sim.add_node(1, NodeType.SUBSTATION, 20000.0, x=640, y=100, efficiency=1.0, parent_id=None)
        
        # 4 Transformadores conectados à subestação (múltiplas rotas possíveis)
        # T1 - Esquerda Superior (Industrial)
        self.sim.add_node(2, NodeType.TRANSFORMER, 6000.0, x=300, y=300, efficiency=0.98, parent_id=1)
        # T2 - Centro Superior (Residencial) - Este será sobrecarregado
        self.sim.add_node(3, NodeType.TRANSFORMER, 5000.0, x=640, y=300, efficiency=0.96, parent_id=1)
        # T3 - Direita Superior (Comercial)
        self.sim.add_node(4, NodeType.TRANSFORMER, 5500.0, x=980, y=300, efficiency=0.95, parent_id=1)
        # T4 - Centro Inferior (Misto) - Para rotas alternativas
        self.sim.add_node(5, NodeType.TRANSFORMER, 5000.0, x=640, y=500, efficiency=0.97, parent_id=1)
        
        # Conexões Subestação -> Transformadores (múltiplas rotas com diferentes eficiências)
        self.sim.graph.add_edge(1, 2, 7.0, 0.015)  # Sub → T1 (rota 1)
        self.sim.graph.add_edge(1, 3, 5.0, 0.010)  # Sub → T2 (rota 2 - melhor)
        self.sim.graph.add_edge(1, 4, 7.0, 0.015)  # Sub → T3 (rota 3)
        self.sim.graph.add_edge(1, 5, 6.0, 0.012)  # Sub → T4 (rota 4 - alternativa)
        
        # IMPORTANTE: NÃO há conexões diretas entre transformadores
        # A energia só flui: Subestação → Transformador → Consumidor
        
        # --- 2. CONSUMIDORES COM MÚLTIPLAS ROTAS ALTERNATIVAS ---
        node_counter = 6
        
        # CONSUMIDOR 1 (Nó 6): Pode ser alimentado por T1, T2 ou T3
        # Este consumidor está no centro e pode receber energia de múltiplos transformadores
        self.sim.add_node(node_counter, NodeType.CONSUMER, 800.0, x=550, y=350, efficiency=0.98, parent_id=3)
        # Conexão principal: T2 → Consumidor (rota mais curta)
        self.sim.graph.add_edge(3, node_counter, 1.5, 0.015)
        # Rota alternativa 1: T1 → Consumidor (via subestação)
        self.sim.graph.add_edge(2, node_counter, 2.5, 0.020)
        # Rota alternativa 2: T3 → Consumidor (via subestação)
        self.sim.graph.add_edge(4, node_counter, 2.8, 0.022)
        node_counter += 1
        
        # CONSUMIDOR 2 (Nó 7): Pode ser alimentado por T2 ou T4
        # Este consumidor está entre T2 e T4
        self.sim.add_node(node_counter, NodeType.CONSUMER, 900.0, x=600, y=400, efficiency=0.98, parent_id=3)
        # Conexão principal: T2 → Consumidor
        self.sim.graph.add_edge(3, node_counter, 1.2, 0.012)
        # Rota alternativa: T4 → Consumidor (via subestação)
        self.sim.graph.add_edge(5, node_counter, 1.8, 0.018)
        node_counter += 1
        
        # CONSUMIDOR 3 (Nó 8): Pode ser alimentado por T1 ou T2
        # Este consumidor está na região entre T1 e T2
        self.sim.add_node(node_counter, NodeType.CONSUMER, 750.0, x=450, y=320, efficiency=0.98, parent_id=2)
        # Conexão principal: T1 → Consumidor
        self.sim.graph.add_edge(2, node_counter, 1.0, 0.010)
        # Rota alternativa: T2 → Consumidor (via subestação)
        self.sim.graph.add_edge(3, node_counter, 2.0, 0.018)
        node_counter += 1
        
        # CONSUMIDOR 4 (Nó 9): Pode ser alimentado por T2, T3 ou T4
        # Este consumidor está no centro e pode receber de 3 transformadores diferentes
        self.sim.add_node(node_counter, NodeType.CONSUMER, 850.0, x=700, y=380, efficiency=0.98, parent_id=3)
        # Conexão principal: T2 → Consumidor
        self.sim.graph.add_edge(3, node_counter, 1.3, 0.013)
        # Rota alternativa 1: T3 → Consumidor (via subestação)
        self.sim.graph.add_edge(4, node_counter, 2.2, 0.020)
        # Rota alternativa 2: T4 → Consumidor (via subestação)
        self.sim.graph.add_edge(5, node_counter, 2.0, 0.019)
        node_counter += 1
        
        # CONSUMIDOR 5 (Nó 10): Pode ser alimentado por T3 ou T4
        # Este consumidor está entre T3 e T4
        self.sim.add_node(node_counter, NodeType.CONSUMER, 950.0, x=800, y=400, efficiency=0.98, parent_id=4)
        # Conexão principal: T3 → Consumidor
        self.sim.graph.add_edge(4, node_counter, 1.1, 0.011)
        # Rota alternativa: T4 → Consumidor (via subestação)
        self.sim.graph.add_edge(5, node_counter, 2.5, 0.023)
        node_counter += 1
        
        # CONSUMIDOR 6 (Nó 11): Pode ser alimentado por T1 ou T4
        # Este consumidor está na região entre T1 e T4 (diagonal)
        self.sim.add_node(node_counter, NodeType.CONSUMER, 1000.0, x=500, y=450, efficiency=0.98, parent_id=2)
        # Conexão principal: T1 → Consumidor
        self.sim.graph.add_edge(2, node_counter, 2.0, 0.019)
        # Rota alternativa: T4 → Consumidor (via subestação)
        self.sim.graph.add_edge(5, node_counter, 1.5, 0.015)
        node_counter += 1
        
        # CONSUMIDOR 7 (Nó 12): Pode ser alimentado por T2 ou T3
        # Este consumidor está entre T2 e T3
        self.sim.add_node(node_counter, NodeType.CONSUMER, 1100.0, x=750, y=320, efficiency=0.98, parent_id=3)
        # Conexão principal: T2 → Consumidor
        self.sim.graph.add_edge(3, node_counter, 1.4, 0.014)
        # Rota alternativa: T3 → Consumidor (via subestação)
        self.sim.graph.add_edge(4, node_counter, 2.3, 0.021)
        node_counter += 1
        
        # CONSUMIDOR 8 (Nó 13): Pode ser alimentado por T1, T2 ou T4
        # Este consumidor está no centro e pode receber de 3 transformadores
        self.sim.add_node(node_counter, NodeType.CONSUMER, 900.0, x=550, y=420, efficiency=0.98, parent_id=3)
        # Conexão principal: T2 → Consumidor
        self.sim.graph.add_edge(3, node_counter, 1.6, 0.016)
        # Rota alternativa 1: T1 → Consumidor (via subestação)
        self.sim.graph.add_edge(2, node_counter, 2.6, 0.024)
        # Rota alternativa 2: T4 → Consumidor (via subestação)
        self.sim.graph.add_edge(5, node_counter, 1.2, 0.012)
        node_counter += 1
        
        # CONSUMIDOR 9 (Nó 14): Pode ser alimentado por T3 ou T4
        # Este consumidor está na região inferior direita
        self.sim.add_node(node_counter, NodeType.CONSUMER, 1050.0, x=850, y=450, efficiency=0.98, parent_id=4)
        # Conexão principal: T3 → Consumidor
        self.sim.graph.add_edge(4, node_counter, 1.8, 0.017)
        # Rota alternativa: T4 → Consumidor (via subestação)
        self.sim.graph.add_edge(5, node_counter, 2.0, 0.020)
        node_counter += 1
        
        # CONSUMIDOR 10 (Nó 15): Pode ser alimentado por T1, T2, T3 ou T4
        # Este consumidor está no centro absoluto e pode receber de TODOS os transformadores
        self.sim.add_node(node_counter, NodeType.CONSUMER, 800.0, x=640, y=400, efficiency=0.98, parent_id=3)
        # Conexão principal: T2 → Consumidor (mais próximo)
        self.sim.graph.add_edge(3, node_counter, 1.0, 0.010)
        # Rota alternativa 1: T1 → Consumidor (via subestação)
        self.sim.graph.add_edge(2, node_counter, 3.4, 0.030)
        # Rota alternativa 2: T3 → Consumidor (via subestação)
        self.sim.graph.add_edge(4, node_counter, 3.4, 0.030)
        # Rota alternativa 3: T4 → Consumidor (via subestação)
        self.sim.graph.add_edge(5, node_counter, 1.0, 0.010)
        node_counter += 1
        
        # Reinicializa IoT
        from src.core.io.iot_simulator import IoTSensorNetwork
        self.sim.iot_network = IoTSensorNetwork(self.sim.graph)
        
        # NOVO: Otimiza atribuição inicial de consumidores aos transformadores baseado em eficiência global
        optimization_logs = self.sim.optimize_initial_transformer_assignment()
        for log_msg in optimization_logs:
            self.sim.log(log_msg)
        
        self.sim.log("Cenário de Demonstração de Rotas Hierárquicas carregado.")
        self.sim.log("Estrutura: Subestação → Transformador → Consumidor")
        self.sim.log("Múltiplas rotas alternativas disponíveis!")
        self.sim.log("Dica: Coloque qualquer consumidor (6-15) em sobrecarga para ver rotas A* alternativas")
        self.sim.log("Exemplo: Consumidor 6 pode ser alimentado por T1, T2 ou T3")
        self.sim.log("Exemplo: Consumidor 10 pode ser alimentado por T1, T2, T3 ou T4")

    # --- SETUP CENÁRIO REALISTA (Mantido para referência) ---
    def setup_realistic_scenario(self):
        """
        Cria uma topologia 'Cidade' começando do ID 1.
        """
        self.sim.graph.nodes.clear()
        self.sim.graph.adj_list.clear()
        self.sim.graph.root_nodes.clear()  # Limpa nós raiz também
        from src.core.structures.avl_tree import AVLTree
        from src.core.io.iot_simulator import IoTSensorNetwork
        self.sim.avl = AVLTree()
        self.sim.balancer.avl = self.sim.avl
        # Reinicializa o balanceador com nova AVL de carga
        if hasattr(self.sim.balancer, 'load_avl'):
            self.sim.balancer._rebuild_load_avl()
        
        # --- 1. INFRAESTRUTURA (Backbone com Múltiplas Rotas de Escape) ---
        
        # Subestação (Nó 1) - O Chefe (raiz da hierarquia) - Centralizada
        self.sim.add_node(1, NodeType.SUBSTATION, 20000.0, x=640, y=120, efficiency=1.0, parent_id=None)
        
        # Transformadores (Nós 2-7) - Múltiplos transformadores para redundância
        # T1 (Industrial - Esquerda Superior)
        self.sim.add_node(2, NodeType.TRANSFORMER, 5000.0, x=200, y=280, efficiency=0.98, parent_id=1)
        # T2 (Residencial - Centro Superior)
        self.sim.add_node(3, NodeType.TRANSFORMER, 4000.0, x=640, y=280, efficiency=0.96, parent_id=1)
        # T3 (Comercial - Direita Superior)
        self.sim.add_node(4, NodeType.TRANSFORMER, 4000.0, x=1080, y=280, efficiency=0.95, parent_id=1)
        # T4 (Industrial - Esquerda Inferior)
        self.sim.add_node(5, NodeType.TRANSFORMER, 4500.0, x=200, y=450, efficiency=0.97, parent_id=1)
        # T5 (Residencial - Centro Inferior)
        self.sim.add_node(6, NodeType.TRANSFORMER, 3500.0, x=640, y=450, efficiency=0.96, parent_id=1)
        # T6 (Comercial - Direita Inferior)
        self.sim.add_node(7, NodeType.TRANSFORMER, 3500.0, x=1080, y=450, efficiency=0.94, parent_id=1)
        
        # Conexões Primárias (Subestação -> Todos os Transformadores) - Múltiplas rotas
        self.sim.graph.add_edge(1, 2, 8.0, 0.01)  # Subestação -> T1
        self.sim.graph.add_edge(1, 3, 6.0, 0.01)  # Subestação -> T2
        self.sim.graph.add_edge(1, 4, 8.0, 0.01)  # Subestação -> T3
        self.sim.graph.add_edge(1, 5, 9.0, 0.01)  # Subestação -> T4
        self.sim.graph.add_edge(1, 6, 7.0, 0.01)  # Subestação -> T5
        self.sim.graph.add_edge(1, 7, 9.0, 0.01)  # Subestação -> T6
        
        # Anel de Redundância Superior (T1-T2-T3) - Rotas de escape horizontais
        self.sim.graph.add_edge(2, 3, 4.5, 0.04)  # T1 <-> T2
        self.sim.graph.add_edge(3, 4, 4.5, 0.04)  # T2 <-> T3
        
        # Anel de Redundância Inferior (T4-T5-T6) - Rotas de escape horizontais
        self.sim.graph.add_edge(5, 6, 4.5, 0.04)  # T4 <-> T5
        self.sim.graph.add_edge(6, 7, 4.5, 0.04)  # T5 <-> T6
        
        # Conexões Verticais (Rotas de escape verticais) - Permite redistribuição entre níveis
        self.sim.graph.add_edge(2, 5, 3.0, 0.03)  # T1 <-> T4 (Esquerda)
        self.sim.graph.add_edge(3, 6, 3.0, 0.03)  # T2 <-> T5 (Centro)
        self.sim.graph.add_edge(4, 7, 3.0, 0.03)  # T3 <-> T6 (Direita)
        
        # Conexões Diagonais (Rotas de escape adicionais) - Maior redundância
        self.sim.graph.add_edge(2, 6, 5.0, 0.05)  # T1 <-> T5 (Diagonal)
        self.sim.graph.add_edge(4, 6, 5.0, 0.05)  # T3 <-> T5 (Diagonal)
        self.sim.graph.add_edge(3, 5, 5.0, 0.05)  # T2 <-> T4 (Diagonal)
        self.sim.graph.add_edge(3, 7, 5.0, 0.05)  # T2 <-> T6 (Diagonal)

        # --- 2. CONSUMIDORES (Clusters) ---
        # Começamos a contar do 8 para não bater com a infra (1-7)
        node_counter = 8
        
        # Cluster 1: Fábricas (Ao redor do T1 - Nó 2)
        for i in range(4):
            angle = (i / 4) * 2 * math.pi
            cx = 200 + 90 * math.cos(angle)
            cy = 280 + 90 * math.sin(angle)
            self.sim.add_node(node_counter, NodeType.CONSUMER, 2000.0, x=cx, y=cy, efficiency=0.99, parent_id=2)
            self.sim.graph.add_edge(2, node_counter, 1.0, 0.02)
            node_counter += 1

        # Cluster 2: Residencial (Ao redor do T2 - Nó 3)
        for i in range(5):
            angle = (i / 5) * 2 * math.pi
            cx = 640 + 80 * math.cos(angle)
            cy = 280 + 80 * math.sin(angle)
            self.sim.add_node(node_counter, NodeType.CONSUMER, 1200.0, x=cx, y=cy, efficiency=0.98, parent_id=3)
            self.sim.graph.add_edge(3, node_counter, 0.8, 0.08)
            node_counter += 1

        # Cluster 3: Comercial (Ao redor do T3 - Nó 4)
        for i in range(4):
            angle = (i / 4) * 2 * math.pi
            cx = 1080 + 90 * math.cos(angle)
            cy = 280 + 90 * math.sin(angle)
            self.sim.add_node(node_counter, NodeType.CONSUMER, 1500.0, x=cx, y=cy, efficiency=0.97, parent_id=4)
            self.sim.graph.add_edge(4, node_counter, 0.9, 0.06)
            node_counter += 1

        # Cluster 4: Industrial (Ao redor do T4 - Nó 5)
        for i in range(3):
            angle = (i / 3) * 2 * math.pi
            cx = 200 + 100 * math.cos(angle)
            cy = 450 + 100 * math.sin(angle)
            self.sim.add_node(node_counter, NodeType.CONSUMER, 1800.0, x=cx, y=cy, efficiency=0.99, parent_id=5)
            self.sim.graph.add_edge(5, node_counter, 1.0, 0.02)
            node_counter += 1

        # Cluster 5: Condomínio (Abaixo do T5 - Nó 6)
        start_x, start_y = 580, 520
        for row in range(2):
            for col in range(3):
                cx = start_x + (col * 60)
                cy = start_y + (row * 50)
                self.sim.add_node(node_counter, NodeType.CONSUMER, 1000.0, x=cx, y=cy, efficiency=0.98, parent_id=6)
                self.sim.graph.add_edge(6, node_counter, 0.5, 0.1)
                if col > 0:
                    self.sim.graph.add_edge(node_counter, node_counter-1, 0.2, 0.2)
                node_counter += 1

        # Cluster 6: Bairro Espalhado (Ao redor do T6 - Nó 7)
        for i in range(6):
            angle = i * 0.9
            dist = 70 + (i * 8)
            cx = 1080 + dist * math.cos(angle)
            cy = 450 + dist * math.sin(angle)
            eff = random.uniform(0.85, 0.95)
            self.sim.add_node(node_counter, NodeType.CONSUMER, 800.0, x=cx, y=cy, efficiency=eff, parent_id=7)
            self.sim.graph.add_edge(7, node_counter, 0.8, 0.3)
            node_counter += 1

        # CRÍTICO: Reinicializa a rede IoT após criar o cenário
        from src.core.io.iot_simulator import IoTSensorNetwork
        self.sim.iot_network = IoTSensorNetwork(self.sim.graph)
        
        # NOVO: Otimiza atribuição inicial de consumidores aos transformadores baseado em eficiência global
        optimization_logs = self.sim.optimize_initial_transformer_assignment()
        for log_msg in optimization_logs:
            self.sim.log(log_msg)
        
        self.sim.log("Cenário carregado (IDs iniciam em 1).")
        self.sim.log("Rede IoT reinicializada.")

    # --- INTERAÇÃO (ADD NODE CUSTOM) ---
    def open_add_node_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Adicionar Nó")
        dialog.geometry("350x400")
        
        var_id = tk.IntVar(value=self._suggest_next_id())
        var_type = tk.StringVar(value="CONSUMIDOR")
        var_cap = tk.DoubleVar(value=1000.0)
        var_eff = tk.DoubleVar(value=0.98) # Campo de Eficiência

        tk.Label(dialog, text="ID do Nó:").pack(pady=(10,0))
        tk.Entry(dialog, textvariable=var_id).pack()
        
        def on_type_change():
            t = var_type.get()
            if t == "CONSUMIDOR": var_cap.set(1000.0); var_eff.set(0.98)
            elif t == "TRANSFORMADOR": var_cap.set(5000.0); var_eff.set(0.96)
            elif t == "SUBESTACAO": var_cap.set(50000.0); var_eff.set(1.0)

        frm = tk.Frame(dialog); frm.pack()
        tk.Radiobutton(frm, text="Consumidor", variable=var_type, value="CONSUMIDOR", command=on_type_change).pack(anchor="w")
        tk.Radiobutton(frm, text="Transformador", variable=var_type, value="TRANSFORMADOR", command=on_type_change).pack(anchor="w")
        tk.Radiobutton(frm, text="Subestação", variable=var_type, value="SUBESTACAO", command=on_type_change).pack(anchor="w")
        
        tk.Label(dialog, text="Capacidade Máx (kW):").pack(pady=(10,0))
        tk.Entry(dialog, textvariable=var_cap).pack()
        
        # AQUI ESTÁ O CAMPO QUE VOCÊ PEDIU
        tk.Label(dialog, text="Eficiência Energética (0.0 - 1.0):").pack(pady=(10,0))
        tk.Entry(dialog, textvariable=var_eff).pack()
        
        def confirm():
            if self.sim.graph.get_node(var_id.get()):
                messagebox.showerror("Erro", "ID já existe!")
                return
            
            type_map = {"CONSUMIDOR": NodeType.CONSUMER, "TRANSFORMADOR": NodeType.TRANSFORMER, "SUBESTACAO": NodeType.SUBSTATION}
            
            self.pending_node_data = {
                'id': var_id.get(),
                'type': type_map[var_type.get()],
                'cap': var_cap.get(),
                'eff': var_eff.get() # Salva a eficiência escolhida
            }
            dialog.destroy()
            self.start_add_mode()

        tk.Button(dialog, text="Posicionar no Mapa ->", command=confirm, bg="#ccffcc", height=2).pack(pady=20, fill=tk.X, padx=20)

    # --- OUTROS MÉTODOS (Mantidos, apenas o update_inspector mudou) ---
    
    def update_inspector(self):
        if self.selected_node_id is None: return
        node = self.sim.graph.get_node(self.selected_node_id)
        if not node: return

        self.insp_id.config(text=f"Nó #{node.id}", font=("Arial", 12, "bold"), fg="black")
        self.insp_type.config(text=f"Tipo: {node.type}")
        
        pct = (node.current_load / node.max_capacity) * 100
        self.insp_load.config(text=f"Carga: {node.current_load:.1f} / {node.max_capacity:.0f} kW ({pct:.1f}%)")
        
        # MOSTRA A EFICIÊNCIA NO INSPETOR
        self.insp_eff.config(text=f"Eficiência: {node.efficiency:.2f}")
        
        status = "ATIVO" if node.active else "INATIVO"
        fg = "green" if node.active else "red"
        if node.is_overloaded and node.active: status = "SOBRECARGA"; fg="red"
        self.insp_status.config(text=f"Status: {status}", fg=fg)
        
        edges = self.sim.graph.get_neighbors(node.id)
        nids = [str(e.target if e.source == node.id else e.source) for e in edges]
        self.insp_neighbors.config(text=f"Vizinhos: {', '.join(nids[:8])}" + ("..." if len(nids)>8 else ""))

    # --- RESTANTE DO CÓDIGO (Igual ao anterior, apenas compactado para caber) ---
    def reset_mode(self, e=None):
        self.interaction_mode="VIEW"; self.pending_node_data=None; self.selected_node_id=None
        self.canvas.config(cursor="arrow"); self.lbl_status.config(text="Modo: VISUALIZAÇÃO", bg="#ddd")
        self.insp_id.config(text="Selecione um nó...", fg="#666"); self.insp_type.config(text="")
        self.insp_load.config(text=""); self.insp_eff.config(text=""); self.insp_status.config(text=""); self.insp_neighbors.config(text="")

    def start_add_mode(self): self.interaction_mode="ADD"; self.canvas.config(cursor="crosshair"); self.lbl_status.config(text="Modo: ADICIONAR", bg="#eebbff")
    def start_stress_mode(self): self.interaction_mode="STRESS"; self.canvas.config(cursor="fleur"); self.lbl_status.config(text="Modo: SOBRECARGA", bg="#ffccaa")
    def start_kill_mode(self): self.interaction_mode="KILL"; self.canvas.config(cursor="X_cursor"); self.lbl_status.config(text="Modo: DESATIVAR", bg="#ffaaaa")
    def start_revive_mode(self): self.interaction_mode="REVIVE"; self.canvas.config(cursor="plus"); self.lbl_status.config(text="Modo: REATIVAR", bg="#aaffaa")
    def start_normalize_mode(self): self.interaction_mode="NORMALIZE"; self.canvas.config(cursor="hand2"); self.lbl_status.config(text="Modo: NORMALIZAR", bg="#aaccff")

    def on_canvas_click(self, e):
        # Usa coordenadas diretas do evento (canvas sem scrollbars)
        x, y = e.x, e.y
        m = self.interaction_mode
        if m=="VIEW": self._handle_view_click(x,y)
        elif m=="ADD": self._handle_add(x,y); self.reset_mode()
        elif m=="STRESS": self._handle_stress(x,y); self.reset_mode()
        elif m=="KILL": self._handle_kill(x,y); self.reset_mode()
        elif m=="REVIVE": self._handle_revive(x,y); self.reset_mode()
        elif m=="NORMALIZE": self._handle_normalize(x,y); self.reset_mode()

    def _handle_view_click(self,x,y): tid=self._find_node_at_pos(x,y); self.selected_node_id=tid; self.update_inspector() if tid else self.reset_mode()
    def _handle_add(self,x,y):
        d=self.pending_node_data; self.sim.add_node(d['id'],d['type'],d['cap'],x,y,efficiency=d['eff'])
        nbs=self._find_k_closest_nodes(x,y,2,d['id'])
        for t in nbs: self.sim.graph.add_edge(d['id'],t,5.0,0.1)
        self.draw_network(); self.sim.log(f"Nó {d['id']} criado.")
    def _handle_stress(self,x,y):
        tid=self._find_node_at_pos(x,y)
        if tid is not None:
            n=self.sim.graph.get_node(tid)
            if n and n.type == NodeType.CONSUMER:
                nl=simpledialog.askfloat("Carga",f"Nova Carga (kW):",parent=self.root,initialvalue=n.max_capacity*1.5)
                if nl: 
                    self.sim.inject_manual_load(tid,nl)
                    # Força atualização imediata da infraestrutura para refletir mudanças
                    # (inject_manual_load já faz isso internamente, mas garantimos aqui também)
                    self.sim._update_infrastructure_loads()
                    # Calcula rota inteligente se o consumidor ficar sobrecarregado
                    if nl > n.max_capacity:
                        self._calculate_and_store_route(tid)
                    self.draw_network()
                    self.update_dashboard()
    def _handle_kill(self,x,y):
        tid=self._find_node_at_pos(x,y)
        if tid is not None and messagebox.askyesno("Confirmar",f"Desativar {tid}?"): 
            self.sim.inject_failure(tid)
            self.draw_network()
            self.update_dashboard()  # Atualiza a fila de prioridade para mostrar o evento CRITICAL
    def _handle_revive(self,x,y):
        tid=self._find_node_at_pos(x,y)
        if tid is not None:
            n=self.sim.graph.get_node(tid)
            if not n.active:
                # Usa a função do simulador que limpa redistribuições anteriores
                self.sim.reactivate_node(tid)
                self.draw_network()
                self.update_dashboard()
    def _handle_normalize(self,x,y):
        tid=self._find_node_at_pos(x,y)
        if tid is not None:
            n=self.sim.graph.get_node(tid)
            if n:
                # Guarda se estava sobrecarregado antes da normalização
                was_overloaded = n.is_overloaded
                
                # Normaliza o nó (remove sobrecarga manual e volta ao comportamento normal)
                self.sim.normalize_node(tid)
                
                # Atualiza a referência do nó após a normalização
                n = self.sim.graph.get_node(tid)
                
                # Remove rotas calculadas se o nó não estiver mais sobrecarregado
                if was_overloaded and tid in self.calculated_routes and not n.is_overloaded:
                    del self.calculated_routes[tid]
                
                self.draw_network()
                self.update_dashboard()
                self.update_inspector()

    def _find_node_at_pos(self,x,y,r=20):
        for n in self.sim.graph.nodes.values():
            if ((n.x-x)**2+(n.y-y)**2)**0.5<=r: return n.id
        return None
    def _find_k_closest_nodes(self,x,y,k=2,eid=None):
        d=[(((n.x-x)**2+(n.y-y)**2)**0.5,n.id) for n in self.sim.graph.nodes.values() if n.id!=eid]
        d.sort(key=lambda p:p[0]); return [p[1] for p in d[:k]]
    def _suggest_next_id(self): return max(self.sim.graph.nodes.keys())+1 if self.sim.graph.nodes else 1
    
    def toggle_noise(self): self.sim.enable_noise=not self.sim.enable_noise; self.btn_noise.config(text="🔊 ON" if self.sim.enable_noise else "🔇 OFF", relief=tk.RAISED if self.sim.enable_noise else tk.SUNKEN)
    def toggle_simulation(self): self.is_running=not self.is_running; self.btn_start.config(text="⏸" if self.is_running else "▶"); self.run_loop() if self.is_running else None
    def step_once(self): self.is_running=False; self.btn_start.config(text="▶"); self.sim.step(); self.draw_network(); self.update_dashboard()
    def run_loop(self):
        if self.is_running: self.sim.step(); self.draw_network(); self.update_dashboard(); self.root.after(self.simulation_speed, self.run_loop)
    def save_snapshot(self): 
        self.sim.save_state_manual()
        messagebox.showinfo("Info", "Snapshot salvo com sucesso!")
    
    def load_snapshot(self):
        """Carrega o snapshot (topologia) do disco."""
        # Confirma antes de carregar (vai sobrescrever o estado atual)
        if not messagebox.askyesno("Confirmar", "Isso irá substituir o estado atual. Continuar?"):
            return
        
        # Para a simulação se estiver rodando
        if self.is_running:
            self.is_running = False
            self.btn_start.config(text="▶")
        
        # Carrega o snapshot
        success = self.sim.load_state_manual()
        
        if success:
            # Atualiza a interface visual
            self.draw_network()
            self.update_dashboard()
            # Limpa rotas calculadas antigas
            self.calculated_routes.clear()
            messagebox.showinfo("Info", "Snapshot carregado com sucesso!")
        else:
            messagebox.showerror("Erro", "Não foi possível carregar o snapshot. Verifique se os arquivos existem.")
    
    def _calculate_and_store_route(self, overloaded_consumer_id: int):
        """
        Frontend: Apenas notifica o simulador sobre sobrecarga.
        A lógica de redistribuição está no simulador/balancer.
        """
        consumer = self.sim.graph.get_node(overloaded_consumer_id)
        if not consumer or consumer.type != NodeType.CONSUMER:
            return
        
        # Apenas loga - a lógica real está no simulador
        self.sim.log(f"[UI] Consumidor {overloaded_consumer_id} sobrecarregado. O simulador irá processar a redistribuição.")

    def draw_network(self):
        self.canvas.delete("all")
        
        # 1. Desenha Arestas
        processed = set()
        for u_id, lines in self.sim.graph.adj_list.items():
            nu = self.sim.graph.get_node(u_id)
            if not nu: continue
            
            for line in lines:
                key = tuple(sorted((line.source, line.target)))
                if key in processed: continue
                processed.add(key)
                
                nv = self.sim.graph.get_node(line.target)
                if not nv: continue

                # Cor da linha
                color = "#aaaaaa"
                width = 2
                
                # Se tiver fluxo alto passando AGORA, destaca a linha
                if line.current_flow > 10:
                    color = "#55aaff" # Azul elétrico indicando fluxo ativo
                    width = 4
                elif (nu.is_overloaded or nv.is_overloaded) and nu.active and nv.active:
                    color = "#ffaaaa"
                    width = 3
                else:
                    # Verifica se esta aresta faz parte de uma rota calculada
                    is_route_edge = False
                    for consumer_id, routes in self.calculated_routes.items():
                        for transformer_id, route in routes.items():
                            # Verifica se esta aresta está na rota
                            for i in range(len(route) - 1):
                                if (route[i] == u_id and route[i+1] == line.target) or \
                                   (route[i] == line.target and route[i+1] == u_id):
                                    is_route_edge = True
                                    break
                            if is_route_edge:
                                break
                        if is_route_edge:
                            break
                    
                    if is_route_edge:
                        color = "#00ff00"  # Verde para rotas A* calculadas
                        width = 3
                
                self.canvas.create_line(nu.x, nu.y, nv.x, nv.y, fill=color, width=width)
                
                # --- NOVO: DESENHAR TEXTO DO FLUXO ---
                if line.current_flow > 5.0: # Só mostra se for relevante (>5kW)
                    # Calcula ponto médio
                    mid_x = (nu.x + nv.x) / 2
                    mid_y = (nu.y + nv.y) / 2
                    
                    # Retângulo de fundo para ler melhor
                    text_val = f"{int(line.current_flow)}kW"
                    self.canvas.create_rectangle(mid_x-20, mid_y-8, mid_x+20, mid_y+8, fill="white", outline="blue")
                    self.canvas.create_text(mid_x, mid_y, text=text_val, font=("Arial", 8, "bold"), fill="blue")

        # 2. Desenha Nós (Inativos atrás, Ativos na frente)
        all_nodes = list(self.sim.graph.nodes.values())
        all_nodes.sort(key=lambda n: 0 if not n.active else 1)

        for node in all_nodes:
            # --- DEFINIÇÃO DE GEOMETRIA (Sempre acontece) ---
            if node.type == NodeType.SUBSTATION:
                radius = 22
            elif node.type == NodeType.TRANSFORMER:
                radius = 18
            else:
                radius = 15 # Consumidor padrão

            # --- DEFINIÇÃO DE CORES (Baseada no estado) ---
            if not node.active:
                color, outline = "#444444", "#000000" # Cinza (Morto)
            elif node.is_overloaded:
                color, outline = "#ff3333", "#880000" # Vermelho (Perigo)
            elif node.type == NodeType.SUBSTATION:
                color, outline = "#4488ff", "#003388" # Azul
            elif node.type == NodeType.TRANSFORMER:
                color, outline = "#ffaa00", "#884400" # Laranja
            else:
                color, outline = "#66cc66", "#004400" # Verde
            
            # Highlight de seleção
            width = 4 if self.selected_node_id == node.id else 2
            outline_final = "blue" if self.selected_node_id == node.id else outline
            
            # Agora 'radius' sempre existe!
            self.canvas.create_oval(
                node.x - radius, node.y - radius,
                node.x + radius, node.y + radius,
                fill=color, outline=outline_final, width=width
            )
            
            self.canvas.create_text(node.x, node.y, text=str(node.id), font=("Arial", 9, "bold"), fill="white")
            
            if node.active:
                txt_y = node.y + radius + 12
                # Fundo para texto
                self.canvas.create_rectangle(node.x-25, txt_y-7, node.x+25, txt_y+7, fill="#eeeeee", outline="", stipple="gray50")
                
                txt_color = "red" if node.is_overloaded else "black"
                self.canvas.create_text(node.x, txt_y, text=f"{int(node.current_load)}", font=("Arial", 8), fill=txt_color)
        
        # 3. Desenha rotas A* calculadas (sobrepostas) - Hierarquia: Subestação → Transformador → Consumidor
        for consumer_id, routes in self.calculated_routes.items():
            consumer_node = self.sim.graph.get_node(consumer_id)
            if not consumer_node or not consumer_node.is_overloaded:
                continue  # Só mostra rotas se o consumidor ainda estiver sobrecarregado
            
            for transformer_id, route in routes.items():
                # Desenha a rota completa como uma linha tracejada verde mais espessa
                # A rota segue: Subestação → ... → Transformador → Consumidor
                for i in range(len(route) - 1):
                    node_a = self.sim.graph.get_node(route[i])
                    node_b = self.sim.graph.get_node(route[i+1])
                    if node_a and node_b:
                        # Linha tracejada verde mais espessa para rota A* hierárquica
                        self.canvas.create_line(
                            node_a.x, node_a.y, node_b.x, node_b.y,
                            fill="#00ff00", width=4, dash=(8, 4)
                        )
                        # Seta indicando direção (ponto médio)
                        mid_x = (node_a.x + node_b.x) / 2
                        mid_y = (node_a.y + node_b.y) / 2
                        # Desenha uma seta maior e mais visível
                        angle = math.atan2(node_b.y - node_a.y, node_b.x - node_a.x)
                        arrow_size = 12
                        arrow_x = mid_x + math.cos(angle) * 15
                        arrow_y = mid_y + math.sin(angle) * 15
                        self.canvas.create_polygon(
                            arrow_x, arrow_y,
                            arrow_x - arrow_size * math.cos(angle - 0.6), arrow_y - arrow_size * math.sin(angle - 0.6),
                            arrow_x - arrow_size * math.cos(angle + 0.6), arrow_y - arrow_size * math.sin(angle + 0.6),
                            fill="#00ff00", outline="#00aa00", width=2
                        )
                
                # Adiciona label na rota mostrando o caminho
                if len(route) >= 2:
                    # Pega o primeiro nó (subestação) e o último (consumidor)
                    substation = self.sim.graph.get_node(route[0])
                    transformer = self.sim.graph.get_node(route[-2])  # Penúltimo é o transformador
                    if substation and transformer:
                        # Label próximo ao transformador mostrando a rota alternativa
                        label_x = transformer.x
                        label_y = transformer.y - 30
                        route_label = f"Rota: Sub→T{transformer.id}→Cons{consumer_id}"
                        self.canvas.create_rectangle(
                            label_x - 60, label_y - 8, label_x + 60, label_y + 8,
                            fill="#ffffaa", outline="#00aa00", width=2
                        )
                        self.canvas.create_text(
                            label_x, label_y, text=route_label,
                            font=("Arial", 7, "bold"), fill="#006600"
                        )

    def update_queue_display(self):
        """Atualiza a visualização da fila de prioridade em tempo real."""
        # Limpa itens anteriores
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        
        # Obtém todos os eventos da fila (ordenados por prioridade)
        events = self.sim.event_queue.get_all_events()
        
        # Obtém estatísticas da fila
        stats = self.sim.get_queue_statistics()
        
        # Atualiza contador com informações detalhadas
        if stats['total'] > 0:
            priority_info = ", ".join([f"{k}: {v}" for k, v in stats['by_priority'].items()])
            self.queue_count_label.config(text=f"Eventos: {stats['total']} ({priority_info})")
        else:
            self.queue_count_label.config(text=f"Eventos: 0")
        
        # Define cores baseadas na prioridade
        priority_colors = {
            PriorityLevel.CRITICAL: "#ff4444",  # Vermelho
            PriorityLevel.HIGH: "#ff8844",      # Laranja
            PriorityLevel.MEDIUM: "#ffaa00",    # Amarelo
            PriorityLevel.LOW: "#888888"        # Cinza
        }
        
        priority_names = {
            PriorityLevel.CRITICAL: "CRÍTICO",
            PriorityLevel.HIGH: "ALTA",
            PriorityLevel.MEDIUM: "MÉDIA",
            PriorityLevel.LOW: "BAIXA"
        }
        
        event_type_names = {
            EventType.LOAD_CHANGE: "Mudança de Carga",
            EventType.NODE_FAILURE: "Falha de Nó",
            EventType.MAINTENANCE: "Manutenção",
            EventType.OVERLOAD_WARNING: "Alerta Sobrecarga"
        }
        
        # Adiciona cada evento à treeview
        for event in events:
            priority_name = priority_names.get(event.priority, "UNKNOWN")
            event_type_name = event_type_names.get(event.event_type, event.event_type)
            timestamp_str = event.timestamp.strftime("%H:%M:%S.%f")[:-3] if hasattr(event.timestamp, 'strftime') else str(event.timestamp)
            
            # Insere o item na treeview
            item_id = self.queue_tree.insert("", tk.END, values=(
                priority_name,
                event_type_name,
                event.node_id,
                timestamp_str
            ))
            
            # Define cor do texto baseada na prioridade
            color = priority_colors.get(event.priority, "#000000")
            self.queue_tree.set(item_id, "Prioridade", priority_name)
            
            # Tag para aplicar cor (opcional, requer configuração de tags)
            tag = f"priority_{event.priority}"
            self.queue_tree.item(item_id, tags=(tag,))
        
        # Configura tags com cores (se suportado)
        for priority, color in priority_colors.items():
            self.queue_tree.tag_configure(f"priority_{priority}", foreground=color)

    def update_dashboard(self):
        m=self.sim.get_metrics(); self.lbl_efficiency.config(text=f"E: {m['efficiency']:.2f}")
        self.lbl_load.config(text=f"Carga: {m['total_load']:.0f} kW"); self.lbl_tick.config(text=f"Tick: {m['tick']}")
        self.log_console.delete(1.0,tk.END)
        for msg in reversed(self.sim.logs): self.log_console.insert(tk.END,msg+"\n")
        if self.selected_node_id is not None: self.update_inspector()
        # Atualiza a fila de prioridade em tempo real
        self.update_queue_display()

if __name__ == "__main__": root = tk.Tk(); app = EcoGridApp(root); root.mainloop()