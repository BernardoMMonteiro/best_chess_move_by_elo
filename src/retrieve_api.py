# API do Lichess
import berserk
import json
from datetime import datetime
from src import configs

# Configura sessão, com token para API
session = berserk.TokenSession(configs.key)
client = berserk.Client(session=session)

# Exporta lista de jogos completa de um jogador pelo nome como
jogos = client.games.export_by_player(configs.MEU_USUARIO)


print(jogos)

games = list(jogos)

for item in games:
    for key, value in item.items():
        if isinstance(value, datetime):
            item[key] = value.isoformat()

with open('meus_jogos.json', 'w', encoding='utf-8') as f:
    json.dump(games, f, indent=4)
