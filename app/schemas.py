from enum import IntEnum, Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class TeamID(IntEnum):
    """Identificador do time."""
    TURING = 1       # professores CLARO e REY
    LOVELACE = 2     # professoras KARIN e BEATRIZ

class TurnPhase(str, Enum):
    """Fase do turno."""
    SETUP = "setup_placement"        # posicionamento inicial
    PLAYER_TURN = "player_turn"      # turno de jogo
    
# ── Celula do tabuleiro ────────────────────────────────

class Cell(BaseModel):
    """
    Cada casa do tabuleiro 5x5.

    - level: altura da construcao (0 a 4).
             0 = terreno vazio, 3 = vitoria ao entrar, 4 = graduada (bloqueada).
    - professor: nome do professor ocupando a casa, ou null se vazia.
    """
    level: int = Field(ge=0, le=4)
    professor: Optional[str] = None

# ── Posicao no tabuleiro ───────────────────────────────

class Position(BaseModel):
    """Coordenada (row, col) no tabuleiro 5x5."""
    row: int = Field(ge=0, le=4)
    col: int = Field(ge=0, le=4)

class PlayerStatus(BaseModel):
    group_name: str
    ai_player_name: str
    ai_player_avatar: Optional[str] = None
    ai_player_description: Optional[str] = None
    ai_player_move_endpoint: str
    id: int
    games_played: int
    games_won: int
    games_lost: int
    average_move_time: Optional[float] = None

class AITurnRequest(BaseModel):
    """
    Payload corrigido para bater exatamente com o formato enviado pelo orquestrador.
    """
    id: str = Field(alias="game_id")  # Mapeia o "id" enviado pela API externa para "game_id" interno se preferir, ou apenas use os campos abaixo:
    status: str
    turn_number: int = 0              # Mude para opcional ou default se o orquestrador mandar dentro de outro escopo
    turn_phase: TurnPhase
    your_team: TeamID
    board: List[List[Cell]]
    professor_to_place: Optional[str] = None
    
    # Se precisar mapear os jogadores que aparecem na imagem:
    turing_player: Optional[PlayerStatus] = None
    lovelace_player: Optional[PlayerStatus] = None

    class Config:
        populate_by_name = True
  
class SetupResponse(BaseModel):
  """Resposta na fase de posicionamento: onde colocar o professor."""
  row: int = Field(ge=0, le=4)
  col: int = Field(ge=0, le=4)
  
class PlayerTurnResponse(BaseModel):
    """
    Resposta na fase de turno de jogo.

    - professor: qual professor mover (ex: "CLARO")
    - move_to: para qual casa mover
    - mentor_at: qual casa adjacente ao destino recebe mentoria (+1 nivel).
                 Pode ser omitido APENAS em jogada de vitoria (destino nivel 3).
    """
    professor: str
    move_to: Position
    mentor_at: Optional[Position] = None