"""Script para baixar da API do Lichess (via Berserk) os jogos, por enquanto configurado para baixar só de um usuário
como uma pequena amostra, usar o download_bulk_games.sh para baixar de fato uma amostra grande"""

# API do Lichess
import berserk
import json
from datetime import datetime
from src import configs



if __name__ == '__main__':
    # Configura sessão, com token para API
    session = berserk.TokenSession(configs.CHAVE_API_CHESS)
    client = berserk.Client(session=session)

    # Exporta lista de jogos completa de um jogador pelo nome
    jogos = client.games.export_by_player(configs.MEU_USUARIO)


    print(jogos)

    games = list(jogos)

    for item in games:
        for key, value in item.items():
            if isinstance(value, datetime):
                item[key] = value.isoformat()

    with open('data/meus_jogos.json', 'w', encoding='utf-8') as f:
        json.dump(games, f, indent=4)
