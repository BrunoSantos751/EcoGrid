Aqui está a documentação técnica do **EcoGrid+** formatada em Markdown, baseada no arquivo fornecido.

-----

# EcoGrid+ - Documentação Técnica Completa

**Versão:** 1.0.0 (Janeiro 2025)
[cite\_start]**Mantenedor:** EcoGrid+ Team [cite: 533]

## Índice

1.  [Arquitetura Geral](https://www.google.com/search?q=%231-arquitetura-geral)
2.  [Setup e Instalação](https://www.google.com/search?q=%232-setup-e-instala%C3%A7%C3%A3o)
3.  [API REST](https://www.google.com/search?q=%233-api-rest)
4.  [WebSocket](https://www.google.com/search?q=%234-websocket)
5.  [Cliente TypeScript/JavaScript](https://www.google.com/search?q=%235-cliente-typescriptjavascript)
6.  [Integração Frontend](https://www.google.com/search?q=%236-integra%C3%A7%C3%A3o-frontend)
7.  [Exemplos de Uso](https://www.google.com/search?q=%237-exemplos-de-uso)
8.  [Troubleshooting](https://www.google.com/search?q=%238-troubleshooting)

-----

## 1\. Arquitetura Geral

[cite\_start]O sistema é dividido em camadas distintas para garantir a separação de responsabilidades[cite: 11].

### Camada de Apresentação

  * [cite\_start]**Frontend:** React + TypeScript/JavaScript (EcoGrid+ Dashboard)[cite: 13, 14].
  * [cite\_start]**Comunicação:** API REST (HTTP/HTTPS) e WebSocket (Tempo Real)[cite: 15, 16, 17, 18].

### Camada de Comunicação

  * [cite\_start]**Backend API:** FastAPI + CORS Middleware (Porta 8000)[cite: 20, 21].

### [cite\_start]Camada de Lógica [cite: 23]

  * [cite\_start]**GridSimulator:** Orquestra toda a simulação[cite: 37].
  * [cite\_start]**Load Balancer:** Redistribui carga entre nós[cite: 38].
  * [cite\_start]**EnergyRouter:** Encontra rotas ótimas com algoritmo A\*[cite: 25, 39].
  * [cite\_start]**Preventive Monitor:** IA Preditiva[cite: 25, 40].
  * [cite\_start]**Demand Predictor:** MLP + Regressão Linear[cite: 26, 41].

### [cite\_start]Camada de Estruturas [cite: 27]

  * **EcoGridGraph:** Representação da Rede.
      * *AVLTree:* Índice para buscas $O(\log n)$.
      * *BPlusTree:* Persistência em disco.
  * **CircularBuffer:** Série Temporal.
  * [cite\_start]**Priority EventQueue:** Eventos por prioridade[cite: 30].

### [cite\_start]Camada de Persistência [cite: 31]

  * [cite\_start]**Persistence Manager:** Gerenciamento de arquivos em disco[cite: 32].
      * [cite\_start]`network_topology.pkl` (Topologia)[cite: 33].
      * [cite\_start]`network_history.db` (Histórico B+)[cite: 34].

-----

## 2\. Setup e Instalação

### [cite\_start]Pré-requisitos [cite: 49]

  * Python 3.9+
  * Node.js 16+
  * pip, npm ou yarn

### Backend Setup

**1. [cite\_start]Clonar e Instalar Dependências** [cite: 56]

```bash
# Clonar o repositório
git clone <seu-repositorio>
cd ecogrid-backend

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate # Linux/Mac
# ou
venv\Scripts\activate # Windows

# Instalar dependências
pip install fastapi uvicorn pydantic python-multipart
```

**2. [cite\_start]Estrutura de Diretórios** [cite: 69]

  * `src/core/`: Modelos (Node, Edge, Graph) e Algoritmos (Balancing, Routing, Prediction).
  * `src/structures/`: Estruturas de dados (AVL Tree, B+ Tree, Circular Buffer).
  * `src/api/`: `main.py` (API Backend).
  * `data/`: Arquivos de persistência e topologia.

**3. [cite\_start]Executar Backend** [cite: 99]

```bash
# Via Uvicorn
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Ou usar Python diretamente
python api/main.py
```

[cite\_start]O servidor estará disponível em `http://localhost:8000` (Docs em `/docs`)[cite: 106, 108].

### Frontend Setup

**1. [cite\_start]Clonar e Instalar** [cite: 110]

```bash
# Criar projeto React
npx create-react-app ecogrid-frontend
cd ecogrid-frontend
# Ou usar Vite
npm create vite@latest ecogrid-frontend --template react

# Instalar dependências adicionais
npm install recharts lucide-react axios
```

**2. [cite\_start]Adicionar Cliente API** [cite: 120]

```bash
# Copiar o arquivo do cliente
cp ../api-client.js src/services/api-client.js
```

**3. [cite\_start]Executar Frontend** [cite: 124]

```bash
npm start # Desenvolvimento
# ou
npm run build # Produção
```

-----

## 3\. API REST

### Autenticação

Atualmente sem autenticação. [cite\_start]Em produção, recomenda-se adicionar JWT usando `fastapi.security`[cite: 134, 136].

### Endpoints Principais

#### Sistema

[cite\_start]**Verificar status (`GET /api/health`)** [cite: 144]

```bash
curl http://localhost:8000/api/health
```

*Resposta:*

```json
{
  "status": "online",
  "timestamp": "2025-01-15T10:30:45.123456",
  "simulator_ready": true
}
```

#### Rede

[cite\_start]**Obter nós (`GET /api/nodes`)** [cite: 156]
[cite\_start]Retorna a lista de todos os nós com detalhes (capacidade, carga, eficiência, status de sobrecarga)[cite: 162].

[cite\_start]**Atualizar carga manualmente (`POST /api/nodes/{node_id}/update-load`)** [cite: 181]

```bash
curl -X POST http://localhost:8000/api/nodes/1/update-load \
-H "Content-Type: application/json" \
-d '{"node_id": 1, "new_load": 7500}'
```

#### Simulação

[cite\_start]**Métricas globais (`GET /api/metrics`)** [cite: 188]
[cite\_start]Retorna tick atual, carga total, percentual de utilização, eficiência global e status da rede (ex: "WARNING")[cite: 194].

[cite\_start]**Controles de Simulação** [cite: 209, 213, 217, 221]

  * Start: `POST /api/simulation/start`
  * Pause: `POST /api/simulation/pause`
  * Reset: `POST /api/simulation/reset`
  * Step (Manual): `POST /api/simulation/step`

#### [cite\_start]Falhas e Recuperação [cite: 226, 230]

  * Simular falha: `POST /api/nodes/{node_id}/inject-failure`
  * Restaurar nó: `POST /api/nodes/{node_id}/restore`

#### [cite\_start]Roteamento (`POST /api/routing/a-star`) [cite: 235]

Encontra a rota ótima entre dois nós.

```bash
curl -X POST http://localhost:8000/api/routing/a-star \
-H "Content-Type: application/json" \
-d '{"start_node_id": 1, "target_node_id": 101, "verbose": true}'
```

#### [cite\_start]Persistência [cite: 251]

  * Salvar estado: `POST /api/persistence/save`
  * Carregar estado: `POST /api/persistence/load`

-----

## 4\. WebSocket

[cite\_start]**URL:** `ws://localhost:8000/ws/simulation` [cite: 263]

### Comandos Suportados (Client -\> Server)

1.  [cite\_start]**Get State:** Solicita o estado completo atual[cite: 275].
    ```javascript
    ws.send(JSON.stringify({ type: 'get_state' }));
    ```
2.  [cite\_start]**Step Simulation:** Avança um tick[cite: 284].
    ```javascript
    ws.send(JSON.stringify({ type: 'step' }));
    ```
3.  [cite\_start]**Keep-Alive:** Ping/Pong[cite: 294].
    ```javascript
    ws.send(JSON.stringify({ type: 'ping' }));
    ```

### [cite\_start]Eventos Broadcast (Server -\> Client) [cite: 303]

  * **Node Failure:** Notifica falha em um nó específico.
  * **Node Update:** Atualização de carga ou status.
  * **Simulation Update:** Novo tick, logs da IA e atualizações gerais.

-----

## 5\. Cliente TypeScript/JavaScript

O cliente encapsula as chamadas REST e WebSocket.

[cite\_start]**Instalação:** [cite: 327]

```bash
npm install ecogrid-api-client
# ou copiar api-client.js manualmente
```

[cite\_start]**Inicialização:** [cite: 334]

```javascript
import EcoGridAPIClient from './api-client.js';
const client = new EcoGridAPIClient('http://localhost:8000', 'ws://localhost:8000');
```

[cite\_start]**Métodos Principais:** [cite: 340]

  * `client.getAllNodes()`
  * `client.updateNodeLoad(id, load)`
  * `client.injectNodeFailure(id)`
  * `client.getMetrics()`
  * `client.startSimulation()`
  * `client.findOptimalPath(start, end, verbose)`
  * `client.saveState()`

[cite\_start]**Uso de WebSocket no Cliente:** [cite: 377]

```javascript
await client.connectWebSocket();
client.onMessage('simulation_update', (message) => {
    console.log("Tick:", message.tick);
});
```

-----

## 6\. Integração Frontend

[cite\_start]Exemplo de um componente React (`EcoGridDashboard`) integrando o cliente[cite: 405].

```javascript
import React, { useState, useEffect, useRef } from 'react';
import EcoGridAPIClient from './api-client.js';

const EcoGridDashboard = () => {
    const [nodes, setNodes] = useState([]);
    const [metrics, setMetrics] = useState(null);
    const clientRef = useRef(null);

    useEffect(() => {
        // Inicializar cliente
        clientRef.current = new EcoGridAPIClient();
        
        const loadInitialData = async () => {
            const nodesData = await clientRef.current.getAllNodes();
            setNodes(nodesData);
            const metricsData = await clientRef.current.getMetrics();
            setMetrics(metricsData);
        };

        const setupWebSocket = async () => {
            try {
                await clientRef.current.connectWebSocket();
                clientRef.current.onMessage('state_update', (msg) => {
                    // Lógica de atualização de estado
                });
            } catch (error) {
                console.error('WebSocket não disponível:', error);
                // Fallback para polling
                clientRef.current.startPolling(2000);
            }
        };

        loadInitialData();
        setupWebSocket();

        return () => {
            if(clientRef.current) clientRef.current.disconnectWebSocket();
        };
    }, []);

    // ... Renderização do componente
};

export default EcoGridDashboard;
```

-----

## 7\. Exemplos de Uso

### [cite\_start]Exemplo 1: Simular Cenário de Sobrecarga (Python) [cite: 447]

```python
import asyncio
from api_client import EcoGridAPIClient

async def simulate_overload():
    client = EcoGridAPIClient()
    
    # Iniciar simulação
    await client.start_simulation()
    
    # Aumentar carga no nó 1 progressivamente
    for i in range(10):
        await client.update_node_load(1, 5000 + i * 500)
        await asyncio.sleep(1)
        
    # Verificar métricas
    metrics = await client.get_metrics()
    print(f"Status: {metrics['network_status']}")
    print(f"Nós sobrecarregados: {metrics['overloaded_nodes']}")

asyncio.run(simulate_overload())
```

### [cite\_start]Exemplo 2: Testar Roteamento A\* (JS) [cite: 464]

```javascript
async function testRouting() {
    const client = new EcoGridAPIClient();
    const route = await client.findOptimalPath(1, 201, true);
    
    console.log('Rota encontrada:', route.path); // ex: [1, 10, 101]
    console.log('Perda total:', route.total_loss);
    console.log('Hops:', route.hops);
}
testRouting();
```

-----

## 8\. Troubleshooting

[cite\_start]**Backend não inicia** [cite: 483]

  * *Causa:* Porta 8000 ocupada.
  * *Solução:* Liberar porta (`kill -9 <PID>` no Linux/Mac ou `taskkill` no Windows).

[cite\_start]**CORS Error** [cite: 491]

  * *Erro:* `Access to XMLHttpRequest has been blocked...`
  * *Solução:* O backend já possui configuração de CORS em `main.py` para permitir origens diferentes (ex: Backend em 8000, Frontend em 3000).

[cite\_start]**WebSocket Connection Failed** [cite: 498]

  * [cite\_start]*Solução:* Use o método `client.startPolling(2000)` como fallback caso o WebSocket não consiga conexão[cite: 503].

[cite\_start]**Dados Fora de Sincronização** [cite: 504]

  * [cite\_start]*Solução:* Force um recarregamento completo do estado com `await client.getSimulationState()`[cite: 509].

-----

## Performance e Produção

### [cite\_start]Otimizações Implementadas [cite: 511]

  * **AVL Tree:** Buscas em $O(\log n)$.
  * **B+ Tree:** Persistência eficiente.
  * **Circular Buffer:** Série temporal em $O(1)$.
  * **WebSocket:** Comunicação tempo real com compressão de eventos.

### [cite\_start]Limites [cite: 522]

  * Máx \~10.000 nós.
  * Máx \~100 conexões WebSocket simultâneas.
  * Histórico: Últimos 1M registros.

### [cite\_start]Deploy em Produção [cite: 527]

Recomenda-se usar **Gunicorn** em vez de Uvicorn diretamente:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 api.main:app
```

Utilize um Reverse Proxy (Nginx) para gerenciar as conexões.