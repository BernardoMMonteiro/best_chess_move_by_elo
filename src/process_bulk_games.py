"""Processa os jogos vindos do Lichess database, extraindo os lançes de cada jogo, acumulando em um arquivo duckdb
Faz uso de geradores e DuckDB para processar alguns GBs de dados em um computador fraco
"""
import io
from pathlib import Path
from typing import Tuple, List, Generator
from enum import IntEnum
import time
from datetime import timedelta
import logging

import zstandard as zstd
import chess.pgn
import duckdb
from tqdm import tqdm

from src import configs

logging.basicConfig(filename='log_file_name.log',
     level=logging.INFO, 
     format= '[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
     datefmt='%H:%M:%S',
     encoding='utf-8'
     )
logger = logging.getLogger(__file__)

class ResultadoJogo(IntEnum):
    EMPATE = 1,
    VITORIA = 2,
    DERROTA = 0



# Funções utilitarias #
def _formatar_resultado(result: str) -> Tuple[ResultadoJogo, ResultadoJogo]:
    if result == "1-0":
        white_score, black_score = ResultadoJogo.VITORIA, ResultadoJogo.DERROTA
    elif result == "0-1":
        white_score, black_score = ResultadoJogo.DERROTA, ResultadoJogo.VITORIA
    elif result == "1/2-1/2":
        white_score, black_score = ResultadoJogo.EMPATE, ResultadoJogo.EMPATE
    else:
        raise ValueError('Sem resultado para o jogo')
    
    return white_score, black_score

def itera_jogos(path: Path) -> Generator:
    """Gera os jogos, um por um do .pgn.zst, usando gerador para não carregar tudo em memória de uma vez"""
    with open(path, "rb") as fh:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(fh) as reader:
            text_stream = io.TextIOWrapper(reader, encoding="utf-8")
            while True:
                game = chess.pgn.read_game(text_stream)
                if game is None:
                    break
                yield game


def extrair_lances(game: chess.pgn.Game) -> List:
    """Extrai dados dos movimentos de cada jogo"""
    headers = game.headers
    try:
        white_rating = int(headers['WhiteElo'])
        black_rating = int(headers['BlackElo'])
        result = headers["Result"]
    except (ValueError, KeyError) as e:
        # Casos de erros mapeados que podem ser descartados aqui com segurança
        logger.debug(f'Jogo não contém informações válidas sobre o ELO ou resultado, será descartado: {e}')
        return []

    average_rating = (white_rating + black_rating ) // 2 
    white_score, black_score =  _formatar_resultado(result)

    board = game.board()
    moves_data = []
    for ply, move in enumerate(game.mainline_moves(), start=1):
        mover = "white" if board.turn else "black"
        # rating = white_rating if mover == "white" else black_rating
        score = white_score if mover == "white" else black_score

        moves_data.append((
            ply,
            board.fen(),
            board.san(move),
            mover,
            average_rating,
            score,
        ))

        board.push(move)

    return moves_data


def processa_pgn_para_duckdb(path: Path, max_games: int=None, chunk_size: int =50_000,
                             conn: duckdb.DuckDBPyConnection = configs.CONEXAO_BD_PADRAO
                             ):
    """Stream PGN -> extrair lançes -> salvar em disco no DuckDB
    Função orquestradora principal do script
    """

    #TODO mapear mais coisas para integer
    logger.info('Criando tabela se já não existir..')
    conn.execute("""
        CREATE TABLE IF NOT EXISTS moves (
            ply INTEGER,
            fen_before TEXT,
            move_san TEXT,
            mover TEXT,
            average_rating INTEGER,
            mover_score TINYINT
        )
    """)

    buffer = []
    total = 0

    INSERT_QUERY = "INSERT INTO moves VALUES (?, ?, ?, ?, ?, ?)"

    for i, game in enumerate(tqdm(itera_jogos(path), desc="Processando jogos")):
        if max_games and i >= max_games:
            break
        try:
            moves = extrair_lances(game)
            if moves:
                buffer.extend(moves)
        except Exception as e:
            logger.exception(f'Erro ao processar o {i}-ésimo jogo, pulando-o...: {e}')
            continue

        # Insere quando o buffer atingir o tamanho esperado
        if len(buffer) >= chunk_size:
            conn.executemany(INSERT_QUERY, buffer)
            total += len(buffer)
            logger.info(f"Já foram inseridos no total: {total} ")
            buffer = []

    # Caso saia do loop com valores ainda a inserir
    if buffer:
        conn.executemany(INSERT_QUERY, buffer)
        total += len(buffer)
    conn.commit()
    conn.close()
    logger.info('Finalizando inserção e fechando conexão')
    logger.info(f"Salvos no total {total} lances na tabela")


if __name__ == "__main__":
    logger.info("Iniciando o programa")
    inicio = time.perf_counter()
    processa_pgn_para_duckdb(
        "data/lichess_db_standard_rated_2018-02.pgn.zst",
        chunk_size=100_000,
        max_games=100_000  # só para teste
    )

    duracao = timedelta(seconds=(time.perf_counter() - inicio))
    logger.info(f"Duração total do processamento: {duracao}")