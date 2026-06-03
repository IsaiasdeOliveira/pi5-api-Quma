# app/logic.py
import random
import math
import copy
import pennylane as qml
from pennylane import numpy as np  # <-- CORREÇÃO 1: Usar o Numpy do próprio PennyLane
from typing import Optional

from app.schemas import Cell, Position, SetupResponse, PlayerTurnResponse

BOARD_SIZE = 5

# Professores de cada time
TEAM_PROFESSORS = {
    1: ["CLARO", "REY"],       # Turing
    2: ["KARIN", "BEATRIZ"],   # Lovelace
}

# =========================================================
# REDE NEURAL QUÂNTICA (QNN) PARA AVALIAÇÃO DO TABULEIRO
# =========================================================
N_QUBITS = 4
# Inicializa o simulador quântico clássico
dev = qml.device("default.qubit", wires=N_QUBITS)

# CORREÇÃO 2: Travar os gradientes (requires_grad=False) pois estamos apenas inferindo/jogando
QML_TRAINED_WEIGHTS = np.array([
    [0.85, -0.42, 1.15, -0.21],
    [1.52, -0.11, 0.93,  0.64]
], requires_grad=False)

@qml.qnode(dev)
def qnn_heuristic_circuit(features, weights):
    """
    Circuito Quântico Parametrizado (PQC).
    Recebe características normalizadas e retorna um valor esperado entre [-1, 1].
    """
    qml.AngleEmbedding(features, wires=range(N_QUBITS))
    qml.BasicEntanglerLayers(weights, wires=range(N_QUBITS))
    return qml.expval(qml.PauliZ(0))


# =========================================================
# MÓDULO 1: FILTRO CSP (Clássico)
# =========================================================
def adjacent_cells(row: int, col: int) -> list[tuple[int, int]]:
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
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c].professor == name:
                return (r, c)
    return None

def choose_setup(board: list[list[Cell]]) -> SetupResponse:
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
                        mentor_at=Position(row=men_row, col=men_col),
                    ))
                    
    return legal_moves

def apply_move(board: list[list[Cell]], move: PlayerTurnResponse) -> list[list[Cell]]:
    new_board = copy.deepcopy(board)
    old_pos = find_professor(new_board, move.professor)
    if old_pos:
        new_board[old_pos[0]][old_pos[1]].professor = None
        
    new_board[move.move_to.row][move.move_to.col].professor = move.professor
    if move.mentor_at:
        new_board[move.mentor_at.row][move.mentor_at.col].level += 1
    return new_board

# =========================================================
# MÓDULO 3: AVALIAÇÃO VIA QUANTUM MACHINE LEARNING
# =========================================================
def evaluate_board_quantum(board: list[list[Cell]], team_id: int, opp_id: int) -> float:
    my_height, opp_height, center_ctrl = 0.0, 0.0, 0.0
    
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell = board[r][c]
            if cell.professor is None:
                continue
                
            if cell.level == 3:
                return 10000.0 if cell.professor in TEAM_PROFESSORS[team_id] else -10000.0

            if cell.professor in TEAM_PROFESSORS[team_id]:
                my_height += cell.level
                center_ctrl += (4 - (abs(r - 2) + abs(c - 2))) 
            elif cell.professor in TEAM_PROFESSORS[opp_id]:
                opp_height += cell.level
                
    f1 = (my_height / 6.0) * np.pi
    f2 = (opp_height / 6.0) * np.pi
    f3 = (center_ctrl / 8.0) * np.pi
    
    my_moves = len(get_legal_moves(board, team_id))
    opp_moves = len(get_legal_moves(board, opp_id))
    f4 = (max(0, my_moves - opp_moves) / 20.0) * np.pi

    # CORREÇÃO 3: Array sem gradiente para injetar no circuito quântico
    features = np.array([f1, f2, f3, f4], requires_grad=False)
    
    qml_expectation = qnn_heuristic_circuit(features, QML_TRAINED_WEIGHTS)
    
    # CORREÇÃO 4: Extração segura do tensor quântico com .item()
    return float(qml_expectation.item()) * 100.0

# =========================================================
# MÓDULO 2: MOTOR MINIMAX HÍBRIDO (Busca Clássica + Avaliação Quântica)
# =========================================================
def minimax(board: list[list[Cell]], depth: int, alpha: float, beta: float, 
            is_maximizing: bool, team_id: int, opp_id: int) -> float:
    
    if depth == 0:
        return evaluate_board_quantum(board, team_id, opp_id)
        
    current_team = team_id if is_maximizing else opp_id
    legal_moves = get_legal_moves(board, current_team)
    
    if not legal_moves:
        return -10000.0 if is_maximizing else 10000.0

    if is_maximizing:
        max_eval = -math.inf
        for move in legal_moves:
            simulated_board = apply_move(board, move)
            
            if move.mentor_at is None and simulated_board[move.move_to.row][move.move_to.col].level == 3:
                return 10000.0
                
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
                return -10000.0
                
            eval_score = minimax(simulated_board, depth - 1, alpha, beta, True, team_id, opp_id)
            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)
            if beta <= alpha:
                break
        return min_eval

def choose_turn(board: list[list[Cell]], team_id: int) -> Optional[PlayerTurnResponse]:
    opp_id = 2 if team_id == 1 else 1
    best_move = None
    best_score = -math.inf
    
    legal_moves = get_legal_moves(board, team_id)
    if not legal_moves:
        return None

    for move in legal_moves:
        if move.mentor_at is None:
            return move

    SEARCH_DEPTH = 2 
    alpha = -math.inf
    beta = math.inf

    for move in legal_moves:
        simulated_board = apply_move(board, move)
        move_score = minimax(simulated_board, SEARCH_DEPTH - 1, alpha, beta, False, team_id, opp_id)
        
        if move_score > best_score:
            best_score = move_score
            best_move = move
            
        alpha = max(alpha, best_score)

    if best_move is None:
        best_move = random.choice(legal_moves)
        
    return best_move