"""Agrega os dados por movimento para formar estatísticas por rating de melhores movimentos"""
from typing import Optional

import duckdb
import pandas as pd


# Conectar ao banco

def definir_faixa_intervalo_sql(intervalo: int = 200) -> str:
    """
    Retorna expressão SQL para criar faixas de rating.
    Ex: 800-999, 1000-1199...
    """
    return f"""
        CASE
            WHEN player_rating IS NULL OR player_rating <= 0 THEN 'unknown'
            ELSE
                CAST((player_rating/{intervalo})*{intervalo} AS VARCHAR) || '-' ||
                CAST(((player_rating/{intervalo})*{intervalo} + {intervalo}-1) AS VARCHAR)
        END
    """

def estatisticas_de_lances_por_posicao(
    con: duckdb.DuckDBPyConnection,
    *,
    intervalo: int = 200,
    min_samples_move: int = 1,
) -> pd.DataFrame:
    """
    Para cada (faixa de rating, posição/FEN, lance):
      - n (quantidade de amostras do lance)
      - win_rate (média de mover_score)
    """
    faixa_expr = definir_faixa_intervalo_sql(intervalo)

    query = f"""
        SELECT 
            {faixa_expr} AS rating_bracket,
            fen_before,
            move_san,
            COUNT(*) AS n,
            AVG(mover_score) AS win_rate
        FROM moves
        GROUP BY rating_bracket, fen_before, move_san
        HAVING COUNT(*) >= {min_samples_move}
    """
    return con.execute(query).df()


def top_k_lances_por_posicao(
    con: duckdb.DuckDBPyConnection,
    *,
    k: int = 3,
    min_rating: int = 200,
    max_rating:int = 1000,
    min_samples_move: int = 1,
) -> pd.DataFrame:
    """Via SQL retorna os melhores lances por posição para uma faixa de rating específica.
    """
    #faixa_expr = definir_faixa_intervalo_sql(intervalo)

    #query_antiga = f"""
    #    SELECT *
    #    FROM (
    #        SELECT 
    #            {faixa_expr} AS rating_bracket,
    #            fen_before,
    #            move_san,
    #            COUNT(*) AS n,
    #            AVG(mover_score) AS win_rate,
    #            ROW_NUMBER() OVER (
    #                PARTITION BY {faixa_expr}, fen_before
    #                ORDER BY AVG(mover_score) DESC, COUNT(*) DESC
    #            ) AS rank
    #        FROM moves
    #        GROUP BY rating_bracket, fen_before, move_san
    #        HAVING COUNT(*) >= {min_samples_move}
    #    )
    #    WHERE rank <= {k}
    #    ORDER BY rating_bracket, fen_before, rank;
    #"""

    query = f"""
        SELECT *
        FROM (
            SELECT 
                fen_before,
                move_san,
                COUNT(*) AS n,
                AVG(mover_score/2) AS win_rate,
                COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY fen_before) AS play_rate,
                ROW_NUMBER() OVER (
                    PARTITION BY fen_before
                    ORDER BY AVG(mover_score) DESC, COUNT(*) DESC
                ) AS rank
            FROM moves
            WHERE average_rating BETWEEN {min_rating} AND {max_rating}
            GROUP BY fen_before, move_san
            HAVING COUNT(*) >= {min_samples_move}
        )
        WHERE rank <= {k}
        ORDER BY fen_before, rank;
    """
    return con.execute(query).df()

if __name__ == "__main__":
    from src import configs

    con = configs.CONEXAO_BD_PADRAO

    stats = estatisticas_de_lances_por_posicao(con, intervalo=200, min_samples_move=10)
    topk = top_k_lances_por_posicao(con, k=15, min_samples_move=10, min_rating=0, max_rating=4000)

    print(topk)
    # topk.to_json("data/analise.json", orient="records", indent=2, force_ascii=False)