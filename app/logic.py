# app/logic.py
import random
from typing import Optional

from app.schemas import Cell, Position, SetupResponse, PlayerTurnResponse

BOARD_SIZE = 5

TEAM_PROFESSORS = {
    1: ["CLARO", "REY"],       # Turing
    2: ["KARIN", "BEATRIZ"],   # Lovelace
}

QML_WEIGHTS = {
    "win_move": 10000,
    "my_height": 22,        # Arredondado de 22.28
    "opp_height": -28,      # Arredondado de -27.94
    "center_control": 11,   # Arredondado de 11.49
    "mobility": 1           # Arredondado de 1.22
}

# =========================================================
# MÓDULO 1: FILTRO CSP (Satisfação de Restrições)
# =========================================================
def adjacent_cells(row: int, col: int) -> list[tuple[int, int]]:
    cells = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0: continue
            nr, nc = row + dr, col + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                cells.append((nr, nc))
    return cells

def find_professor(board: list[list[Cell]], name: str) -> Optional[tuple[int, int]]:
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c].professor == name:
                return (r, c)
    return None

def choose_setup(board: list[list[Cell]]) -> SetupResponse:
    candidates = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) 
                  if board[r][c].level == 0 and board[r][c].professor is None]
    center_candidates = [(r, c) for r, c in candidates if 1 <= r <= 3 and 1 <= c <= 3]
    row, col = random.choice(center_candidates if center_candidates else candidates)
    return SetupResponse(row=row, col=col)

def get_legal_moves(board: list[list[Cell]], team_id: int) -> list[PlayerTurnResponse]:
    legal_moves = []
    for professor in TEAM_PROFESSORS[team_id]:
        pos = find_professor(board, professor)
        if pos is None: continue

        cur_row, cur_col = pos
        cur_level = board[cur_row][cur_col].level

        for dst_row, dst_col in adjacent_cells(cur_row, cur_col):
            dst_cell = board[dst_row][dst_col]

            if dst_cell.professor is not None: continue
            if dst_cell.level == 4: continue
            if dst_cell.level > cur_level + 1: continue

            if dst_cell.level == 3:
                legal_moves.append(PlayerTurnResponse(professor=professor, move_to=Position(row=dst_row, col=dst_col)))
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


# NOVO: Contador veloz que não usa Pydantic. Salva MUITA memória!
def count_legal_moves(board: list[list[Cell]], team_id: int) -> int:
    count = 0
    for professor in TEAM_PROFESSORS[team_id]:
        pos = find_professor(board, professor)
        if pos is None: continue
        cur_row, cur_col = pos
        cur_level = board[cur_row][cur_col].level

        for dst_row, dst_col in adjacent_cells(cur_row, cur_col):
            dst_cell = board[dst_row][dst_col]
            if dst_cell.professor is not None: continue
            if dst_cell.level == 4: continue
            if dst_cell.level > cur_level + 1: continue

            if dst_cell.level == 3:
                count += 1
                continue

            for men_row, men_col in adjacent_cells(dst_row, dst_col):
                men_cell = board[men_row][men_col]
                is_source = (men_row, men_col) == (cur_row, cur_col)
                if (men_cell.professor is None or is_source) and men_cell.level < 4:
                    count += 1
    return count

# NOVO: Criador de tabuleiro sem Deepcopy. É 100 vezes mais rápido!
def apply_move(board: list[list[Cell]], move: PlayerTurnResponse) -> list[list[Cell]]:
    new_board = [row[:] for row in board] 
    
    old_pos = find_professor(board, move.professor)
    if old_pos:
        o_r, o_c = old_pos
        new_board[o_r][o_c] = Cell(level=board[o_r][o_c].level, professor=None)
        
    n_r, n_c = move.move_to.row, move.move_to.col
    new_board[n_r][n_c] = Cell(level=board[n_r][n_c].level, professor=move.professor)
    
    if move.mentor_at:
        m_r, m_c = move.mentor_at.row, move.mentor_at.col
        curr_level = new_board[m_r][m_c].level
        curr_prof = new_board[m_r][m_c].professor
        new_board[m_r][m_c] = Cell(level=curr_level + 1, professor=curr_prof)
        
    return new_board


# =========================================================
# MÓDULO 2: AVALIAÇÃO DE ESTADO
# =========================================================
def evaluate_board_classic(board: list[list[Cell]], team_id: int, opp_id: int) -> int:
    score = 0
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell = board[r][c]
            if cell.professor is None: continue
                
            if cell.level == 3:
                return QML_WEIGHTS["win_move"] if cell.professor in TEAM_PROFESSORS[team_id] else -QML_WEIGHTS["win_move"]

            if cell.professor in TEAM_PROFESSORS[team_id]:
                score += cell.level * QML_WEIGHTS["my_height"]
                score += (4 - (abs(r - 2) + abs(c - 2))) * QML_WEIGHTS["center_control"]
            elif cell.professor in TEAM_PROFESSORS[opp_id]:
                score += cell.level * QML_WEIGHTS["opp_height"]
                
    score += (count_legal_moves(board, team_id) - count_legal_moves(board, opp_id)) * QML_WEIGHTS["mobility"]
    return score


# =========================================================
# MÓDULO 3: MOTOR MINIMAX
# =========================================================
def minimax(board: list[list[Cell]], depth: int, alpha: int, beta: int, is_maximizing: bool, team_id: int, opp_id: int) -> int:
    if depth == 0:
        return evaluate_board_classic(board, team_id, opp_id)
        
    legal_moves = get_legal_moves(board, team_id if is_maximizing else opp_id)
    if not legal_moves:
        return -QML_WEIGHTS["win_move"] if is_maximizing else QML_WEIGHTS["win_move"]

    if is_maximizing:
        max_eval = -999999
        for move in legal_moves:
            sim_board = apply_move(board, move)
            if move.mentor_at is None and sim_board[move.move_to.row][move.move_to.col].level == 3:
                return QML_WEIGHTS["win_move"]
            eval_score = minimax(sim_board, depth - 1, alpha, beta, False, team_id, opp_id)
            max_eval = max(max_eval, eval_score)
            alpha = max(alpha, eval_score)
            if beta <= alpha: break
        return max_eval
    else:
        min_eval = 999999
        for move in legal_moves:
            sim_board = apply_move(board, move)
            if move.mentor_at is None and sim_board[move.move_to.row][move.move_to.col].level == 3:
                return -QML_WEIGHTS["win_move"]
            eval_score = minimax(sim_board, depth - 1, alpha, beta, True, team_id, opp_id)
            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)
            if beta <= alpha: break
        return min_eval

def choose_turn(board: list[list[Cell]], team_id: int) -> Optional[PlayerTurnResponse]:
    opp_id = 2 if team_id == 1 else 1
    legal_moves = get_legal_moves(board, team_id)
    if not legal_moves: return None

    for move in legal_moves:
        if move.mentor_at is None: return move

    SEARCH_DEPTH = 2 
    best_move = None
    best_score = -999999
    alpha = -999999
    beta = 999999

    for move in legal_moves:
        sim_board = apply_move(board, move)
        score = minimax(sim_board, SEARCH_DEPTH - 1, alpha, beta, False, team_id, opp_id)
        if score > best_score:
            best_score = score
            best_move = move
        alpha = max(alpha, best_score)

    return best_move if best_move else random.choice(legal_moves)