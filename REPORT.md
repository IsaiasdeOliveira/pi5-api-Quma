# Relatório de Engenharia e Estratégia - QumAI Engine (Backend)

Este relatório detalha a arquitetura interna, as motivações técnicas e a evolução algorítmica do backend da **QumAI**, em conformidade com as exigências da disciplina de Projeto Integrador V.

---

## 1. Estrutura da Aplicação e Decisões Técnicas

O backend foi estruturado com foco em alta concorrência e baixa latência computacional.

* **Escolha do Framework (FastAPI):** Optamos pelo FastAPI devido à sua natureza assíncrona nativa e serialização ultrarrápida via Pydantic. Isso garantiu que o tempo de resposta da nossa API fosse gasto quase inteiramente no cálculo do Minimax, e não no *parsing* do JSON da requisição.
* **Abordagem Stateless:** O servidor não guarda o estado do tabuleiro na memória RAM entre os turnos. Cada requisição `/move` carrega a matriz completa do jogo. A motivação para isso foi criar um sistema resiliente a falhas: se o servidor reiniciar no meio de um campeonato, ele não perde a partida, pois recalcula tudo com base no payload da requisição atual.

---

## 2. Jogador Inteligente - Estratégia

*(Esta seção atende ao requisito obrigatório de explicação do motor lógico)*

A construção do jogador inteligente passou por iterações focadas em resolver o problema da **explosão combinatória**. Num grid $5 \times 5$, as possibilidades de movimento e construção ramificam exponencialmente, tornando inviável uma busca profunda sem otimizações.

### A Evolução do Algoritmo e Otimizações
Inicialmente, nosso bot utilizava a biblioteca padrão `copy.deepcopy()` do Python para simular tabuleiros futuros. Isso gerou um gargalo imenso, fazendo o bot estourar o limite de tempo da requisição web já na Profundidade 2. 
A solução de engenharia foi reescrever a simulação de estado para utilizar cópias rasas (*shallow copies*) e matrizes locais onde apenas a coordenada alterada era reescrita. Essa otimização permitiu que a QumAI alcançasse a **Profundidade 3 (Depth = 3)** com extrema folga térmica no servidor, além de viabilizar a implementação da Poda Alpha-Beta com alta eficiência de corte de ramos inúteis.

### A Filosofia das Heurísticas
A função de avaliação não foi criada com achismos, mas sim calibrada para corrigir fraquezas que a IA apresentou nas primeiras versões:
* Percebemos que o bot perdia partidas por ser muito "ganancioso", tentando subir de nível enquanto o adversário o encurralava. 
* A solução foi criar o **Gatilho de Interceptação Extrema (-800.0)**. Em vez de calcular apenas vitórias, ensinamos o Minimax a sentir "medo" do adversário no nível 2. A matemática força a QumAI a usar seus blocos para tampar o rival com o nível 4 antes de tentar sua própria vitória.
* Adicionamos a **Muralha Central** porque peças nas bordas iniciais perdiam 50% de sua mobilidade. A heurística de controle de centro garante que a QumAI comece o jogo disputando o meio do tabuleiro.

---
### Metodologia de Testes, Resultados e Upgrades Pós-Campeonato

O processo de validação e evolução da QumAI ocorreu em três fases fundamentais:

1. **Testes Locais e Validação Lógica:** Inicialmente, a IA foi testada localmente contra agentes randômicos e contra versões anteriores de si mesma (o bot QumAI desatualizado). O objetivo foi garantir que os nossos 3 pilares lógicos (Filtro CSP, Minimax e Heurísticas Lineares) funcionassem em perfeita harmonia, sem realizar jogadas ilegais ou estourar o limite de tempo.
2. **Homologação na Arena Oficial (Campeonato):** Colocamos o bot em produção contra os concorrentes desenvolvidos pelas outras equipes. Durante os confrontos oficiais, notamos que a nossa IA teve dificuldades contra os bots mais avançados da tabela. Embora não tenhamos conseguido vencê-los durante o tempo do torneio, jogar contra lógicas superiores foi essencial para mapear nossas fraquezas táticas.
3. **Análise e Upgrade Final Pós-Campeonato:** O desenvolvimento não parou no fim do torneio. Utilizamos as derrotas como base de estudo para um *upgrade* direto na nossa lógica base, refinando os pesos matemáticos finais e a agressividade defensiva do Minimax. O resultado desta refatoração (a versão definitiva apresentada neste repositório) gerou uma nova matriz de resultados muito mais competitiva:
   * **Superação e Vitórias:** Passamos a vencer de forma consistente bots que antes nos derrotavam, como o `apatetado`,  o bot `Nome completo?` e o `Carille`.
   * **Equilíbrio Tático (50/50):** Alcançamos um patamar de igualdade contra lógicas de altíssimo nível, como o bot `supla` , estabelecendo uma taxa de vitória equilibrada onde alternamos vitórias e derrotas partida a partida, jogando de igual para igual.
   * **Limitações Atuais:** Com total transparência acadêmica, validamos que nossa heurística atual ainda não é capaz de superar os bots `Boboca_v2` e `Gepeto X`. Isso evidencia o teto computacional da nossa atual função de avaliação estática, deixando um excelente ponto de partida mapeado para futuros trabalhos com aprendizado de máquina.

---

## 4. Conformidade com os Requisitos da API

O servidor atende a todos os contratos estipulados:
* **Endpoint de Health (`GET /health`):** Desenvolvido para retornar o status da aplicação para orquestradores.
* **Endpoint de Move (`POST /move`):** Rota validada que engole a interface do jogo (matriz e informações do turno) e cospe a ação exata no formato `{"move": {...}, "mentor": {...}}`.
