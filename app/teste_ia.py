# app/teste_ia.py
import random
import json
import app.logic as logic
from app.logic import choose_turn, apply_move, get_legal_moves
from app.schemas import Cell, PlayerTurnResponse

# =======================================================
# 1. A ARENA DE SIMULAÇÃO (Minimax vs Minimax)
# =======================================================
def gerar_tabuleiro_inicial():
    return [[Cell(level=0, professor=None) for _ in range(5)] for _ in range(5)]

def simular_partida():
    board = gerar_tabuleiro_inicial()
    
    board[0][0].professor = "CLARO"
    board[0][4].professor = "REY"
    board[4][0].professor = "KARIN"
    board[4][4].professor = "BEATRIZ"
    
    # Guarda os pesos que o treinador está avaliando (Time 1)
    pesos_treinados = logic.New_WEIGHTS.copy()
    
    # Define os pesos do Rival Inteligente de referência (Time 2)
    pesos_rivais_base = {
        "win_move": 10000.0,
        "my_height": 40.0,
        "opp_height": -18.0,
        "center_control": 15.0,
        "mobility": 2.0,
        "block_enemy": 0.0,      # O rival antigo não joga com anti-jogo
        "trap_professor": 0.0    
    }
    
    turnos = 0
    max_turnos = 150
    
    while turnos < max_turnos:
        # 🤖 TURNO DA QUMAI (Time 1 - Inteligência Nova/Mutante)
        logic.New_WEIGHTS = pesos_treinados
        jogada_qumai = choose_turn(board, team_id=1)
        if not jogada_qumai: 
            return False, turnos 
        
        board = apply_move(board, jogada_qumai)
        turnos += 1
        
        pos = jogada_qumai.move_to
        if board[pos.row][pos.col].level == 3 and board[pos.row][pos.col].professor in ["CLARO", "REY"]:
            return True, turnos
            
        # 🧠 TURNO DO RIVAL INTELIGENTE (Time 2 - Minimax Antigo)
        logic.New_WEIGHTS = pesos_rivais_base 
        jogada_rival = choose_turn(board, team_id=2)
        if not jogada_rival: 
            logic.New_WEIGHTS = pesos_treinados
            return True, turnos 
            
        board = apply_move(board, jogada_rival)
        turnos += 1
        
        pos_r = jogada_rival.move_to
        if board[pos_r.row][pos_r.col].level == 3 and board[pos_r.row][pos_r.col].professor in ["KARIN", "BEATRIZ"]:
            logic.New_WEIGHTS = pesos_treinados
            return False, turnos
            
    logic.New_WEIGHTS = pesos_treinados
    return False, turnos


# =======================================================
# 2. O MOTOR DE MACHINE LEARNING (Hill Climbing)
# =======================================================
# IMPORTANTE: Mude para 500 quando rodar no Colab!
N_PARTIDAS_POR_TESTE = 100  
GERACOES = 10  

def avaliar_geracao(pesos_teste):
    logic.New_WEIGHTS = pesos_teste 
    vitorias = 0
    total_turnos = 0
    
    for _ in range(N_PARTIDAS_POR_TESTE):
        venceu, n_turnos = simular_partida()
        if venceu:
            vitorias += 1
            total_turnos += n_turnos
            
    taxa_vitoria = (vitorias / N_PARTIDAS_POR_TESTE) * 100
    media_turnos = total_turnos / vitorias if vitorias > 0 else 999
    
    return taxa_vitoria, media_turnos

if __name__ == "__main__":
    print("🧠 Iniciando Treinamento e Simulação de IA...")
    
    melhores_pesos = logic.carregar_pesos()
    
    print(f"📊 Avaliando a inteligência base ({N_PARTIDAS_POR_TESTE} partidas)...")
    melhor_taxa, melhor_media = avaliar_geracao(melhores_pesos)
    print(f"🏆 Recorde Atual -> Vitória: {melhor_taxa:.1f}% | Média: {melhor_media:.2f} turnos\n")

    for geracao in range(1, GERACOES + 1):
        print(f"🧬 Geração {geracao}/{GERACOES}...")
        
        pesos_mutantes = melhores_pesos.copy()
        for chave in pesos_mutantes:
            if chave != "win_move": 
                variacao = random.uniform(0.85, 1.15) 
                pesos_mutantes[chave] = round(pesos_mutantes[chave] * variacao, 2)
        
        taxa_mutante, media_mutante = avaliar_geracao(pesos_mutantes)
        
        if taxa_mutante >= (melhor_taxa - 1.0) and media_mutante < melhor_media:
            print(f"   ✅ EVOLUÇÃO! Média caiu de {melhor_media:.2f} para {media_mutante:.2f} turnos.")
            melhor_taxa = taxa_mutante
            melhor_media = media_mutante
            melhores_pesos = pesos_mutantes.copy()
            
            with open("melhores_pesos.json", "w") as f:
                json.dump(melhores_pesos, f, indent=4)
            print(f"   💾 Arquivo 'melhores_pesos.json' atualizado!")
        else:
            print(f"   ❌ Mutante ruim (Média: {media_mutante:.2f}). Descartado.")

    print("\n🏁 Treinamento concluído!")