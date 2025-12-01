# EcoGrid+ - Documentação Técnica Completa

**Versão:** 1.0.0 (Janeiro 2025)
**Mantenedor:** EcoGrid+ Team

## Índice

1.  Arquitetura Geral
2.  Setup e Instalação
3.  Exemplos de Uso
4.  Troubleshooting

-----

## 1\. Arquitetura Geral

O sistema é dividido em camadas distintas para garantir a separação de responsabilidades.

### Camada de Apresentação

  * **Interface Gráfica:** Tkinter (EcoGrid+ Simulator GUI).

### Camada de Lógica

  * **GridSimulator:** Orquestra toda a simulação.
  * **Load Balancer:** Redistribui carga entre nós.
  * **EnergyRouter:** Encontra rotas ótimas com algoritmo A\*.
  * **Preventive Monitor:** IA Preditiva.
  * **Demand Predictor:** MLP + Regressão Linear.

### Camada de Estruturas

  * **EcoGridGraph:** Representação da Rede.
      * *AVLTree:* Índice para buscas $O(\log n)$.
      * *BPlusTree:* Persistência em disco.
  * **CircularBuffer:** Série Temporal.
  * **Priority EventQueue:** Eventos por prioridade.

### Camada de Persistência

  * **Persistence Manager:** Gerenciamento de arquivos em disco.
      * `network_topology.pkl` (Topologia).
      * `network_history.db` (Histórico B+).

-----

## 2\. Setup e Instalação

### Pré-requisitos

  * Python 3.9+
  * pip

### Instalação

**1. Clonar e Instalar Dependências**

```bash
# Clonar o repositório
git clone <seu-repositorio>
cd Ecogrid

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate # Linux/Mac
# ou
venv\Scripts\activate # Windows

# Instalar dependências
pip install -r requirements.txt
```

**2. Estrutura de Diretórios**

  * `src/core/`: Modelos (Node, Edge, Graph) e Algoritmos (Balancing, Routing, Prediction).
  * `src/structures/`: Estruturas de dados (AVL Tree, B+ Tree, Circular Buffer).
  * `src/ui/`: Interface gráfica (Tkinter).
  * `data/`: Arquivos de persistência e topologia.

### Executar Aplicação

**1. Executar Interface Gráfica**

A interface gráfica do EcoGrid+ utiliza Tkinter e está integrada no projeto. Para executar:

```bash
# Com o ambiente virtual ativado
python src/ui/fallback_gui.py
```

A interface gráfica fornece:
  * Visualização em tempo real da rede elétrica
  * Controles de simulação (iniciar, pausar, passo a passo)
  * Edição interativa da topologia
  * Ferramentas para injetar falhas e sobrecargas
  * Dashboard com métricas e logs

-----

## 3\. Exemplos de Uso

### Exemplo: Uso da Interface Gráfica

A interface gráfica permite interagir diretamente com a simulação:

1. **Iniciar Simulação:** Clique no botão "Iniciar" na barra de ferramentas
2. **Editar Nós:** Use o modo "Criar Nó" para adicionar novos nós à rede
3. **Simular Falhas:** Use os botões "Sobrecarga" ou "Desativar" e clique em um nó
4. **Visualizar Rotas:** As rotas calculadas pelo algoritmo A* são exibidas automaticamente no canvas
5. **Salvar/Carregar:** Use os botões "Snapshot" e "Carregar" para persistir o estado da simulação

-----

## 4\. Troubleshooting

**Interface gráfica não inicia**

  * *Causa:* Tkinter não está instalado ou ambiente virtual não está ativado.
  * *Solução:* Certifique-se de que o ambiente virtual está ativado e que todas as dependências estão instaladas.

**Erro ao carregar topologia**

  * *Causa:* Arquivo de topologia não encontrado ou corrompido.
  * *Solução:* Verifique se o arquivo `data/network_topology.pkl` existe ou crie uma nova topologia usando a interface gráfica.

**Performance lenta com muitos nós**

  * *Causa:* Renderização de muitos elementos no canvas.
  * *Solução:* O sistema é otimizado para até ~10.000 nós. Para redes maiores, considere ajustar a velocidade de simulação.

-----

## Performance

### Otimizações Implementadas

  * **AVL Tree:** Buscas em $O(\log n)$.
  * **B+ Tree:** Persistência eficiente.
  * **Circular Buffer:** Série temporal em $O(1)$.
  * **Priority Event Queue:** Eventos ordenados por prioridade.

### Limites

  * Máx ~10.000 nós para melhor performance.
  * Histórico: Últimos 1M registros.
