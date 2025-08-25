import dotenv
import os
import duckdb

# Carregar variaveis de ambiente .env
dotenv.load_dotenv()

# Coloque sua chave api num .env
CHAVE_API_CHESS = os.getenv("key_lichess")
MEU_USUARIO = os.getenv("NOME_USUARIO_LICHESS")

# Banco padrao:
CONEXAO_BD_PADRAO = duckdb.connect("melhores_lances.duckdb")
