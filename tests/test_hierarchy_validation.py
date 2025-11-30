"""
Teste para validar que a hierarquia está sendo respeitada no balanceamento.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models.graph import EcoGridGraph
from src.core.models.node import NodeType
from src.core.structures.avl_tree import AVLTree
from src.core.algorithms.balancing import LoadBalancer

def test_consumer_cannot_transfer_to_transformer():
    """Testa que consumidor NÃO pode transferir para transformador."""
    print("--- Teste: Consumidor -> Transformador (DEVE BLOQUEAR) ---")
    
    graph = EcoGridGraph()
    avl = AVLTree()
    
    # Cria transformador
    transformer = graph.add_node(1, NodeType.TRANSFORMER, 5000.0, parent_id=None)
    avl.insert(1, transformer)
    
    # Cria consumidor (filho do transformador)
    consumer = graph.add_node(2, NodeType.CONSUMER, 1000.0, parent_id=1)
    avl.insert(2, consumer)
    
    # Conecta fisicamente
    graph.add_edge(1, 2, 1.0, 0.1)
    
    # Inicializa balanceador
    balancer = LoadBalancer(graph, avl)
    
    # Tenta transferir de consumidor para transformador
    can_transfer = balancer._can_transfer_to(consumer, transformer)
    
    print(f"Consumidor (ID:{consumer.id}) -> Transformador (ID:{transformer.id}): {can_transfer}")
    
    if not can_transfer:
        print(">> SUCESSO: Transferência bloqueada corretamente!")
        return True
    else:
        print(">> FALHA: Transferência deveria ser bloqueada!")
        return False

def test_consumer_cannot_transfer_to_consumer():
    """Testa que consumidor NÃO PODE transferir para outro consumidor (removido)."""
    print("\n--- Teste: Consumidor -> Consumidor (DEVE BLOQUEAR) ---")
    
    graph = EcoGridGraph()
    avl = AVLTree()
    
    # Cria transformador
    transformer = graph.add_node(1, NodeType.TRANSFORMER, 5000.0, parent_id=None)
    avl.insert(1, transformer)
    
    # Cria dois consumidores (mesmo pai)
    consumer1 = graph.add_node(2, NodeType.CONSUMER, 1000.0, parent_id=1)
    consumer2 = graph.add_node(3, NodeType.CONSUMER, 1000.0, parent_id=1)
    avl.insert(2, consumer1)
    avl.insert(3, consumer2)
    
    # Conecta ao transformador
    graph.add_edge(1, 2, 1.0, 0.1)
    graph.add_edge(1, 3, 1.0, 0.1)
    # Conecta consumidores entre si (rede secundária)
    graph.add_edge(2, 3, 0.5, 0.2)
    
    # Inicializa balanceador
    balancer = LoadBalancer(graph, avl)
    
    # Tenta transferir de consumidor para consumidor
    can_transfer = balancer._can_transfer_to(consumer1, consumer2)
    
    print(f"Consumidor (ID:{consumer1.id}) -> Consumidor (ID:{consumer2.id}): {can_transfer}")
    
    if not can_transfer:
        print(">> SUCESSO: Transferência bloqueada corretamente!")
        return True
    else:
        print(">> FALHA: Transferência deveria ser bloqueada!")
        return False

def test_transformer_cannot_transfer_to_substation():
    """Testa que transformador NÃO pode transferir para subestação."""
    print("\n--- Teste: Transformador -> Subestacao (DEVE BLOQUEAR) ---")
    
    graph = EcoGridGraph()
    avl = AVLTree()
    
    # Cria subestação
    substation = graph.add_node(1, NodeType.SUBSTATION, 10000.0, parent_id=None)
    avl.insert(1, substation)
    
    # Cria transformador (filho da subestação)
    transformer = graph.add_node(2, NodeType.TRANSFORMER, 5000.0, parent_id=1)
    avl.insert(2, transformer)
    
    # Conecta fisicamente
    graph.add_edge(1, 2, 10.0, 0.01)
    
    # Inicializa balanceador
    balancer = LoadBalancer(graph, avl)
    
    # Tenta transferir de transformador para subestação
    can_transfer = balancer._can_transfer_to(transformer, substation)
    
    print(f"Transformador (ID:{transformer.id}) -> Subestacao (ID:{substation.id}): {can_transfer}")
    
    if not can_transfer:
        print(">> SUCESSO: Transferência bloqueada corretamente!")
        return True
    else:
        print(">> FALHA: Transferência deveria ser bloqueada!")
        return False

def test_transformer_cannot_transfer_to_consumer():
    """Testa que transformador NÃO pode transferir para consumidor."""
    print("\n--- Teste: Transformador -> Consumidor (DEVE BLOQUEAR) ---")
    
    graph = EcoGridGraph()
    avl = AVLTree()
    
    # Cria transformador
    transformer = graph.add_node(1, NodeType.TRANSFORMER, 5000.0, parent_id=None)
    avl.insert(1, transformer)
    
    # Cria consumidor (filho do transformador)
    consumer = graph.add_node(2, NodeType.CONSUMER, 1000.0, parent_id=1)
    avl.insert(2, consumer)
    
    # Conecta fisicamente
    graph.add_edge(1, 2, 1.0, 0.1)
    
    # Inicializa balanceador
    balancer = LoadBalancer(graph, avl)
    
    # Tenta transferir de transformador para consumidor
    can_transfer = balancer._can_transfer_to(transformer, consumer)
    
    print(f"Transformador (ID:{transformer.id}) -> Consumidor (ID:{consumer.id}): {can_transfer}")
    
    if not can_transfer:
        print(">> SUCESSO: Transferência bloqueada corretamente!")
        return True
    else:
        print(">> FALHA: Transferência deveria ser bloqueada!")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTES DE VALIDAÇÃO DE HIERARQUIA")
    print("=" * 60)
    
    results = []
    results.append(("Consumidor -> Transformador (bloqueado)", test_consumer_cannot_transfer_to_transformer()))
    results.append(("Consumidor -> Consumidor (bloqueado)", test_consumer_cannot_transfer_to_consumer()))
    results.append(("Transformador -> Subestacao (bloqueado)", test_transformer_cannot_transfer_to_substation()))
    results.append(("Transformador -> Consumidor (bloqueado)", test_transformer_cannot_transfer_to_consumer()))
    
    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    for name, passed in results:
        status = "PASSOU" if passed else "FALHOU"
        print(f"  {name:50s}: {status}")

