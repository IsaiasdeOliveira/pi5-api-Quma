# app/logic.py
import random
import math
import copy
from typing import Optional

from app.schemas import Cell, Position, SetupResponse, PlayerTurnResponse

BOARD_SIZE = 5

# Professores de cada time
TEAM_PROFESSORS = {
    1: ["CLARO", "REY"],       # Turing
    2: ["KARIN", "BEATRIZ"],   # Lovelace
}

# ---------------------------------------------------------
# PESOS DA HEURÍSTICA (Otimizados pelo Algoritmo Genético offline)
# ---------------------------------------------------------
# Estes valores devem ser ajustados pelo seu processo de treinamento GA.
GA_WEIGHTS = {
    "win_move": 10000.0,
    "my_height": 22.28540020874664,
    "opp_height": -27.94907717122248,
    "center_control": 11.498133950334724,
    "mobility": 1.225367536592565              # Bônus por ter muitas opções de jogada (CSP)
}

def adjacent_cells(row: int, col: int) -> list[tuple[int, int]]:
    """Retorna todas as casas vizinhas (incluindo diagonais) dentro do grid."""
    cells = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = row + dr, col + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                cells.append((nr, nc))
    return cells

def find_professor(board: list[list[Cell]], name: str) -> Optional[tuple[int, int]]:
    """Encontra a posição (row, col) de um professor no tabuleiro."""
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c].professor == name:
                return (r, c)
    return None

def choose_setup(board: list[list[Cell]]) -> SetupResponse:
    """Fase de posicionamento: escolhe o centro ou adjacências aleatórias."""
    candidates = [
        (r, c)
        for r in range(BOARD_SIZE)
        for c in range(BOARD_SIZE)
        if board[r][c].level == 0 and board[r][c].professor is None
    ]
    # Tenta priorizar o centro no setup
    center_candidates = [(r, c) for r, c in candidates if 1 <= r <= 3 and 1 <= c <= 3]
    row, col = random.choice(center_candidates if center_candidates else candidates)
    return SetupResponse(row=row, col=col)

# ---------------------------------------------------------
# MÓDULO 1: FILTRO CSP (Satisfação de Restrições)
# ---------------------------------------------------------
def get_legal_moves(board: list[list[Cell]], team_id: int) -> list[PlayerTurnResponse]:
    """Gera todos os movimentos legais para a equipe atual (Filtro CSP)."""
    legal_moves = []
    
    for professor in TEAM_PROFESSORS[team_id]:
        pos = find_professor(board, professor)
        if pos is None:
            continue

        cur_row, cur_col = pos
        cur_level = board[cur_row][cur_col].level

        for dst_row, dst_col in adjacent_cells(cur_row, cur_col):
            dst_cell = board[dst_row][dst_col]

            # Restrições (CSP)
            if dst_cell.professor is not None: continue
            if dst_cell.level == 4: continue
            if dst_cell.level > cur_level + 1: continue

            # Se for vitória imediata (movimento para nível 3)
            if dst_cell.level == 3:
                legal_moves.append(PlayerTurnResponse(
                    professor=professor,
                    move_to=Position(row=dst_row, col=dst_col)
                ))
                continue

            # Movimentos normais que exigem mentoria (construção)
            for men_row, men_col in adjacent_cells(dst_row, dst_col):
                men_cell = board[men_row][men_col]
                is_source = (men_row, men_col) == (cur_row, cur_col)
                
                if (men_cell.professor is None or is_source) and men_cell.level < 4:
                    legal_moves.append(PlayerTurnResponse(
                        professor=professor,
                        move_to=Position(row=dst_row, col=dst_col),
                        mentor_at=Position(row=men_row, col=men_col),
                    ))
                    
    return legal_moves

def apply_move(board: list[list[Cell]], move: PlayerTurnResponse) -> list[list[Cell]]:
    """Simula um movimento em um novo tabuleiro para a árvore Minimax."""
    new_board = copy.deepcopy(board)
    
    # 1. Encontra e remove o professor da posição antiga
    old_pos = find_professor(new_board, move.professor)
    if old_pos:
        new_board[old_pos[0]][old_pos[1]].professor = None
        
    # 2. Move o professor para a nova posição
    new_board[move.move_to.row][move.move_to.col].professor = move.professor
    
    # 3. Aplica a mentoria (constrói um andar), se houver
    if move.mentor_at:
        new_board[move.mentor_at.row][move.mentor_at.col].level += 1
        
    return new_board

# ---------------------------------------------------------
# MÓDULO 3: FUNÇÃO DE AVALIAÇÃO (Treinada pelo Genético)
# ---------------------------------------------------------
def evaluate_board(board: list[list[Cell]], team_id: int, opp_id: int) -> float:
    """Avalia o estado do tabuleiro usando os pesos do Algoritmo Genético."""
    score = 0.0
    
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell = board[r][c]
            if cell.professor is None:
                continue
                
            # Verifica se alguém já venceu
            if cell.level == 3:
                if cell.professor in TEAM_PROFESSORS[team_id]:
                    return GA_WEIGHTS["win_move"]
                else:
                    return -GA_WEIGHTS["win_move"]

            # Aplica pontuação de heurística
            if cell.professor in TEAM_PROFESSORS[team_id]:
                score += cell.level * GA_WEIGHTS["height_score"]
                # Bônus por controle central (distância de Manhattan do centro)
                center_dist = abs(r - 2) + abs(c - 2)
                score += (4 - center_dist) * GA_WEIGHTS["center_control"]
            elif cell.professor in TEAM_PROFESSORS[opp_id]:
                score += cell.level * GA_WEIGHTS["opponent_height"]
                
    # Fator de Mobilidade: Quem tem mais opções de movimento tem vantagem
    score += len(get_legal_moves(board, team_id)) * GA_WEIGHTS["mobility"]
    score -= len(get_legal_moves(board, opp_id)) * GA_WEIGHTS["mobility"]
    
    return score

# ---------------------------------------------------------
# MÓDULO 2: MOTOR MINIMAX COM PODA ALPHA-BETA
# ---------------------------------------------------------
def minimax(board: list[list[Cell]], depth: int, alpha: float, beta: float, 
            is_maximizing: bool, team_id: int, opp_id: int) -> float:
    """Busca em profundidade com Alpha-Beta Pruning."""
    
    # Condição de parada: profundidade limite alcançada
    if depth == 0:
        return evaluate_board(board, team_id, opp_id)
        
    current_team = team_id if is_maximizing else opp_id
    legal_moves = get_legal_moves(board, current_team)
    
    # Se não há movimentos legais, o jogador atual perdeu
    if not legal_moves:
        return -GA_WEIGHTS["win_move"] if is_maximizing else GA_WEIGHTS["win_move"]

    if is_maximizing:
        max_eval = -math.inf
        for move in legal_moves:
            simulated_board = apply_move(board, move)
            
            # Se a jogada simulada garante a vitória instantânea, para de buscar
            if move.mentor_at is None and simulated_board[move.move_to.row][move.move_to.col].level == 3:
                return GA_WEIGHTS["win_move"]
                
            eval_score = minimax(simulated_board, depth - 1, alpha, beta, False, team_id, opp_id)
            max_eval = max(max_eval, eval_score)
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Poda Alpha-Beta
        return max_eval
    else:
        min_eval = math.inf
        for move in legal_moves:
            simulated_board = apply_move(board, move)
            
            if move.mentor_at is None and simulated_board[move.move_to.row][move.move_to.col].level == 3:
                return -GA_WEIGHTS["win_move"]
                
            eval_score = minimax(simulated_board, depth - 1, alpha, beta, True, team_id, opp_id)
            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Poda Alpha-Beta
        return min_eval

def choose_turn(board: list[list[Cell]], team_id: int) -> Optional[PlayerTurnResponse]:
    """
    Decide a melhor jogada usando CSP (Filtro) e Minimax + Alpha-Beta.
    """
    opp_id = 2 if team_id == 1 else 1
    best_move = None
    best_score = -math.inf
    
    # 1. Filtro CSP: Busca todos os nós raiz válidos
    legal_moves = get_legal_moves(board, team_id)
    if not legal_moves:
        return None

    # Verifica primeiro se há um movimento de vitória imediata para economizar processamento
    for move in legal_moves:
        if move.mentor_at is None:  # Jogada de vitória não tem 'mentor_at'
            return move

    # 2. Avaliação de ramos via Minimax com profundidade definida
    # A profundidade (depth) pode ser ajustada. Para grids 5x5, depth 2 ou 3 costuma ter boa performance.
    SEARCH_DEPTH = 2 
    alpha = -math.inf
    beta = math.inf

    for move in legal_moves:
        simulated_board = apply_move(board, move)
        # Inicia a busca assumindo que o próximo turno é do oponente (is_maximizing=False)
        move_score = minimax(simulated_board, SEARCH_DEPTH - 1, alpha, beta, False, team_id, opp_id)
        
        if move_score > best_score:
            best_score = move_score
            best_move = move
            
        alpha = max(alpha, best_score)

    # Se todas as avaliações empatarem, fallback de segurança
    if best_move is None:
        best_move = random.choice(legal_moves)
        
    return best_move