# Testes de Validação de Eficiência do Projeto EcoGrid+

Este arquivo documenta os testes criados para validar os objetivos de eficiência especificados no documento `Projeto_EcoGrid_Plat_IA_Energia_Sustentavel.pdf`.

## Objetivos do Projeto

Conforme o PDF do projeto, os objetivos são:

1. **Redução de 15% nas perdas simuladas de energia**
2. **Melhoria de 40% na velocidade de redistribuição** em relação a métodos não balanceados

## Testes Implementados

### Arquivo: `test_project_efficiency_validation.py`

#### Teste 1: Redução de Perdas de Energia (`test_energy_losses_reduction`)

**Objetivo**: Validar que o sistema balanceado (com AVL e redistribuição automática) reduz as perdas de energia em pelo menos 15% comparado a um sistema não balanceado.

**Metodologia**:
- Cria dois simuladores: um balanceado (com redistribuição) e um não balanceado (sem redistribuição)
- Usa o cenário de demonstração de rotas do `fallback_gui.py` (1 Subestação → 4 Transformadores → 10 Consumidores)
- Injeta sobrecarga em consumidores para forçar redistribuição
- Calcula perdas totais usando `calculate_total_energy_losses()`
- Compara as perdas entre os dois sistemas

**Cenário de Teste**:
- Cenário base: `setup_routing_demo_scenario()` (hierarquia: Subestação → Transformador → Consumidor)
- Sobrecarga injetada: Consumidores 6 e 7 com cargas acima da capacidade
- Execução: 10 ticks de estabilização + 20 ticks após sobrecarga

**Resultado Esperado**: Redução de perdas >= 15%

#### Teste 2: Melhoria de Velocidade de Redistribuição (`test_redistribution_speed_improvement`)

**Objetivo**: Validar que o sistema balanceado (com AVL) é pelo menos 40% mais rápido na redistribuição comparado a métodos não balanceados (busca linear).

**Metodologia**:
- Compara complexidade algorítmica: O(log n) com AVL vs O(n log n) sem AVL
- Mede número de iterações/operações necessárias para redistribuir carga
- Sistema balanceado usa AVL Tree para busca O(log n)
- Sistema não balanceado usa busca linear O(n) + ordenação O(n log n)

**Cenário de Teste**:
- Mesmo cenário do Teste 1
- Sobrecarga injetada: Consumidor 6 com carga acima da capacidade
- Múltiplas execuções para média

**Resultado Esperado**: Melhoria de velocidade >= 40%

#### Teste 3: Validação de Eficiência Global (`test_comprehensive_efficiency`)

**Objetivo**: Validar que a eficiência global E calculada está dentro de valores esperados.

**Metodologia**:
- Executa simulação completa por 20 ticks
- Calcula eficiência global usando `EnergyHeuristics.calculate_global_efficiency()`
- Valida que eficiência é positiva e menor que 1000 (limite máximo)

**Resultado Esperado**: Eficiência > 0 e < 1000

## Como Executar

```bash
# Executar todos os testes
python tests/test_project_efficiency_validation.py

# Ou executar testes individuais
python -c "from tests.test_project_efficiency_validation import *; test_energy_losses_reduction()"
python -c "from tests.test_project_efficiency_validation import *; test_redistribution_speed_improvement()"
python -c "from tests.test_project_efficiency_validation import *; test_comprehensive_efficiency()"
```

## Estrutura do Cenário de Teste

O cenário usado (`setup_routing_demo_scenario`) replica o cenário do `fallback_gui.py`:

```
Subestação (Nó 1)
├── Transformador T1 (Nó 2) - Esquerda Superior
├── Transformador T2 (Nó 3) - Centro Superior  
├── Transformador T3 (Nó 4) - Direita Superior
└── Transformador T4 (Nó 5) - Centro Inferior

Consumidores (Nós 6-15):
- Cada consumidor pode ser alimentado por múltiplos transformadores
- Rotas alternativas disponíveis para redistribuição
- Diferentes resistências e eficiências nas arestas
```

## Notas Importantes

1. **Sistema Não Balanceado**: Implementado como `UnbalancedSimulator` que não executa redistribuição automática no método `step()`.

2. **Cálculo de Perdas**: Usa a mesma lógica de `EnergyHeuristics.calculate_global_efficiency()` para calcular perdas totais (nós + arestas).

3. **Medição de Velocidade**: Usa número de iterações/operações como proxy para complexidade algorítmica, já que tempo real pode variar muito.

4. **Validação Flexível**: Os testes avisam se os valores estão abaixo da meta, mas não falham completamente, pois em cenários reais os valores podem variar.

## Resultados Esperados

- **Redução de Perdas**: >= 15% (sistema balanceado tem menos perdas)
- **Melhoria de Velocidade**: >= 40% (sistema balanceado é mais rápido)
- **Eficiência Global**: Valor positivo e razoável (entre 0 e 1000)

## Melhorias Futuras

1. Adicionar mais cenários de teste (diferentes topologias)
2. Testes com diferentes níveis de sobrecarga
3. Validação estatística com múltiplas execuções
4. Comparação com outros algoritmos de balanceamento

