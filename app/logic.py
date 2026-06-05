# app/logic.py
import random
import math
import copy
from typing import Optional
import numpy as np
import pennylane as qml

from app.schemas import Cell, Position, SetupResponse, PlayerTurnResponse

BOARD_SIZE = 5

# Professores de cada time
TEAM_PROFESSORS = {
    1: ["CLARO", "REY"],       # Turing
    2: ["KARIN", "BEATRIZ"],   # Lovelace
}

# ---------------------------------------------------------
# MÓDULO 3: QUANTUM MACHINE LEARNING (Substituindo GA)
# ---------------------------------------------------------
# Definição da Arquitetura Quântica: 4 Qubits, 2 Camadas de Emaranhamento
N_QUBITS = 4
N_LAYERS = 2
dev = qml.device("default.qubit", wires=N_QUBITS)

# Pesos da Rede Neural Quântica (Devem ser otimizados via Quantum Gradient Descent)
# Para este teste, inicializados aleatoriamente no espaço [-pi, pi]
QML_WEIGHTS = np.random.uniform(low=-np.pi, high=np.pi, size=(N_LAYERS, N_QUBITS, 3))

@qml.qnode(dev)
def quantum_evaluation_circuit(features, weights):
    """
    Circuito Quântico Parametrizado.
    Transforma dados clássicos em estados quânticos e aplica portas de rotação.
    """
    # 1. State Preparation: Angle Embedding (mapeia features para rotações X)
    qml.AngleEmbedding(features, wires=range(N_QUBITS), rotation='X')

    # 2. Ansatz: Camadas de forte emaranhamento (CNOTs) e rotações parametrizadas
    qml.StronglyEntanglingLayers(weights, wires=range(N_QUBITS))

    # 3. Measurement: Valor esperado do qubit 0 no eixo Z
    return qml.expval(qml.PauliZ(0))

def extract_quantum_features(board: list[list[Cell]], team_id: int, opp_id: int) -> np.ndarray:
    """Redução de Dimensionalidade clássica para alimentar o circuito quântico."""
    f_team_height, f_opp_height = 0.0, 0.0
    f_team_center, f_opp_center = 0.0, 0.0

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell = board[r][c]
            if cell.professor is None:
                continue

            center_dist = abs(r - 2) + abs(c - 2)
            
            if cell.professor in TEAM_PROFESSORS[team_id]:
                f_team_height += cell.level
                f_team_center += (4 - center_dist)
            elif cell.professor in TEAM_PROFESSORS[opp_id]:
                f_opp_height += cell.level
                f_opp_center += (4 - center_dist)

    features = np.array([f_team_height, f_opp_height, f_team_center, f_opp_center])
    
    # Normalização em [0, pi] rigorosamente exigida pelo Angle Embedding
    max_val = np.max(features)
    if max_val > 0:
        features = (features / max_val) * np.pi
        
    return features

def evaluate_board(board: list[list[Cell]], team_id: int, opp_id: int) -> float:
    """Avaliação VQC (Variational Quantum Classifier)."""
    # Fallback clássico para vitória absoluta O(1)
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell = board[r][c]
            if cell.level == 3 and cell.professor is not None:
                return 10000.0 if cell.professor in TEAM_PROFESSORS[team_id] else -10000.0

    # Extrai características de estado e executa a simulação do circuito
    features = extract_quantum_features(board, team_id, opp_id)
    quantum_score = quantum_evaluation_circuit(features, QML_WEIGHTS)
    
    # A medição <Z> retorna escalares no intervalo [-1, 1]. Amplificamos para o Minimax.
    return float(quantum_score) * 1000.0

# ---------------------------------------------------------
# MÓDULO 1: FILTRO CSP (Mantido)
# ---------------------------------------------------------
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
        (r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE)
        if board[r][c].level == 0 and board[r][c].professor is None
    ]
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
            if dst_cell.professor is not None or dst_cell.level == 4 or dst_cell.level > cur_level + 1:
                continue

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
                        mentor_at=Position(row=men_row, col=men_col),
                    ))
    return legal_moves

def apply_move(board: list[list[Cell]], move: PlayerTurnResponse) -> list[list[Cell]]:
    new_board = copy.deepcopy(board)
    old_pos = find_professor(new_board, move.professor)
    if old_pos: new_board[old_pos[0]][old_pos[1]].professor = None
    new_board[move.move_to.row][move.move_to.col].professor = move.professor
    if move.mentor_at: new_board[move.mentor_at.row][move.mentor_at.col].level += 1
    return new_board

# ---------------------------------------------------------
# MÓDULO 2: MOTOR MINIMAX COM PODA ALPHA-BETA (Mantido)
# ---------------------------------------------------------
def minimax(board: list[list[Cell]], depth: int, alpha: float, beta: float, 
            is_maximizing: bool, team_id: int, opp_id: int) -> float:
    if depth == 0:
        return evaluate_board(board, team_id, opp_id)
        
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
            if beta <= alpha: break
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
            if beta <= alpha: break
        return min_eval

def choose_turn(board: list[list[Cell]], team_id: int) -> Optional[PlayerTurnResponse]:
    opp_id = 2 if team_id == 1 else 1
    best_move = None
    best_score = -math.inf
    
    legal_moves = get_legal_moves(board, team_id)
    if not legal_moves: return None

    for move in legal_moves:
        if move.mentor_at is None: return move

    # Profundidade reduzida devido à latência computacional do simulador quântico
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