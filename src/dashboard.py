import chess.svg
import streamlit as st
import pandas as pd
import chess


from src import aggregate_data, configs

DEFAULT_MIN_RATING = 800
DEFAUT_MAX_RATING = 1200

def normalizar_fen(fen: str) -> str:
    """Mantém apenas os 4 primeiros campos da FEN (posição, turno, roques, en passant),
    retirando os dados de número de jogadas."""
    return " ".join(fen.split(" ")[:4])


def carregar_analise(path: str) -> pd.DataFrame:
    return pd.read_json(path)

def carregar_analise_inicial_default() -> pd.DataFrame:
    df = aggregate_data.top_k_lances_por_posicao(con = configs.CONEXAO_BD_PADRAO,
                                            k=15,
                                            min_rating=DEFAULT_MIN_RATING,
                                            max_rating=DEFAUT_MAX_RATING,
                                            min_samples_move=5
                                                      )
    df["fen_before_norm"] = df["fen_before"].apply(normalizar_fen)

    return df


def main():
    st.set_page_config(page_title="Chess Best Moves by Rating", layout="wide")
    st.title("Melhores Lances por Faixa de Rating - Lichess")

    # Inicializa o tabuleiro na sessão, se ainda não existir
    if "board" not in st.session_state:
        st.session_state.board = chess.Board()

    # Carrega dados processados
    #df = carregar_analise("data/analise.json")
    df = carregar_analise_inicial_default()

    # Seleciona faixa de rating
    # faixas = sorted(df["rating_bracket"].unique().tolist())
    
    #faixa = st.selectbox("Escolha a faixa de rating", faixas)

    rating_range = st.slider(
    "Escolha a faixa de rating",
    min_value=0,
    max_value=4000,
    value=(DEFAULT_MIN_RATING, DEFAUT_MAX_RATING),
    step=50
    )

    min_rating, max_rating = rating_range

    faixa = f'{min_rating} - {max_rating}'

    # Usando st.cache_data para evitar recalcular a cada interação
    @st.cache_data
    def load_data(min_r, max_r):
        
        df = aggregate_data.top_k_lances_por_posicao(
            con=configs.CONEXAO_BD_PADRAO,
            k=15,
            min_rating=min_r,
            max_rating=max_r,
            min_samples_move=5
        )

        df["fen_before_norm"] = df["fen_before"].apply(normalizar_fen)
        return df



    df = load_data(min_rating, max_rating)

    # Seleciona posição (FEN inicial)
    posicoes = df["fen_before_norm"].unique().tolist()
    fen_default = chess.STARTING_FEN
    fen = st.selectbox(
        "Escolha a posição (FEN)",
        options=posicoes,
        index=posicoes.index(fen_default) if fen_default in posicoes else 0,
    )

    # Resetar tabuleiro para a FEN escolhida
    if st.button("Carregar posição selecionada"):
        st.session_state.board = chess.Board(fen)

    if st.button("Voltar à posição inicial"):
        st.session_state.board =  chess.Board(fen_default)

    col1, col2 = st.columns([1, 1.5])

    with col1:
        st.subheader("Tabuleiro da posição")

        # Entrada de movimento manual
        move_input = st.text_input("Digite um lance (SAN)", "")

        if move_input:
            try:
                st.session_state.board.push_san(move_input)
                st.success(f"Lance '{move_input}' jogado com sucesso!")
            except Exception as e:
                st.error(f"Lance inválido: {e}")

        st.image(chess.svg.board(st.session_state.board, size=400))

    with col2:
        st.subheader(f"Top lances em {faixa}")

        # Pega a FEN atual do tabuleiro
        fen_atual = normalizar_fen(st.session_state.board.fen())

        st.text(f"FEN atual: {fen_atual}")


        # Filtra os lances para essa posição
        pos_df = df[df["fen_before_norm"] == fen_atual]

        if not pos_df.empty:
            st.dataframe(
                pos_df[["move_san", "win_rate", "n", "play_rate"]]
                .sort_values(["win_rate", "n"], ascending=[False, False])
                .reset_index(drop=True)
            )
        else:
            st.info("Ainda não há estatísticas para essa posição nesta faixa de rating.")


if __name__ == "__main__":
    # para rodar no terminal: poetry run python -m streamlit run src/dashboard.py
    main()