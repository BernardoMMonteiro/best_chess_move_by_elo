"""Processa o JSON bruto vindo da API do lichess num JSON por movimento, guardando a jogada, a posição antes da jogada,
quem venceu o jogo e o rating de quem moveu
"""

import json
from typing import List, Dict, Any, Iterable
from pathlib import Path
import re

import chess # biblioteca externa conveniente para tratar PGN

Result = float  # 1.0 vitória, 0.5 empate, 0.0 derrota (pro jogador que move)
Event = Dict[str, Any]

def _token_is_result(tok: str) -> bool:
    return tok in {"1-0", "0-1", "1/2-1/2", "*"}

def _winner_to_score(winner: str | None, mover_is_white: bool) -> Result:
    if winner is None:
        return 0.5
    if winner == "white":
        return 1.0 if mover_is_white else 0.0
    if winner == "black":
        return 1.0 if not mover_is_white else 0.0
    # fallback (ex.: “draw” em alguns dumps)
    if winner == "draw":
        return 0.5
    return 0.5

def _parse_and_push(board: chess.Board, token: str) -> tuple[chess.Move, str]:
    """
    Tenta interpretar o token como UCI (mais comum no Lichess) e,
    em fallback, como SAN. Retorna (move, san_do_lance).
    """
    # UCI?
    if re.fullmatch(r"[a-h][1-8][a-h][1-8][qrbn]?", token):
        move = chess.Move.from_uci(token)
        san = board.san(move)
        board.push(move)
        return move, san
    # SAN (fallback)
    move = board.parse_san(token)  # lança se inválido
    san = board.san(move)
    board.push(move)
    return move, san

def jogo_para_eventos(game: Dict[str, Any]) -> List[Event]:
    """
    Converte um jogo em lista de eventos por lance, cada um com:
      - fen_before (posição antes do lance)
      - move_uci, move_san
      - ply (1..N)
      - mover ('white'/'black')
      - player_rating (rating do jogador que move naquele lance)
      - mover_score (1, 0.5, 0) baseado no resultado do ponto de vista do mover
      - game_id, rated, variant, speed (se existirem)
    """
    board = chess.Board()  # posição inicial
    tokens = (game.get("moves") or "").split()
    players = game.get("players")
    white_player = players.get("white")

    black_player = players.get("black")
    white_rating = white_player.get("rating", 0)
    black_rating = black_player.get("rating", 0)
    winner = game.get("winner")  # 'white' | 'black' | 'draw' | None
    game_id = game.get("id")
    rated = game.get("rated")
    variant = game.get("variant")
    speed = game.get("speed")

    eventos: List[Event] = []
    ply = 0

    for tok in tokens:
        if _token_is_result(tok):
            break

        fen_before = board.fen()
        mover_is_white = board.turn  # True se branco move
        mover = "white" if mover_is_white else "black"
        player_rating = white_rating if mover_is_white else black_rating
        ply += 1

        try:
            move, san = _parse_and_push(board, tok)
        except Exception:
            # Se algo vier corrompido, ignora o token e segue
            continue

        mover_score = _winner_to_score(winner, mover_is_white)

        eventos.append({
            "game_id": game_id,
            "rated": rated,
            "variant": variant,
            "speed": speed,
            "ply": ply,
            "fen_before": fen_before,
            "move_uci": move.uci(),
            "move_san": san,
            "mover": mover,
            "player_rating": player_rating,
            "mover_score": mover_score,
        })

    return eventos

def carregar_jogos(path: str) -> List[Dict[str, Any]]:
    """Carrega jogos de um arquivo JSON exportado do Lichess."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extrair_eventos(jogos: Iterable[Dict[str, Any]]) -> List[Event]:
    eventos: List[Event] = []
    for g in jogos:
        eventos.extend(jogo_para_eventos(g))
    return eventos


def salvar_eventos(eventos: List[Dict[str, Any]], path: str) -> None:
    """Salva lista de eventos em JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(eventos, f, indent=4, ensure_ascii=False)





if __name__ == '__mfefeaain__':
    nome_arquivo_padrao = Path('data/meus_jogos.json') # mudar se necessario
    jogos = carregar_jogos(nome_arquivo_padrao)
    eventos = extrair_eventos(jogos)
    salvar_eventos(eventos,  Path('data/analise_movimentos.json'))