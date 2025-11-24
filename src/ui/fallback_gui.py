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

class EcoGridApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EcoGrid+ Simulator (Cenário Urbano Realista)")
        self.root.geometry("1366x768")
        
        self.sim = GridSimulator()
        
        # --- CENÁRIO REALISTA ---
        # Carrega uma topologia que imita uma cidade pequena
        self.setup_realistic_scenario() 
        
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
        
        # Reset
        tk.Button(toolbar, text="✋ Cancelar", command=self.reset_mode).pack(side=tk.LEFT, padx=20)
        
        # Persistência
        tk.Button(toolbar, text="💾 Snapshot", command=self.save_snapshot).pack(side=tk.RIGHT, padx=5, pady=5)

        # --- 2. ÁREA PRINCIPAL ---
        main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)
        
        # Canvas
        self.canvas_frame = tk.Frame(main_pane, bg="white")
        self.canvas = tk.Canvas(self.canvas_frame, bg="#ffffff", cursor="arrow")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.reset_mode)
        
        main_pane.add(self.canvas_frame, minsize=900)
        
        # Dashboard Lateral
        sidebar = tk.Frame(main_pane, width=350, bg="#e8e8e8")
        main_pane.add(sidebar)
        self._create_dashboard_widgets(sidebar)

    def _create_dashboard_widgets(self, parent):
        tk.Label(parent, text="EcoGrid+ Dashboard", font=("Segoe UI", 14, "bold"), bg="#e8e8e8").pack(pady=10)
        
        # Métricas
        frame_metrics = tk.LabelFrame(parent, text="Métricas Globais", bg="#e8e8e8", font=("Arial", 9, "bold"))
        frame_metrics.pack(fill=tk.X, padx=10, pady=5)
        
        self.lbl_efficiency = tk.Label(frame_metrics, text="E: 0.00", font=("Segoe UI", 18, "bold"), fg="#0055aa", bg="#e8e8e8")
        self.lbl_efficiency.pack(pady=5)
        
        self.lbl_load = tk.Label(frame_metrics, text="Carga Total: 0 kW", font=("Consolas", 10), bg="#e8e8e8")
        self.lbl_load.pack(anchor="w", padx=5)
        self.lbl_tick = tk.Label(frame_metrics, text="Tick: 0", font=("Consolas", 10), bg="#e8e8e8")
        self.lbl_tick.pack(anchor="w", padx=5)

        # Inspetor
        frame_inspector = tk.LabelFrame(parent, text="Inspetor de Nó", bg="#e8e8e8", font=("Arial", 9, "bold"))
        frame_inspector.pack(fill=tk.X, padx=10, pady=10)
        
        self.insp_id = tk.Label(frame_inspector, text="Selecione um nó...", font=("Arial", 10, "italic"), bg="#e8e8e8", fg="#666")
        self.insp_id.pack(anchor="w", padx=5, pady=2)
        self.insp_type = tk.Label(frame_inspector, text="", font=("Arial", 9), bg="#e8e8e8")
        self.insp_type.pack(anchor="w", padx=5)
        self.insp_load = tk.Label(frame_inspector, text="", font=("Arial", 9), bg="#e8e8e8")
        self.insp_load.pack(anchor="w", padx=5)
        self.insp_eff = tk.Label(frame_inspector, text="", font=("Arial", 9), bg="#e8e8e8") # NOVO: Mostra Eficiência
        self.insp_eff.pack(anchor="w", padx=5)
        self.insp_status = tk.Label(frame_inspector, text="", font=("Arial", 9, "bold"), bg="#e8e8e8")
        self.insp_status.pack(anchor="w", padx=5)
        self.insp_neighbors = tk.Label(frame_inspector, text="", font=("Arial", 8), bg="#e8e8e8", justify=tk.LEFT)
        self.insp_neighbors.pack(anchor="w", padx=5, pady=5)

        # Console
        self.lbl_status = tk.Label(parent, text="Modo: VISUALIZAÇÃO", font=("Arial", 10, "bold"), bg="#ddd", pady=5)
        self.lbl_status.pack(fill=tk.X, pady=(20, 0))
        tk.Label(parent, text="Console de Eventos:", bg="#e8e8e8", anchor="w").pack(fill=tk.X, padx=10)
        self.log_console = scrolledtext.ScrolledText(parent, height=15, font=("Consolas", 8), state='normal')
        self.log_console.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    # --- SETUP CENÁRIO REALISTA ---
    def setup_realistic_scenario(self):
        """
        Cria uma topologia 'Cidade' começando do ID 1.
        """
        self.sim.graph.nodes.clear()
        self.sim.graph.adj_list.clear()
        from src.core.structures.avl_tree import AVLTree
        self.sim.avl = AVLTree()
        self.sim.balancer.avl = self.sim.avl
        
        # --- 1. INFRAESTRUTURA (Backbone) ---
        
        # Subestação (Nó 1) - O Chefe
        self.sim.add_node(1, NodeType.SUBSTATION, 10000.0, x=640, y=120, efficiency=1.0)
        
        # Transformadores (Nós 2, 3, 4)
        # T1 (Industrial - Esq)
        self.sim.add_node(2, NodeType.TRANSFORMER, 5000.0, x=250, y=320, efficiency=0.98)
        # T2 (Residencial Centro)
        self.sim.add_node(3, NodeType.TRANSFORMER, 3000.0, x=640, y=370, efficiency=0.96)
        # T3 (Residencial Direita)
        self.sim.add_node(4, NodeType.TRANSFORMER, 3000.0, x=1030, y=320, efficiency=0.92)
        
        # Conexões Backbone (Subestação -> Transformadores)
        self.sim.graph.add_edge(1, 2, 10.0, 0.01)
        self.sim.graph.add_edge(1, 3, 8.0, 0.01)
        self.sim.graph.add_edge(1, 4, 10.0, 0.01)
        
        # Anel de Redundância (Entre Transformadores)
        self.sim.graph.add_edge(2, 3, 5.0, 0.05)
        self.sim.graph.add_edge(3, 4, 5.0, 0.05)

        # --- 2. CONSUMIDORES (Clusters) ---
        # Começamos a contar do 5 para não bater com a infra
        node_counter = 5
        
        # Cluster 1: Fábricas (Ao redor do T1 - Nó 2)
        for i in range(5):
            angle = (i / 5) * 2 * math.pi
            cx = 250 + 100 * math.cos(angle)
            cy = 320 + 100 * math.sin(angle)
            self.sim.add_node(node_counter, NodeType.CONSUMER, 2000.0, x=cx, y=cy, efficiency=0.99)
            self.sim.graph.add_edge(2, node_counter, 1.0, 0.02) # Conecta ao Nó 2
            node_counter += 1

        # Cluster 2: Condomínio (Abaixo do T2 - Nó 3)
        start_x, start_y = 540, 470 
        for row in range(2):
            for col in range(4): 
                cx = start_x + (col * 70)
                cy = start_y + (row * 60)
                self.sim.add_node(node_counter, NodeType.CONSUMER, 1000.0, x=cx, y=cy, efficiency=0.98)
                self.sim.graph.add_edge(3, node_counter, 0.5, 0.1) # Conecta ao Nó 3
                if col > 0:
                    self.sim.graph.add_edge(node_counter, node_counter-1, 0.2, 0.2)
                node_counter += 1

        # Cluster 3: Bairro Espalhado (Direita do T3 - Nó 4)
        for i in range(12):
            angle = i * 0.8 
            dist = 80 + (i * 10) 
            cx = 1030 + dist * math.cos(angle)
            cy = 320 + dist * math.sin(angle) 
            eff = random.uniform(0.85, 0.95)
            
            self.sim.add_node(node_counter, NodeType.CONSUMER, 800.0, x=cx, y=cy, efficiency=eff)
            self.sim.graph.add_edge(4, node_counter, 0.8, 0.3) # Conecta ao Nó 4
            node_counter += 1

        self.sim.log("Cenário carregado (IDs iniciam em 1).")

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

    def on_canvas_click(self, e):
        x,y=e.x,e.y; m=self.interaction_mode
        if m=="VIEW": self._handle_view_click(x,y)
        elif m=="ADD": self._handle_add(x,y); self.reset_mode()
        elif m=="STRESS": self._handle_stress(x,y); self.reset_mode()
        elif m=="KILL": self._handle_kill(x,y); self.reset_mode()
        elif m=="REVIVE": self._handle_revive(x,y); self.reset_mode()

    def _handle_view_click(self,x,y): tid=self._find_node_at_pos(x,y); self.selected_node_id=tid; self.update_inspector() if tid else self.reset_mode()
    def _handle_add(self,x,y):
        d=self.pending_node_data; self.sim.add_node(d['id'],d['type'],d['cap'],x,y,efficiency=d['eff'])
        nbs=self._find_k_closest_nodes(x,y,2,d['id'])
        for t in nbs: self.sim.graph.add_edge(d['id'],t,5.0,0.1)
        self.draw_network(); self.sim.log(f"Nó {d['id']} criado.")
    def _handle_stress(self,x,y):
        tid=self._find_node_at_pos(x,y)
        if tid is not None:
            n=self.sim.graph.get_node(tid); nl=simpledialog.askfloat("Carga",f"Nova Carga:",parent=self.root,initialvalue=n.max_capacity*1.5)
            if nl: self.sim.inject_manual_load(tid,nl); self.draw_network()
    def _handle_kill(self,x,y):
        tid=self._find_node_at_pos(x,y)
        if tid is not None and messagebox.askyesno("Confirmar",f"Desativar {tid}?"): self.sim.inject_failure(tid); self.draw_network()
    def _handle_revive(self,x,y):
        tid=self._find_node_at_pos(x,y)
        if tid is not None:
            n=self.sim.graph.get_node(tid)
            if not n.active: n.active=True; n.current_load=0; self.sim.log(f"Nó {tid} ON."); self.draw_network()

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
    def save_snapshot(self): self.sim.save_state_manual(); messagebox.showinfo("Info","Salvo!")

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

    def update_dashboard(self):
        m=self.sim.get_metrics(); self.lbl_efficiency.config(text=f"E: {m['efficiency']:.2f}")
        self.lbl_load.config(text=f"Carga: {m['total_load']:.0f} kW"); self.lbl_tick.config(text=f"Tick: {m['tick']}")
        self.log_console.delete(1.0,tk.END)
        for msg in reversed(self.sim.logs): self.log_console.insert(tk.END,msg+"\n")
        if self.selected_node_id is not None: self.update_inspector()

if __name__ == "__main__": root = tk.Tk(); app = EcoGridApp(root); root.mainloop()