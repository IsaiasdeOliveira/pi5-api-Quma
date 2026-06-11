import random
import math
import json
import os
from typing import Optional

from app.schemas import Cell, Position, SetupResponse, PlayerTurnResponse

BOARD_SIZE = 5

# Professores de cada time
TEAM_PROFESSORS = {
    1: ["CLARO", "REY"],       # Turing
    2: ["KARIN", "BEATRIZ"],   # Lovelace
}

# Pesos padrão da Função de Avaliação (Plano B caso o arquivo treinado não exista)
WEIGHTS = {
    "win_move": 10000.0,
    "my_height": 35.0,         
    "opp_height": -35.0,       # Respeito absoluto ao avanço inimigo
    "center_control": 15.0,    
    "mobility": 15.0           # Aumentado para valorizar o controle de espaço livre
}

def carregar_pesos():
    """Procura o cérebro treinado. Se não achar, usa o padrão."""
    caminho = "melhores_pesos.json" 
    if os.path.exists(caminho):
        with open(caminho, "r") as f:
            return json.load(f)
    return WEIGHTS.copy()

# Salva os pesos treinados para o próximo confronto
New_WEIGHTS = carregar_pesos()

# =========================================================
# MÓDULO 1: FILTRO CSP (Satisfação de Restrições)
# =========================================================
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
    center_candidates = [(r, c) for r, c in candidates if 1 <= r <= 3 and 1 <= c <= 3]
    row, col = random.choice(center_candidates if center_candidates else candidates)
    return SetupResponse(row=row, col=col)

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

            if dst_cell.professor is not None: continue
            if dst_cell.level == 4: continue
            if dst_cell.level > cur_level + 1: continue

            if dst_cell.level == 3:
                legal_moves.append(PlayerTurnResponse(
                    professor=professor,
                    move_to=Position(row=dst_row, col=dst_col)
                ))
                continue

            for men_row, men_col in adjacent_cells(dst_row, dst_col):
                men_cell = board[men_row][men_col]
                is_source = (men_row, men_col) == (cur_row, cur_col)
                
                if (men_cell.professor is None or is_source) and men_cell.level < 4:
                    legal_moves.append(PlayerTurnResponse(
                        professor=professor,
                        move_to=Position(row=dst_row, col=dst_col),
                        mentor_at=Position(row=men_row, col=men_col)
                    ))
                    
    return legal_moves

def _calcular_mobilidade_posicional(board: list[list[Cell]], posicoes: list[tuple[int, int, int]]) -> int:
    """Otimização Extrema: Conta movimentos legais direto das posições em cache, sem escanear o tabuleiro."""
    count = 0
    for cur_row, cur_col, cur_level in posicoes:
        for dst_row, dst_col in adjacent_cells(cur_row, cur_col):
            dst_cell = board[dst_row][dst_col]
            if dst_cell.professor is not None or dst_cell.level == 4 or dst_cell.level > cur_level + 1:
                continue

            if dst_cell.level == 3:
                count += 1
                continue

            for men_row, men_col in adjacent_cells(dst_row, dst_col):
                men_cell = board[men_row][men_col]
                is_source = (men_row, men_col) == (cur_row, cur_col)
                if (men_cell.professor is None or is_source) and men_cell.level < 4:
                    count += 1
    return count

def apply_move(board: list[list[Cell]], move: PlayerTurnResponse) -> list[list[Cell]]:
    """Simula um movimento via reatribuição explícita."""
    new_board = [row[:] for row in board] 

    old_pos = find_professor(board, move.professor)
    if old_pos:
        o_r, o_c = old_pos
        new_board[o_r][o_c] = Cell(level=board[o_r][o_c].level, professor=None)

    n_r, n_c = move.move_to.row, move.move_to.col
    new_board[n_r][n_c] = Cell(level=board[n_r][n_c].level, professor=move.professor)

    if move.mentor_at:
        m_r, m_c = move.mentor_at.row, move.mentor_at.col
        curr_prof = new_board[m_r][m_c].professor
        new_board[m_r][m_c] = Cell(level=board[m_r][m_c].level + 1, professor=curr_prof)

    return new_board

# =========================================================
# MÓDULO 2: AVALIAÇÃO DE ESTADO (Tática Anti-Sufocamento e Anti-Camping)
# =========================================================
def evaluate_board(board: list[list[Cell]], team_id: int, opp_id: int) -> float:
    score = 0.0
    my_profs = []
    opp_profs = []

    # 1. Coleta posições e avalia a altura base das peças (Varredura Única)
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell = board[r][c]
            if cell.professor is None:
                continue

            # Condição de Vitória Matemática Imediata
            if cell.level == 3:
                return 10000.0 if cell.professor in TEAM_PROFESSORS[team_id] else -10000.0

            if cell.professor in TEAM_PROFESSORS[team_id]:
                my_profs.append((r, c, cell.level))
                if cell.level == 1: score += 40.0
                elif cell.level == 2: score += 150.0
                
                # Controle de centro
                center_dist = abs(r - 2) + abs(c - 2)
                score += (4 - center_dist) * 5.0

            elif cell.professor in TEAM_PROFESSORS[opp_id]:
                opp_profs.append((r, c, cell.level))
                if cell.level == 1: score -= 50.0
                elif cell.level == 2: score -= 400.0

    # 2. MARCAÇÃO HOMEM A HOMEM (Antídoto contra Encastelamento do Boboca_v2)
    for o_r, o_c, o_lvl in opp_profs:
        if o_lvl >= 1 and my_profs:
            min_dist = min(max(abs(m_r - o_r), abs(m_c - o_c)) for m_r, m_c, m_lvl in my_profs)
            
            if min_dist > 1:
                # Se o inimigo tentar erguer torres nos cantos/bordas, caçamos agressivamente
                if o_r in [0, 4] or o_c in [0, 4]:
                    score -= (min_dist * 350.0 * o_lvl)
                else:
                    score -= (min_dist * 100.0 * o_lvl)

    # 3. Visão de Futuro (Posicionamento ao redor para subida própria)
    for m_r, m_c, m_lvl in my_profs:
         for nr, nc in adjacent_cells(m_r, m_c):
            adj = board[nr][nc]
            if adj.professor is None and adj.level <= m_lvl + 1 and adj.level < 4:
                score += (adj.level * 10.0)

    # 4. DETECTOR DE CLAUSTROFOBIA / ANTI-SUFOCAMENTO (Contra Supla, Carille e ComFome)
    for m_r, m_c, m_lvl in my_profs:
        rotas_fuga = 0
        for nr, nc in adjacent_cells(m_r, m_c):
            adj_cell = board[nr][nc]
            if adj_cell.level < 4 and adj_cell.professor is None:
                rotas_fuga += 1
        
        # Penalidade violenta se o inimigo reduzir nossas saídas para 1 ou nenhuma
        if rotas_fuga <= 1:
            score -= 4500.0

    # 5. Diferencial de Mobilidade Otimizado (Sem dar varredura extra no grid)
    meus_movimentos = _calcular_mobilidade_posicional(board, my_profs)
    movimentos_adversarios = _calcular_mobilidade_posicional(board, opp_profs)
    score += (meus_movimentos - movimentos_adversarios) * New_WEIGHTS["mobility"]

    return score

# =========================================================
# MÓDULO 3: MOTOR MINIMAX (Com Pressão de Tempo)
# =========================================================
def minimax(board: list[list[Cell]], depth: int, alpha: float, beta: float, is_maximizing: bool, team_id: int, opp_id: int) -> float:
    """Busca em profundidade com Alpha-Beta Pruning."""
    if depth == 0:
        return evaluate_board(board, team_id, opp_id)

    current_team = team_id if is_maximizing else opp_id
    legal_moves = get_legal_moves(board, current_team)
    
    if not legal_moves:
        return -New_WEIGHTS["win_move"] if is_maximizing else New_WEIGHTS["win_move"]

    if is_maximizing:
        max_eval = -math.inf
        for move in legal_moves:
            simulated_board = apply_move(board, move)
            if move.mentor_at is None and simulated_board[move.move_to.row][move.move_to.col].level == 3:
                return New_WEIGHTS["win_move"] + (depth * 1000)
                
            eval_score = minimax(simulated_board, depth - 1, alpha, beta, False, team_id, opp_id)
            max_eval = max(max_eval, eval_score)
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = math.inf
        for move in legal_moves:
            simulated_board = apply_move(board, move)
            if move.mentor_at is None and simulated_board[move.move_to.row][move.move_to.col].level == 3:
                return -New_WEIGHTS["win_move"] - (depth * 1000)
                
            eval_score = minimax(simulated_board, depth - 1, alpha, beta, True, team_id, opp_id)
            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)
            if beta <= alpha:
                break
        return min_eval

def choose_turn(board: list[list[Cell]], team_id: int) -> Optional[PlayerTurnResponse]:
    """Decide a melhor jogada usando CSP e Minimax de Profundidade 3 Otimizado."""
    opp_id = 2 if team_id == 1 else 1
    legal_moves = get_legal_moves(board, team_id)
    if not legal_moves:
        return None

    for move in legal_moves:
        if move.mentor_at is None:
            return move

    # Ordenação de jogadas para maximizar a velocidade da Poda Alpha-Beta
    legal_moves.sort(key=lambda m: board[m.move_to.row][m.move_to.col].level, reverse=True)

    # 🚀 PROFUNDIDADE ATUALIZADA PARA 3: Graças à otimização da mobilidade, a IA enxerga muito mais longe
    SEARCH_DEPTH = 3 
    best_move = None
    best_score = -math.inf
    alpha = -math.inf
    beta = math.inf

    for move in legal_moves:
        simulated_board = apply_move(board, move)
        move_score = minimax(simulated_board, SEARCH_DEPTH - 1, alpha, beta, False, team_id, opp_id)
        if move_score > best_score:
            best_score = move_score
            best_move = move
        alpha = max(alpha, best_score)

    return best_move if best_move else random.choice(legal_moves)