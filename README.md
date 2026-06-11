# QumAI - Backend

Este repositório contém a infraestrutura de backend e o motor de Inteligência Artificial do jogador **QumAI**, desenvolvido para o campeonato da disciplina de Projeto Integrador V.

A aplicação foi construída em Python e projetada para oferecer respostas táticas otimizadas em tempo real sob restrições estritas de latência computacional.

---

##  Como Executar o Projeto Localmente

Para iniciar o servidor da IA em sua máquina, siga os passos abaixo:

1. Certifique-se de ter o **Python 3.10+** instalado.
2. Clone este repositório e navegue até a pasta raiz.
3. Instale as dependências executando:
   ```bash
   pip install -r requirements.txt
   ```
4. Inicie o servidor FastAPI através do Uvicorn:
    ```bash
   uvicorn main:app --reload
   ```
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
O núcleo da tática em tempo real. A cada turno que não apresenta uma condição de vitória imediata, a QumAI inicia a geração preditiva dos cenários usando o clássico algoritmo Minimax, explorando nós a uma profundidade ampliada (Depth = 3), calibrada para enxergar armadilhas futuras sem estourar o limite de tempo web.

A fim de maximizar essa profundidade, implementamos a Poda Alpha-Beta. O motor é capaz de descartar ramificações inteiras da árvore de decisão assim que a matemática prova que elas são inferiores a uma jogada já garantida, economizando massivamente ciclos de CPU. Outra otimização crítica foi a substituição da cópia recursiva profunda por reatribuições matriciais restritas e um cache de mobilidade posicional. Essa engenharia reduziu o custo de simulação dos nós-folha de forma drástica, viabilizando a busca profunda.

### 3. Função de Avaliação Linear
Como a árvore do Minimax atinge o limite temporal em nós-folha (tabuleiros inacabados), a QumAI usa uma Heurística Linear para calcular um "score" indicando a probabilidade de vitória de um estado qualquer. Os pesos foram calibrados no servidor oficial para forçar um comportamento de dominação territorial:

* `Autonomia de Ataque (+350.0)`: Prioridade altíssima para verticalização no mapa. Recompensa a subida bem-sucedida dos nossos professores para o nível 2.

* `Gatilho de Interceptação Extrema (-800.0)`: Penalidade drástica caso o adversário ameace subir. Isso força o motor a abandonar planos de corrida e priorizar o bloqueio imediato do rival com blocos de nível 4, inutilizando a torre inimiga.

* `Controle de Centro Agressivo (12.0)`: Bônus de posicionamento calculado matematicamente a partir da Distância de Manhattan. Isso atrai as peças para o centro do grid nos turnos iniciais, sufocando o espaço de manobra do inimigo.

* `Detector de Claustrofobia Regulado (-600.0)`: Penalidade ativada apenas em casos de encurralamentos reais por paredes estruturais, mantendo a agressividade da IA nas bordas livres do mapa.

* `Diferencial de Mobilidade (5.0)`: Recompensa tática para estados onde o número de movimentos legais da QumAI é numericamente superior às opções do oponente.
  
## Documentação Completa e Relatório

Para uma análise aprofundada dos resultados práticos desses algoritmos, da nossa metodologia de testes na arena oficial e de como alcançamos a marca de estabilidade contra os bots líderes do campeonato, consulte o arquivo **[REPORT.md](./REPORT.md)** na raiz deste repositório.

