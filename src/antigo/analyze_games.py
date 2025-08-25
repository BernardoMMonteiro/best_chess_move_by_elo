import json
import pandas as pd

from typing import List, Dict, Any, Literal, Tuple
import numpy as np


def carregar_eventos(path: str) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data)



def definir_faixa_intervalo(rating: int, intervalo = 200) -> str:
    """Cria faixas de N (default 200) pontos (ex: 800-999, 1000-1199, etc.)."""
    if pd.isna(rating) or rating <= 0:
        return "unknown"
    lower = (rating // intervalo) * intervalo
    upper = lower + (intervalo - 1)
    return f"{lower}-{upper}"


def preparar_eventos_para_analise(
    eventos: pd.DataFrame,
) -> pd.DataFrame:
    """
    Produz um DF com colunas:     
    ['rating_bracket','fen_before','move_san','mover_score']

    """
    df = eventos.copy()
    df["rating_bracket"] = df["player_rating"].apply(definir_faixa_intervalo)
    return df[["rating_bracket", "fen_before", "move_san", "mover_score"]]



def estatisticas_de_lances_por_posicao(
    df_ev: pd.DataFrame,
    *,
    min_samples_move: int = 1,
) -> pd.DataFrame:
    """
    Para cada (faixa de rating, posição/FEN, lance) calcula:
      - n (amostras do lance)
      - win_rate (média do mover_score)
    Retorna tabela granular para alimentar um dashboard ou um "top-k" posterior.
    """
    g = (
        df_ev.groupby(["rating_bracket", "fen_before", "move_san"])
             .agg(n=("mover_score", "size"), win_rate=("mover_score", "mean"))
             .reset_index()
    )
    return g[g["n"] >= min_samples_move].sort_values(["rating_bracket", "fen_before", "win_rate", "n"], ascending=[True, True, False, False])


def top_k_lances_por_posicao(
    stats: pd.DataFrame,
    *,
    k: int = 3
) -> pd.DataFrame:
    """
    Seleciona os k melhores lances por (faixa, posição) usando win_rate e, em empate, n.
    """
    # rank por grupo
    stats = stats.copy()
    stats["rank"] = stats.groupby(["rating_bracket", "fen_before"])\
                         .apply(lambda g: g[["win_rate", "n"]] # TODO: uso do apply torna operação bem lenta
                                .rank(method="first", ascending=False)
                                .sum(axis=1))\
                         .reset_index(level=[0,1], drop=True)
    return stats.sort_values(["rating_bracket", "fen_before", "rank"]).groupby(["rating_bracket", "fen_before"]).head(k)


def salvar_analise(stats: pd.DataFrame, path: str) -> None:
    stats.to_json(path, orient="records", indent=2, force_ascii=False)


if __name__ == '__main__':
    df_ev = carregar_eventos("data/analise_movimentos.json")
    df_prep = preparar_eventos_para_analise(df_ev)
    stats = estatisticas_de_lances_por_posicao(df_prep, min_samples_move=1)
    topk = top_k_lances_por_posicao(stats, k=15)
    salvar_analise(topk, "data/analise.json")