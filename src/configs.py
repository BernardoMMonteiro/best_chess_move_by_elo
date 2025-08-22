import dotenv
import os

# Carregar variaveis de ambiente .env
dotenv.load_dotenv()

# Coloque sua chave api num .env
CHAVE_API_CHESS = os.getenv("key_lichess")
MEU_USUARIO = os.getenv("NOME_USUARIO_LICHESS")