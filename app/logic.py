# app/logic.py
import random
import math
import copy
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

# =========================================================
# CARREGAMENTO AUTOMÁTICO DOS PESOS QUÂNTICOS
# =========================================================
# Valores fallback de segurança (caso o JSON ainda não tenha sido gerado)
QML_WEIGHTS = {
    "win_move": 10000.0,
    "my_height": 10.0,
    "opp_height": -15.0,
    "center_control": 3.0,
    "mobility": 1.0
}

# Carrega o arquivo JSON gerado pelo trainer de forma transparente e instantânea
try:
    if os.path.exists("pesos_quanticos.json"):
        with open("pesos_quanticos.json", "r") as f:
            QML_WEIGHTS = json.load(f)
            print("[INFO] Pesos otimizados por Quantum Machine Learning injetados com sucesso!")
except Exception as e:
    print(f"[AVISO] Não foi possível ler o arquivo quântico. Usando o fallback estático. Erro: {e}")


# =========================================================
# MÓDULO 1: FILTRO CSP (Satisfação de Restrições)
# =========================================================
def adjacent_cells(row: int, col: int) -> list[tuple[int, int]]:
    """Retorna todas as casas vizinhas (incluindo diagonais) dentro do grid."""
    cells = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0: continue
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
    """Fase de posicionamento inicial: Prioriza o controle das salas do centro."""
    candidates = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) 
                  if board[r][c].level == 0 and board[r][c].professor is None]
    center_candidates = [(r, c) for r, c in candidates if 1 <= r <= 3 and 1 <= c <= 3]
    row, col = random.choice(center_candidates if center_candidates else candidates)
    return SetupResponse(row=row, col=col)

def get_legal_moves(board: list[list[Cell]], team_id: int) -> list[PlayerTurnResponse]:
    """Gera todos os movimentos e mentorias 100% válidos (Filtro CSP)."""
    legal_moves = []
    for professor in TEAM_PROFESSORS[team_id]:
        pos = find_professor(board, professor)
        if pos is None: continue

        cur_row, cur_col = pos
        cur_level = board[cur_row][cur_col].level

        for dst_row, dst_col in adjacent_cells(cur_row, cur_col):
            dst_cell = board[dst_row][dst_col]

            # Aplicação das restrições estritas do jogo (CSP)
            if dst_cell.professor is not None: continue
            if dst_cell.level == 4: continue
            if dst_cell.level > cur_level + 1: continue

            # Movimento de Vitória Imediata (Ir para o 3º ano)
            if dst_cell.level == 3:
                legal_moves.append(PlayerTurnResponse(professor=professor, move_to=Position(row=dst_row, col=dst_col)))
                continue

            # Regras para Mentoria (Construção das salas adjacentes ao destino)
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

def apply_move(board: list[list[Cell]], move: PlayerTurnResponse) -> list[list[Cell]]:
    """Gera um clone hipotético do tabuleiro para simulação das jogadas futuras."""
    new_board = copy.deepcopy(board)
    old_pos = find_professor(new_board, move.professor)
    if old_pos:
        new_board[old_pos[0]][old_pos[1]].professor = None
        
    new_board[move.move_to.row][move.move_to.col].professor = move.professor
    if move.mentor_at:
        new_board[move.mentor_at.row][move.mentor_at.col].level += 1
    return new_board


# =========================================================
# MÓDULO 2: AVALIAÇÃO DE ESTADO COM INTELIGÊNCIA QUÂNTICA
# =========================================================
def evaluate_board_classic(board: list[list[Cell]], team_id: int, opp_id: int) -> float:
    """Mapeia matematicamente o valor das salas usando os pesos gerados pelo circuito QML."""
    score = 0.0
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell = board[r][c]
            if cell.professor is None: continue
                
            if cell.level == 3:
                return QML_WEIGHTS["win_move"] if cell.professor in TEAM_PROFESSORS[team_id] else -QML_WEIGHTS["win_move"]

            if cell.professor in TEAM_PROFESSORS[team_id]:
                score += cell.level * QML_WEIGHTS["my_height"]
                # Distância de Manhattan invertida para bonificar o centro (2,2)
                score += (4 - (abs(r - 2) + abs(c - 2))) * QML_WEIGHTS["center_control"]
            elif cell.professor in TEAM_PROFESSORS[opp_id]:
                score += cell.level * QML_WEIGHTS["opp_height"]
                
    # Vantagem posicional quantificada pela mobilidade gerada no CSP
    my_moves = len(get_legal_moves(board, team_id))
    opp_moves = len(get_legal_moves(board, opp_id))
    score += (my_moves - opp_moves) * QML_WEIGHTS["mobility"]
    
    return score


# =========================================================
# MÓDULO 3: MOTOR MINIMAX COM PODA ALPHA-BETA (Alta Velocidade)
# =========================================================
def minimax(board: list[list[Cell]], depth: int, alpha: float, beta: float, is_maximizing: bool, team_id: int, opp_id: int) -> float:
    """Árvore de busca clássica extremamente rápida usando as diretrizes de pontuação do QML."""
    if depth == 0:
        return evaluate_board_classic(board, team_id, opp_id)
        
    current_team = team_id if is_maximizing else opp_id
    legal_moves = get_legal_moves(board, current_team)
    
    if not legal_moves:
        return -QML_WEIGHTS["win_move"] if is_maximizing else QML_WEIGHTS["win_move"]

    if is_maximizing:
        max_eval = -math.inf
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
        min_eval = math.inf
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
    """Ponto de entrada do endpoint /move: decide a jogada ótima instantaneamente."""
    opp_id = 2 if team_id == 1 else 1
    legal_moves = get_legal_moves(board, team_id)
    if not legal_moves: return None

    # Se houver vitória imediata na raiz, executa sem abrir a árvore
    for move in legal_moves:
        if move.mentor_at is None: return move

    # Como a matemática quântica complexa foi isolada em formato JSON, 
    # o Minimax agora pode olhar até 3 turnos à frente com tempo de resposta de milissegundos!
    SEARCH_DEPTH = 3 
    best_move, best_score, alpha, beta = None, -math.inf, -math.inf, math.inf

    for move in legal_moves:
        sim_board = apply_move(board, move)
        score = minimax(sim_board, SEARCH_DEPTH - 1, alpha, beta, False, team_id, opp_id)
        if score > best_score:
            best_score, best_move = score, move
        alpha = max(alpha, best_score)

    return best_move if best_move else random.choice(legal_moves)