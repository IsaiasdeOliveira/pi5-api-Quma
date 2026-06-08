# QumAI - Backend

Este repositório contém a infraestrutura de backend e o motor de Inteligência Artificial do jogador **QumAI**, desenvolvido para o campeonato da disciplina de Projeto Integrador V.

A aplicação foi construída em Python e projetada para oferecer respostas táticas otimizadas em tempo real sob restrições estritas de latência computacional.

## Arquitetura da Aplicação e Endpoints

A arquitetura adota um design *stateless*, garantindo que a API não sofra com vazamentos de memória durante o processamento consecutivo das rodadas de um campeonato em nuvem. 

A comunicação com o motor principal do jogo ocorre por meio de dois endpoints fundamentais:

* **`GET /health`**: Retorna um status HTTP 200 confirmando que a infraestrutura está ativa e pronta para receber partidas.
* **`POST /move`**: Recebe uma estrutura de dados representando o grid $5 \times 5$ atual e delega a árvore de estado para os módulos lógicos de IA, retornando a jogada calculada.

---

## Jogador Inteligente - Estratégia

Para garantir que a QumAI dominasse o grid sob limites de tempo, descartamos algoritmos puramente exaustivos sem função de utilidade e métodos reativos baseados em aprendizado de máquina profundo (como Q-Learning), devido à explosão combinatória do espaço de estados no tabuleiro $5 \times 5$.

Em vez disso, a inteligência foi construída a partir de uma **Arquitetura Heurística Híbrida em 3 Módulos**, integrando os conceitos centrais das disciplinas de Busca Heurística e Otimização.

### 1. Filtro CSP (Problema de Satisfação de Restrições)
A primeira camada do algoritmo atua como um sistema de supressão matemática de estados inválidos. 
A função de geração de movimentos traduz as restrições físicas do jogo (adjacências, proibições de escalar múltiplos níveis simultaneamente, ocupações) em código eficiente $O(N)$. Isso impede que a IA aloque memória ou processe sub-árvores lógicas para posições geometricamente ou logicamente ilegais no tabuleiro, eliminando o gargalo de expansão indiscriminada da árvore de busca na raiz do processo de decisão.

### 2. Motor de Decisão (Minimax com Poda Alpha-Beta)
O núcleo da tática em tempo real. A cada turno que não apresenta uma condição de vitória imediata, a QumAI inicia a geração preditiva dos cenários usando o clássico algoritmo Minimax, explorando nós a uma profundidade predefinida (Depth = 2, calibrado para a latência de requisições web). 

A fim de maximizar essa profundidade, implementamos a **Poda Alpha-Beta**. O motor é capaz de descartar ramificações inteiras da árvore de decisão assim que a matemática prova que elas são inferiores a uma jogada já garantida, economizando massivamente ciclos de CPU. Outra otimização crítica no motor foi a substituição da cópia recursiva do tabuleiro (`copy.deepcopy()`) por uma técnica de *shallow copy* seguida por instanciamentos locais restritos unicamente às peças movimentadas. Essa engenharia reduziu o custo de simulação dos nós-folha da árvore de forma drástica, viabilizando a busca profunda sem o risco de atingir o *timeout* da partida.

### 3. Função de Avaliação Linear
Como a árvore do Minimax atinge o limite temporal em nós-folha (tabuleiros inacabados), a QumAI usa uma Heurística Linear para calcular um "score" indicando a probabilidade de vitória de um estado qualquer:
$V(s) = w_1(Altura) + w_2(Controle de Centro) + w_3(Mobilidade) - w_4(Altura do Oponente)$

Os pesos ($w$) não foram deduzidos empiricamente, mas sim calibrados para forçar a IA a adotar um comportamento metódico:
* `my_height (22.0)`: Prioridade altíssima para verticalização no mapa.
* `opp_height (-28.0)`: Penalidade extrema caso o adversário ganhe altitude. É a diretriz tática primária da QumAI assumir um posicionamento defensivo-agressivo focado em impedir o progresso adversário acima de qualquer outra ação no grid.
* `center_control (11.0)`: Bônus de posicionamento calculado matematicamente a partir da **Distância de Manhattan** em relação às coordenadas centrais do grid. Isso força a IA a buscar a dominância do anel central para controlar as zonas de influência.
* `mobility (1.0)`: Recompensa tática para estados onde o número de opções de ações da QumAI é numericamente superior às restrições do oponente, priorizando tabuleiros que limitam a área de manobra do inimigo.
