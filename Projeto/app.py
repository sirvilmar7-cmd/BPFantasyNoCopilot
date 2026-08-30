from flask import Flask, jsonify
from flask_cors import CORS
from nba_api.stats.endpoints import leaguedashplayerstats, playerindex, playergamelogs
import numpy as np
import pandas as pd
import json
import os
import unicodedata

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

TEMPORADA = '2025-26'


def normalizar_nome(nome):
    if not nome:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', nome)
        if unicodedata.category(c) != 'Mn'
    ).lower()


def carregar_banco_fantasy():
    """
    Le elencos.json e devolve dois mapas indexados pelo nome normalizado:

    mapa_times    -> { nome_jogador: { liga: franquia } }
    mapa_salarios -> { nome_jogador: { liga: { ano: valor } } }

    O salario e sempre associado a liga de origem. Um mesmo jogador pode ter
    contratos diferentes em ligas diferentes, e ligas sem informacao de
    salario simplesmente nao aparecem no mapa (campo fica em branco no front).
    """
    caminho_arquivo = 'elencos.json'
    mapa_times = {}
    mapa_salarios = {}

    if not os.path.exists(caminho_arquivo):
        return mapa_times, mapa_salarios

    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        dados_ligas = json.load(f)

    for liga, franquias in dados_ligas.items():
        for nome_franquia, conteudo in franquias.items():

            # Compatibilidade com os dois formatos ja usados no projeto:
            # lista simples de nomes, ou dicionario com metadados por jogador.
            if isinstance(conteudo, list):
                itens = {nome: {} for nome in conteudo}
            else:
                itens = conteudo.get('jogadores', {})
                if isinstance(itens, list):
                    itens = {nome: {} for nome in itens}

            for jogador, meta in itens.items():
                nome_limpo = normalizar_nome(jogador)

                mapa_times.setdefault(nome_limpo, {})
                mapa_times[nome_limpo][liga] = nome_franquia

                salarios = {}
                if isinstance(meta, dict):
                    salarios = meta.get('salarios', {}) or {}

                # So registra a liga no mapa de salarios se houver algum valor.
                if salarios:
                    mapa_salarios.setdefault(nome_limpo, {})
                    mapa_salarios[nome_limpo][liga] = salarios

    return mapa_times, mapa_salarios


@app.route('/api/jogadores', methods=['GET'])
def obter_jogadores():
    try:
        dados_api = leaguedashplayerstats.LeagueDashPlayerStats(
            season=TEMPORADA,
            per_mode_detailed='PerGame'
        )
        resultados = dados_api.get_dict()['resultSets'][0]
        headers = resultados['headers']
        linhas = resultados['rowSet']

        # --- Posicoes (endpoint em lote) ---
        mapa_posicoes = {}
        try:
            dados_posicao = playerindex.PlayerIndex(
                season=TEMPORADA, historical_nullable='1'
            ).get_dict()['resultSets'][0]
            idx_fname = dados_posicao['headers'].index('PLAYER_FIRST_NAME')
            idx_lname = dados_posicao['headers'].index('PLAYER_LAST_NAME')
            idx_pos = dados_posicao['headers'].index('POSITION')

            for l in dados_posicao['rowSet']:
                nome_completo = f"{l[idx_fname]} {l[idx_lname]}".strip()
                posicao = l[idx_pos]
                if posicao:
                    mapa_posicoes[normalizar_nome(nome_completo)] = posicao
        except Exception as e:
            print(f"Aviso: falha ao carregar matriz de posicoes. Detalhes: {e}")

        # --- Desvio-padrao por categoria (em lote) ---
        std_dict = {}
        try:
            print("Coletando logs de jogo em lote para calcular variancia...")
            logs = playergamelogs.PlayerGameLogs(season_nullable=TEMPORADA)
            logs_df = logs.get_data_frames()[0]
            std_df = logs_df.groupby('PLAYER_ID')[
                ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M', 'TOV']
            ].std().reset_index()
            std_df = std_df.fillna(0.0)
            std_dict = std_df.set_index('PLAYER_ID').to_dict('index')
        except Exception as e:
            print(f"Aviso: falha ao carregar logs para variancia. Detalhes: {e}")

        cats = {
            'pts': headers.index('PTS'), 'reb': headers.index('REB'),
            'ast': headers.index('AST'), 'stl': headers.index('STL'),
            'blk': headers.index('BLK'), 'fg3m': headers.index('FG3M'),
            'tov': headers.index('TOV')
        }

        idx_nome = headers.index('PLAYER_NAME')
        idx_min = headers.index('MIN')
        idx_idade = headers.index('AGE')
        idx_time = headers.index('TEAM_ABBREVIATION')
        idx_gp = headers.index('GP')
        idx_player_id = headers.index('PLAYER_ID')

        linhas_filt = [l for l in linhas if l[idx_min] >= 10]

        vals = {cat: [l[idx] for l in linhas_filt] for cat, idx in cats.items()}
        medias = {cat: np.mean(vals[cat]) for cat in cats}
        desvios = {
            cat: np.std(vals[cat]) if np.std(vals[cat]) > 0 else 1
            for cat in cats
        }

        vals_pm = {
            cat: [l[idx] / l[idx_min] for l in linhas_filt]
            for cat, idx in cats.items()
        }
        medias_pm = {cat: np.mean(vals_pm[cat]) for cat in cats}
        desvios_pm = {
            cat: np.std(vals_pm[cat]) if np.std(vals_pm[cat]) > 0 else 0.001
            for cat in cats
        }

        mapa_times, mapa_salarios = carregar_banco_fantasy()
        lista = []

        for l in linhas_filt:
            nome = l[idx_nome]
            nome_norm = normalizar_nome(nome)
            player_id = l[idx_player_id]

            z = {
                c: ((l[cats[c]] - medias[c]) / desvios[c]) * -1 if c == 'tov'
                else (l[cats[c]] - medias[c]) / desvios[c]
                for c in cats
            }
            z_pm = {
                c: ((l[cats[c]] / l[idx_min] - medias_pm[c]) / desvios_pm[c]) * -1 if c == 'tov'
                else (l[cats[c]] / l[idx_min] - medias_pm[c]) / desvios_pm[c]
                for c in cats
            }

            var_data = std_dict.get(player_id, {})

            lista.append({
                'nome': nome,
                'status_fantasy': mapa_times.get(nome_norm, {}),
                # Salarios por liga. Ligas sem dado nao aparecem aqui.
                'salarios_fantasy': mapa_salarios.get(nome_norm, {}),
                'posicao': mapa_posicoes.get(nome_norm, 'N/D'),
                'idade': l[idx_idade], 'time': l[idx_time],
                'gp': l[idx_gp], 'min': l[idx_min],
                **{c: l[cats[c]] for c in cats},
                **{f'z_{c}': z[c] for c in cats},
                **{f'z_pm_{c}': z_pm[c] for c in cats},
                'rating': round(float(np.mean(list(z.values()))), 3),
                'rating_pm': round(float(np.mean(list(z_pm.values()))), 3),
                'desvio_pts': float(var_data.get('PTS', 0.0)),
                'desvio_reb': float(var_data.get('REB', 0.0)),
                'desvio_ast': float(var_data.get('AST', 0.0)),
                'desvio_stl': float(var_data.get('STL', 0.0)),
                'desvio_blk': float(var_data.get('BLK', 0.0)),
                'desvio_fg3m': float(var_data.get('FG3M', 0.0)),
                'desvio_tov': float(var_data.get('TOV', 0.0))
            })

        # Rank de referencia do backend (antes do bonus de GP aplicado no front).
        # O frontend RECALCULA os ranks apos aplicar o bonus, entao estes campos
        # servem apenas como fallback caso o front nao recalcule.
        lista = sorted(lista, key=lambda x: x['rating'], reverse=True)
        for i, j in enumerate(lista):
            j['rank_absoluto'] = i + 1

        return jsonify(lista)

    except Exception as e:
        return jsonify({'erro': str(e)}), 500


if __name__ == '__main__':
    porta = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=porta, debug=True)
