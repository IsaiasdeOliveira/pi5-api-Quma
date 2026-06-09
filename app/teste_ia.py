# testar_IA.py
import random
from app.logic import choose_turn, apply_move, get_legal_moves
from app.schemas import Cell, PlayerTurnResponse

def gerar_tabuleiro_inicial():
    return [[Cell(level=0, professor=None) for _ in range(5)] for _ in range(5)]

def simular_partida():
    board = gerar_tabuleiro_inicial()
    
    # Setup manual simplificado para o teste
    board[0][0].professor = "CLARO"
    board[0][4].professor = "REY"
    board[4][0].professor = "KARIN"
    board[4][4].professor = "BEATRIZ"
    
    turnos = 0
    max_turnos = 150 # Trava de segurança para loops infinitos
    
    while turnos < max_turnos:
        # Turno da QumAI (Time 1)
        jogada_qumai = choose_turn(board, team_id=1)
        if not jogada_qumai: 
            return False, turnos # QumAI ficou sem movimentos (Derrota)
        
        board = apply_move(board, jogada_qumai)
        turnos += 1
        
        # Verifica se a QumAI alcançou o nível 3
        pos = jogada_qumai.move_to
        if board[pos.row][pos.col].level == 3 and board[pos.row][pos.col].professor in ["CLARO", "REY"]:
            return True, turnos # Vitória da QumAI
            
        # Turno do Bot Randômico (Time 2)
        jogadas_rivais = get_legal_moves(board, team_id=2)
        if not jogadas_rivais: 
            return True, turnos # Rival ficou sem movimentos (Vitória)
            
        jogada_rival = random.choice(jogadas_rivais)
        board = apply_move(board, jogada_rival)
        turnos += 1
        
        # Verifica se o rival venceu
        pos_r = jogada_rival.move_to
        if board[pos_r.row][pos_r.col].level == 3 and board[pos_r.row][pos_r.col].professor in ["KARIN", "BEATRIZ"]:
            return False, turnos
            
    return False, turnos

if __name__ == "__main__":
    N_PARTIDAS = 500
    vitorias = 0
    total_turnos = 0
    
    print(f"Iniciando simulação de {N_PARTIDAS} partidas locais...")
    for _ in range(N_PARTIDAS):
        venceu, n_turnos = simular_partida()
        if venceu:
            vitorias += 1
            total_turnos += n_turnos
            
    taxa_vitoria = (vitorias / N_PARTIDAS) * 100
    media_turnos = total_turnos / vitorias if vitorias > 0 else 0
    
    print("\n================ RESULTADOS ================")
    print(f"Taxa de Vitória: {taxa_vitoria:.2f}% (Esperado: 100%)")
    print(f"Média de Turnos para Vencer: {media_turnos:.1f} turnos")
    print("============================================")