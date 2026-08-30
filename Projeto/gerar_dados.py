"""
GERADOR DE DADOS ESTATICOS
==========================

Roda NA SUA MAQUINA (nao em servidor) e grava o arquivo `dados.json`.

POR QUE ISSO EXISTE
-------------------
O endpoint stats.nba.com fica atras da protecao Akamai e descarta requisicoes
vindas de IPs de datacenter. Um backend hospedado nao consegue buscar os dados
da NBA de forma confiavel. A solucao e gerar os dados aqui, do seu IP
residencial, e publicar o resultado como arquivo estatico.

O QUE ESTA VERSAO ACRESCENTA
----------------------------
Antes, quem nao tinha estatistica na temporada simplesmente NAO EXISTIA para o
sistema. Isso apagava dezenas de jogadores das suas ligas e produzia tres
distorcoes: folha salarial subestimada (chegava a 38% de erro numa franquia),
idade media enviesada e elencos incapazes de montar escalacao valida.

Agora TODO jogador presente em elencos.json entra no arquivo final. Quem nao tem
estatistica recebe uma PROJECAO, sempre marcada com `projetado: true`:

  1. NOVATOS        -> projecao pela posicao no draft (decaimento logaritmico,
                       calibrado empiricamente com drafts anteriores)
  2. VOLTA DE LESAO -> ultima temporada completa, com desconto de recuperacao
  3. SEM INFORMACAO -> entra sem rating, apenas para salario/idade/elenco

COMO USAR
---------
    python gerar_dados.py
"""

import json
import math
import os
import sys
import unicodedata
from datetime import datetime, timezone

import numpy as np

try:
    from nba_api.stats.endpoints import (
        leaguedashplayerstats, playerindex, playergamelogs, drafthistory,
        commonplayerinfo
    )
    from nba_api.stats.static import players as players_static
except ImportError:
    print("ERRO: nba_api nao instalado. Rode:  pip install -r requirements.txt")
    sys.exit(1)

# Temporada estatistica usada por TODAS as consultas. Em agosto de 2026,
# 2025-26 e a ultima temporada completa. Mantenha este valor explicito: os
# endpoints da nba_api possuem defaults proprios que mudam a cada versao.
TEMPORADA = '2025-26'
ARQUIVO_SAIDA = 'dados.json'
ARQUIVO_ELENCOS = 'elencos.json'
ARQUIVO_HASHTAG = 'hashtag_projecoes_2026_27.json'

CATEGORIAS = ['pts', 'reb', 'ast', 'stl', 'blk', 'fg3m', 'tov']

# ---------------------------------------------------------------------------
# HISTORICO DE 3 TEMPORADAS
#
# Cada temporada tem seu Z-Score calculado contra a POPULACAO DAQUELE ANO, e
# nao contra a media atual. Isso e essencial: a liga inteira muda de patamar
# de um ano para outro (ritmo de jogo, volume de arremessos de 3), e comparar
# estatistica bruta entre temporadas confundiria evolucao do jogador com
# inflacao da liga. Em Z-Score, "+1.0 em 2022" e "+1.0 em 2024" significam a
# mesma coisa: um desvio-padrao acima dos pares daquele ano.
#
# LIMITE HONESTO DE 3 PONTOS
# Com 3 temporadas igualmente espacadas, a inclinacao da regressao linear e
# exatamente (ultimo - primeiro)/2: o ponto do meio NAO afeta a inclinacao.
# Por isso reportamos duas medidas distintas:
#   - inclinacao  -> direcao e magnitude da mudanca
#   - consistencia-> se a trajetoria foi monotonica ou teve pico/vale
# Uma queda de -0.4 continua e uma queda de -0.4 com repique no meio contam
# historias diferentes, e so a segunda medida distingue as duas.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# RECORTES DE PERIODO (SPLITS)
#
# Alem da temporada inteira, o sistema guarda recortes menores. Cada recorte
# tem seu PROPRIO Z-Score, calculado contra os jogadores que atuaram NAQUELE
# periodo. Isso e o que torna a comparacao valida: um Z de +1,0 nos ultimos 15
# dias significa "um desvio-padrao acima de quem jogou nesses 15 dias", nao
# acima da media da temporada inteira.
#
# CUIDADO ESTATISTICO
# Janelas curtas tem MUITO menos jogos por jogador. Em 15 dias um jogador faz
# de 5 a 8 partidas, e o Z-Score fica dominado por ruido: uma partida atipica
# desloca a media inteira. Por isso o app exibe os jogos de cada recorte e
# marca visualmente as janelas curtas. Elas servem para detectar mudanca de
# papel ou volta de lesao, nao para avaliar valor de jogador.
#
# 'segmento' usa o parametro season_segment da API; 'dias' usa date_from.
# ---------------------------------------------------------------------------
RECORTES = [
    {'chave': 'total',   'rotulo': 'Temporada inteira',  'dias': None, 'segmento': None},
    {'chave': 'pos_asg', 'rotulo': 'Pós All-Star Game',  'dias': None, 'segmento': 'Post All-Star'},
    {'chave': 'd90',     'rotulo': 'Últimos 90 dias',    'dias': 90,   'segmento': None},
    {'chave': 'd60',     'rotulo': 'Últimos 60 dias',    'dias': 60,   'segmento': None},
    {'chave': 'd30',     'rotulo': 'Último mês',         'dias': 30,   'segmento': None},
    {'chave': 'd15',     'rotulo': 'Últimos 15 dias',    'dias': 15,   'segmento': None},
]

# Minimo de jogadores qualificados para um recorte ser considerado utilizavel.
# Fora de temporada, "ultimos 15 dias" volta vazio: melhor desabilitar o
# recorte do que exibir um Z-Score calculado sobre 3 jogadores.
MIN_JOGADORES_RECORTE = 40

# Cinco temporadas dao uma leitura de carreira, nao so de momento: cobrem
# entrada na liga, pico e inicio de declinio para a maioria dos jogadores.
# O custo sao 4 requisicoes extras a API por geracao.
TEMPORADAS_HISTORICO = 5

# Limiar para classificar tendencia, em Z por temporada.
LIMIAR_TENDENCIA = 0.15

# Minimo de jogos para a temporada ser considerada informativa.
# Abaixo disso o dado entra no grafico mas nao pesa na classificacao.
GP_MINIMO_CONFIAVEL = 25

# ---------------------------------------------------------------------------
# CALIBRACAO DA PROJECAO DE NOVATOS
#
# A literatura de avaliacao de draft converge para um decaimento LOGARITMICO do
# valor esperado conforme a posicao da escolha (formulas do tipo
# EV = a + b*ln(pick)). Usamos a mesma forma funcional, porem na escala de
# Z-Score do proprio sistema, para que a projecao seja comparavel ao resto.
#
# O script tenta CALIBRAR esses coeficientes com dados reais (drafts passados +
# temporada de estreia de cada escolhido). Se a calibracao falhar, caem os
# valores abaixo, que sao estimativas conservadoras.
#
# IMPORTANTE: o intercepto e negativo de proposito. Novatos tipicamente produzem
# ABAIXO da media da liga; um Z projetado positivo seria irrealista mesmo para a
# primeira escolha. Incluir novatos tende a REDUZIR o score de profundidade de
# times jovens, e esse e o resultado correto, nao um defeito do modelo.
# ---------------------------------------------------------------------------
NOVATO_A_PADRAO = -0.12       # Z esperado do pick 1
NOVATO_B_PADRAO = -0.14       # inclinacao por ln(pick)
NOVATO_DESVIO_PADRAO = 0.45   # dispersao tipica em torno da projecao
ANOS_CALIBRACAO = [2018, 2019, 2020, 2021, 2022, 2023]

# ---------------------------------------------------------------------------
# DESCONTOS DE RETORNO DE LESAO
#
# Base empirica (estudos de NBA sobre reconstrucao de LCA):
#  - eficiencia no 1o ano de volta caiu cerca de 19% frente ao pre-lesao
#  - no 2o ano nao houve diferenca significativa frente ao pre-lesao
#  - a disponibilidade caiu MUITO mais que a producao: 48,4% dos jogos no 1o ano
#    e 62,1% no 2o, contra 78,5% na temporada anterior a lesao
#
# Por isso producao e disponibilidade sao fatores SEPARADOS: o jogador volta
# produzindo quase tao bem por jogo, mas jogando bem menos jogos.
# Aquiles tem prognostico pior, com perda relevante mesmo apos duas temporadas.
# ---------------------------------------------------------------------------
FATORES_LESAO = {
    'LCA':     {1: {'prod': 0.81, 'disp': 0.62}, 2: {'prod': 0.97, 'disp': 0.79}},
    'AQUILES': {1: {'prod': 0.70, 'disp': 0.55}, 2: {'prod': 0.85, 'disp': 0.72}},
    'OUTRA':   {1: {'prod': 0.90, 'disp': 0.75}, 2: {'prod': 1.00, 'disp': 0.90}},
}


def normalizar_nome(nome):
    if not nome:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', nome)
        if unicodedata.category(c) != 'Mn'
    ).lower().strip()


# Sufixos de geracao, que aparecem de forma inconsistente entre a base da NBA
# e as exportacoes das ligas.
SUFIXOS = ('jr', 'sr', 'ii', 'iii', 'iv', 'v')


def chave_join(nome):
    """
    Chave usada para CASAR o mesmo jogador entre fontes diferentes.

    O problema que isso resolve: a base da NBA e o CSV das ligas discordam sobre
    sufixos de geracao, e discordam nos DOIS sentidos. O CSV traz
    "Terrence Shannon Jr." enquanto a NBA traz "Terrence Shannon"; e traz
    "Bobby Portis" enquanto a NBA traz "Bobby Portis Jr.". Comparando as chaves
    cruas, o jogador nao casava e o sistema criava DUAS entradas para ele: uma
    com as estatisticas reais e outra projetada, como se nao tivesse jogado.

    Aqui removemos pontuacao e sufixo para efeito de comparacao. O nome exibido
    continua sendo o original; isto e apenas a chave de juncao.
    """
    base = normalizar_nome(nome).replace('.', '').replace(',', '')
    partes = base.split()
    while len(partes) > 2 and partes[-1] in SUFIXOS:
        partes.pop()
    return ' '.join(partes)


def carregar_banco_fantasy():
    """
    Devolve tres mapas indexados pelo nome normalizado:
      mapa_times    -> { jogador: { liga: franquia } }
      mapa_salarios -> { jogador: { liga: { ano: valor } } }
      mapa_meta     -> { jogador: { draft_pick, idade, lesao, ano_retorno, nome_original } }
    """
    mapa_times, mapa_salarios, mapa_meta = {}, {}, {}
    mapa_picks = {}
    if not os.path.exists(ARQUIVO_ELENCOS):
        print(f"AVISO: {ARQUIVO_ELENCOS} nao encontrado.")
        return mapa_times, mapa_salarios, mapa_meta, mapa_picks

    with open(ARQUIVO_ELENCOS, 'r', encoding='utf-8') as f:
        dados_ligas = json.load(f)

    for liga, franquias in dados_ligas.items():
        for nome_franquia, conteudo in franquias.items():
            if isinstance(conteudo, list):
                itens = {n: {} for n in conteudo}
            else:
                itens = conteudo.get('jogadores', {})
                if isinstance(itens, list):
                    itens = {n: {} for n in itens}
                # Livro-razao de picks da franquia
                if conteudo.get('picks'):
                    mapa_picks.setdefault(liga, {})[nome_franquia] = conteudo['picks']

            for jogador, meta in itens.items():
                chave = normalizar_nome(jogador)
                mapa_times.setdefault(chave, {})[liga] = nome_franquia
                registro = mapa_meta.setdefault(chave, {'nome_original': jogador})
                if isinstance(meta, dict):
                    if meta.get('salarios'):
                        mapa_salarios.setdefault(chave, {})[liga] = meta['salarios']
                    for campo in ('draft_pick', 'idade', 'lesao', 'ano_retorno', 'posicao'):
                        if meta.get(campo) is not None and campo not in registro:
                            registro[campo] = meta[campo]

    return mapa_times, mapa_salarios, mapa_meta, mapa_picks


def aplicar_fallback_hashtag(lista):
    """Prioriza Hashtag quando a NBA não trouxe produção para o jogador.

    A projeção interna (novato/lesão) continua sendo construída normalmente e
    funciona como terceira fonte. Quando existe correspondência no Hashtag ela
    substitui essa estimativa, estabelecendo a ordem NBA -> Hashtag -> app.
    O rating copiado não contém o bônus de GP, pois o frontend aplica esse
    mesmo bônus de disponibilidade ao carregar a base.
    """
    if not os.path.exists(ARQUIVO_HASHTAG):
        return {'hashtag': 0, 'app': sum(1 for j in lista if j.get('projetado'))}
    try:
        with open(ARQUIVO_HASHTAG, 'r', encoding='utf-8') as f:
            pacote = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"AVISO: fallback Hashtag indisponivel: {exc}")
        return {'hashtag': 0, 'app': sum(1 for j in lista if j.get('projetado'))}

    mapa = {}
    for p in pacote.get('jogadores', []):
        for nome in (p.get('nome_app'), p.get('nome')):
            if nome:
                mapa.setdefault(normalizar_nome(nome), p)
                mapa.setdefault(chave_join(nome), p)

    contagem = {'hashtag': 0, 'app': 0}
    data_fonte = pacote.get('metadados', {}).get('atualizado_na_fonte', 'nao informada')
    for jogador in lista:
        if not jogador.get('projetado'):
            jogador['fonte_estatistica'] = 'nba'
            continue
        p = mapa.get(normalizar_nome(jogador.get('nome'))) or mapa.get(chave_join(jogador.get('nome')))
        if not p:
            jogador['fonte_estatistica'] = 'projecao_app'
            contagem['app'] += 1
            continue
        jogador['gp'] = p.get('gp', 0)
        jogador['min'] = p.get('min', 0)
        for c in CATEGORIAS:
            jogador[c] = p.get(c, 0)
            jogador[f'z_{c}'] = p.get(f'z_{c}', 0)
            jogador[f'z_pm_{c}'] = p.get(f'z_{c}', 0)
        jogador['rating'] = p.get('rating_7cat')
        jogador['rating_pm'] = p.get('rating_7cat')
        jogador['posicao'] = p.get('posicao') or jogador.get('posicao') or 'N/D'
        jogador['time'] = p.get('time_nba') or jogador.get('time') or 'N/D'
        jogador['tipo_projecao'] = 'hashtag'
        jogador['origem_projecao'] = 'Hashtag Basketball 2026-27 (fallback)'
        jogador['fonte_estatistica'] = 'hashtag_fallback'
        jogador['modo_minuto_indisponivel'] = True
        jogador['detalhe_projecao'] = (
            f"Sem producao NBA. Projecao Hashtag 2026-27 atualizada em {data_fonte}."
        )
        contagem['hashtag'] += 1
    return contagem


def calcular_medias_desvios(linhas, idx):
    vals = {c: [l[idx[c]] for l in linhas] for c in CATEGORIAS}
    med = {c: float(np.mean(vals[c])) for c in CATEGORIAS}
    dev = {c: (float(np.std(vals[c])) or 1.0) for c in CATEGORIAS}
    return med, dev


def rating_de_linha(linha, idx, med, dev):
    """Media dos 7 Z-Scores, com TOV invertido (menos e melhor)."""
    z = []
    for c in CATEGORIAS:
        valor = (linha[idx[c]] - med[c]) / dev[c]
        z.append(-valor if c == 'tov' else valor)
    return float(np.mean(z))


def calibrar_curva_novatos():
    """
    Regressao Z_estreia = a + b*ln(pick) usando drafts passados.
    Devolve (a, b, desvio, n_amostras, origem).
    """
    print("Calibrando curva de novatos com drafts anteriores...")
    pontos = []

    for ano in ANOS_CALIBRACAO:
        temporada_estreia = f"{ano}-{str(ano + 1)[-2:]}"
        try:
            draft = drafthistory.DraftHistory(
                season_year_nullable=str(ano)).get_dict()['resultSets'][0]
            h = draft['headers']
            i_nome, i_pick = h.index('PLAYER_NAME'), h.index('OVERALL_PICK')
            escolhidos = {normalizar_nome(l[i_nome]): l[i_pick]
                          for l in draft['rowSet'] if l[i_pick]}

            stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season=temporada_estreia, per_mode_detailed='PerGame'
            ).get_dict()['resultSets'][0]
            sh, sl = stats['headers'], stats['rowSet']
            idx = {c: sh.index(c.upper()) for c in CATEGORIAS}
            i_min, i_nm = sh.index('MIN'), sh.index('PLAYER_NAME')

            qualificados = [l for l in sl if l[i_min] >= 10]
            if len(qualificados) < 50:
                continue
            med, dev = calcular_medias_desvios(qualificados, idx)

            for l in qualificados:
                chave = normalizar_nome(l[i_nm])
                if chave in escolhidos:
                    pick = escolhidos[chave]
                    if 1 <= pick <= 60:
                        pontos.append((math.log(pick), rating_de_linha(l, idx, med, dev)))
        except Exception as e:
            print(f"  aviso: draft {ano} indisponivel ({type(e).__name__})")

    if len(pontos) < 30:
        print(f"  amostra insuficiente ({len(pontos)}). Usando coeficientes padrao.")
        return NOVATO_A_PADRAO, NOVATO_B_PADRAO, NOVATO_DESVIO_PADRAO, len(pontos), 'padrao'

    x = np.array([p[0] for p in pontos])
    y = np.array([p[1] for p in pontos])
    b, a = np.polyfit(x, y, 1)
    desvio = float(np.std(y - (a + b * x)))
    print(f"  calibrado com {len(pontos)} novatos: "
          f"Z = {a:.3f} {b:+.3f}*ln(pick), desvio {desvio:.3f}")
    return float(a), float(b), desvio, len(pontos), 'calibrado'


def projetar_novato(pick, a, b, desvio):
    """Projecao pontual + faixa interquartil (+-0,674 desvios)."""
    pick = max(1, min(int(pick), 60))
    z = a + b * math.log(pick)
    return {
        'rating': round(z, 3),
        'p25': round(z - 0.674 * desvio, 3),
        'p75': round(z + 0.674 * desvio, 3),
    }


def buscar_posicoes_temporada(temporada):
    """Mapa de posicoes exatamente como registradas na temporada informada."""
    mapa = {}
    try:
        dados = playerindex.PlayerIndex(
            season=temporada, historical_nullable='1'
        ).get_dict()['resultSets'][0]
        h = dados['headers']
        i_fn = h.index('PLAYER_FIRST_NAME')
        i_ln = h.index('PLAYER_LAST_NAME')
        i_pos = h.index('POSITION')
        for linha in dados['rowSet']:
            posicao = linha[i_pos]
            if not posicao:
                continue
            nome = f"{linha[i_fn]} {linha[i_ln]}".strip()
            mapa[normalizar_nome(nome)] = posicao
            mapa[chave_join(nome)] = posicao
    except Exception as e:
        print(f"  aviso: posicoes de {temporada} indisponiveis ({type(e).__name__})")
    return mapa


def buscar_temporada_anterior(temporadas_atras=1):
    """Base para projetar quem voltou de lesao."""
    ano = int(TEMPORADA.split('-')[0]) - temporadas_atras
    alvo = f"{ano}-{str(ano + 1)[-2:]}"
    try:
        stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=alvo, per_mode_detailed='PerGame'
        ).get_dict()['resultSets'][0]
        h, linhas = stats['headers'], stats['rowSet']
        idx = {c: h.index(c.upper()) for c in CATEGORIAS}
        i_min, i_nm, i_gp = h.index('MIN'), h.index('PLAYER_NAME'), h.index('GP')
        i_idade = h.index('AGE') if 'AGE' in h else None
        i_time = h.index('TEAM_ABBREVIATION') if 'TEAM_ABBREVIATION' in h else None
        qualificados = [l for l in linhas if l[i_min] >= 10]
        med, dev = calcular_medias_desvios(qualificados, idx)
        mapa_posicoes = buscar_posicoes_temporada(alvo)
        mapa = {}
        for l in qualificados:
            nome = l[i_nm]
            chave = normalizar_nome(nome)
            registro = {
                'rating': rating_de_linha(l, idx, med, dev),
                'gp': l[i_gp], 'min': l[i_min],
                'idade': l[i_idade] if i_idade is not None else None,
                'time': l[i_time] if i_time is not None else None,
                'posicao': (mapa_posicoes.get(chave)
                            or mapa_posicoes.get(chave_join(nome))),
                'stats': {c: l[idx[c]] for c in CATEGORIAS},
                'temporada': alvo,
                'anos_atras': temporadas_atras,
            }
            mapa[chave] = registro
            mapa.setdefault(chave_join(nome), registro)
        print(f"  temporada {alvo}: {len(qualificados)} jogadores disponiveis como base")
        return mapa
    except Exception as e:
        print(f"  aviso: temporada {alvo} indisponivel ({type(e).__name__})")
        return {}


def temporada_anterior(temporada, passos):
    """'2024-25' com passos=1 -> '2023-24'"""
    ano = int(temporada.split('-')[0]) - passos
    return f"{ano}-{str(ano + 1)[-2:]}"


def coletar_historico():
    """
    Devolve { nome_normalizado: [ {temporada, rating, gp, min, cats...}, ... ] }
    com as temporadas em ordem cronologica (mais antiga primeiro).

    Cada temporada e padronizada contra a propria populacao daquele ano.
    """
    historico = {}
    temporadas = [temporada_anterior(TEMPORADA, i)
                  for i in range(TEMPORADAS_HISTORICO - 1, 0, -1)]

    for temp in temporadas:
        try:
            res = leaguedashplayerstats.LeagueDashPlayerStats(
                season=temp, per_mode_detailed='PerGame'
            ).get_dict()['resultSets'][0]
            h, linhas = res['headers'], res['rowSet']
            idx = {c: h.index(c.upper()) for c in CATEGORIAS}
            i_min, i_nm, i_gp = h.index('MIN'), h.index('PLAYER_NAME'), h.index('GP')

            qualificados = [l for l in linhas if l[i_min] >= 10]
            if len(qualificados) < 50:
                print(f"  aviso: {temp} com poucos jogadores, ignorada")
                continue

            med, dev = calcular_medias_desvios(qualificados, idx)
            for l in qualificados:
                chave = normalizar_nome(l[i_nm])
                historico.setdefault(chave, []).append({
                    'temporada': temp,
                    'rating': round(rating_de_linha(l, idx, med, dev), 3),
                    'gp': l[i_gp],
                    'min': round(l[i_min], 1),
                    **{c: l[idx[c]] for c in CATEGORIAS},
                })
            print(f"  {temp}: {len(qualificados)} jogadores")
        except Exception as e:
            print(f"  aviso: {temp} indisponivel ({type(e).__name__})")

    return historico


def analisar_tendencia(serie):
    """
    Le a trajetoria de um jogador ao longo das temporadas disponiveis.

    POR QUE ESTA FUNCAO FOI REESCRITA
    A versao anterior foi desenhada para 3 temporadas e classificava a
    consistencia como "monotonica" apenas quando a serie subia (ou caia) em
    TODOS os passos. Com 3 pontos isso ainda acontecia com alguma frequencia.
    Com 5, praticamente nenhuma carreira real e estritamente monotonica: basta
    uma temporada de oscilacao para tudo virar "erratico", e a leitura perde
    utilidade justamente onde havia mais informacao.

    Agora a trajetoria e descrita por quatro medidas independentes:

      inclinacao  direcao e magnitude, por regressao sobre TODOS os pontos
      r2          o quanto uma reta explica a trajetoria (0 a 1)
      aderencia   fracao das variacoes ano a ano que seguem a direcao geral
      forma       o desenho da curva: subida, queda, pico, vale ou plato

    Com 5 pontos a inclinacao passa a usar a serie inteira, e nao apenas as
    pontas como acontecia com 3. Ja a forma captura o que a inclinacao sozinha
    esconde: um jogador que subiu ate o meio e depois caiu pode terminar com
    inclinacao proxima de zero, e "estavel" seria uma leitura enganosa.
    """
    if not serie or len(serie) < 2:
        return {'inclinacao': None, 'r2': None, 'aderencia': None, 'forma': None,
                'consistencia': None, 'classe': 'Sem histórico',
                'confiavel': False, 'n': len(serie or []),
                'inclinacao_recente': None, 'pico_em': None, 'vale_em': None}

    ys = [p['rating'] for p in serie]
    n = len(ys)
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(ys) / n

    den = sum((x - mx) ** 2 for x in xs)
    inclinacao = (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den) if den else 0.0
    intercepto = my - inclinacao * mx

    # R2: quanto da variacao a reta explica
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (intercepto + inclinacao * x)) ** 2 for x, y in zip(xs, ys))
    r2 = (1 - ss_res / ss_tot) if ss_tot > 1e-9 else 1.0

    # Aderencia: quantos passos ano a ano seguem a direcao geral
    deltas = [ys[i + 1] - ys[i] for i in range(n - 1)]
    if abs(inclinacao) < 1e-9:
        aderencia = 0.5
    else:
        sinal = 1 if inclinacao > 0 else -1
        aderencia = sum(1 for d in deltas if (d > 0) == (sinal > 0)) / len(deltas)

    # Forma: onde estao o melhor e o pior ano
    i_max = ys.index(max(ys))
    i_min = ys.index(min(ys))
    amplitude = max(ys) - min(ys)
    meio = (n >= 3)

    # Pico e vale se distinguem por ONDE cada extremo cai. Se o melhor ano
    # esta no miolo e o pior numa ponta, a curva subiu e recuou: e um pico.
    # Se ambos os extremos estao no miolo, nao ha desenho definido, e chamar de
    # pico ou vale seria escolher arbitrariamente um dos dois.
    max_no_meio = meio and 0 < i_max < n - 1
    min_no_meio = meio and 0 < i_min < n - 1

    # Quanto o jogador recuou desde o melhor ano, e quanto se recuperou desde o
    # pior, em proporcao a amplitude total da carreira. Serve para exigir que o
    # "pico" seja um recuo de verdade, e nao uma desaceleracao no fim.
    recuo = (ys[i_max] - ys[-1]) / amplitude if amplitude > 1e-9 else 0
    recuperacao = (ys[-1] - ys[i_min]) / amplitude if amplitude > 1e-9 else 0
    RECUO_MINIMO = 0.35

    direcao_clara = abs(inclinacao) >= LIMIAR_TENDENCIA

    if amplitude < 0.25:
        forma = 'plato'
    # Pico e vale so prevalecem quando NAO ha direcao clara. Com inclinacao
    # forte, a direcao e a informacao principal: uma carreira que subiu muito e
    # apenas desacelerou no ultimo ano continua sendo uma ascensao, e uma que
    # despencou continua sendo um declinio, ainda que o melhor ano esteja no
    # miolo da serie.
    elif max_no_meio and not min_no_meio and not direcao_clara and recuo >= RECUO_MINIMO:
        forma = 'pico'
    elif min_no_meio and not max_no_meio and not direcao_clara and recuperacao >= RECUO_MINIMO:
        forma = 'vale'
    elif inclinacao >= LIMIAR_TENDENCIA:
        forma = 'subida'
    elif inclinacao <= -LIMIAR_TENDENCIA:
        forma = 'queda'
    else:
        forma = 'oscilante'

    # Tendencia recente: ultimas 3 temporadas, para separar carreira de momento
    inclinacao_recente = None
    if n >= 4:
        ult = ys[-3:]
        mxr = 1.0
        myr = sum(ult) / 3
        denr = sum((x - mxr) ** 2 for x in range(3))
        inclinacao_recente = sum((x - mxr) * (y - myr)
                                 for x, y in zip(range(3), ult)) / denr

    confiavel = all(p['gp'] >= GP_MINIMO_CONFIAVEL for p in serie)

    # A classe segue a FORMA quando existe um desenho claro. Um jogador que
    # subiu e recuou termina com inclinacao proxima de zero, e rotula-lo de
    # "Estavel" seria a leitura mais enganosa possivel.
    if forma == 'pico':
        classe = 'Pico e recuo'
    elif forma == 'vale':
        classe = 'Recuperação'
    elif forma == 'plato':
        classe = 'Platô'
    elif forma == 'oscilante':
        classe = 'Oscilante'
    elif inclinacao >= LIMIAR_TENDENCIA:
        classe = 'Ascensão'
    elif inclinacao <= -LIMIAR_TENDENCIA:
        classe = 'Declínio'
    else:
        classe = 'Estável'

    # Qualificador vem da aderencia e da linearidade, nao de monotonicidade
    if forma in ('subida', 'queda'):
        if aderencia >= 0.99:
            classe += ' contínua'
        elif aderencia >= 0.6 and r2 >= 0.7:
            classe += ' firme'
        elif r2 < 0.4:
            classe += ' irregular'

    if not confiavel:
        classe += ' (amostra curta)'

    return {
        'inclinacao': round(inclinacao, 3),
        'r2': round(r2, 3),
        'aderencia': round(aderencia, 2),
        'forma': forma,
        # mantido por compatibilidade com versoes anteriores do frontend
        'consistencia': 'monotonica' if aderencia >= 0.99 else 'erratica',
        'classe': classe,
        'confiavel': confiavel,
        'n': n,
        'inclinacao_recente': round(inclinacao_recente, 3) if inclinacao_recente is not None else None,
        'pico_em': serie[i_max]['temporada'],
        'vale_em': serie[i_min]['temporada'],
    }


def inclinacao_esperada_por_idade(idade):
    """
    Variacao anual de Z que a curva de envelhecimento sozinha explicaria.
    Serve para separar "esta caindo porque envelheceu" de "esta caindo mais do
    que a idade justifica", que e um sinal bem diferente para o GM.

    Derivado da mesma curva usada no rating dynasty.
    """
    if idade is None:
        return None
    if idade <= 22:
        return 0.18
    if idade <= 24:
        return 0.12
    if idade <= 26:
        return 0.05
    if idade <= 29:
        return 0.0
    if idade <= 31:
        return -0.08
    if idade <= 33:
        return -0.15
    return -0.22


def coletar_recorte(recorte):
    """
    Busca as estatisticas de um recorte e devolve
    { nome_normalizado: {rating, rating_pm, gp, min, cats, z_*, z_pm_*} }
    com Z-Score calculado contra a populacao do proprio recorte.

    Devolve (dados, info) onde info traz rotulo, periodo e disponibilidade.
    """
    from datetime import date, timedelta

    params = {'season': TEMPORADA, 'per_mode_detailed': 'PerGame'}
    descricao = recorte['rotulo']

    if recorte['segmento']:
        params['season_segment_nullable'] = recorte['segmento']
    if recorte['dias']:
        inicio = date.today() - timedelta(days=recorte['dias'])
        params['date_from_nullable'] = inicio.strftime('%m/%d/%Y')
        descricao += f" (desde {inicio.strftime('%d/%m/%Y')})"

    try:
        res = leaguedashplayerstats.LeagueDashPlayerStats(**params).get_dict()['resultSets'][0]
    except Exception as e:
        print(f"  {recorte['chave']:8} indisponivel ({type(e).__name__})")
        return {}, {'chave': recorte['chave'], 'rotulo': recorte['rotulo'],
                    'descricao': descricao, 'disponivel': False, 'n': 0}

    h, linhas = res['headers'], res['rowSet']
    idx = {c: h.index(c.upper()) for c in CATEGORIAS}
    i_min, i_nm, i_gp = h.index('MIN'), h.index('PLAYER_NAME'), h.index('GP')

    # Em janelas curtas o corte de 10 minutos por jogo continua valendo, mas
    # exigimos tambem pelo menos 1 jogo para nao entrar quem so tem linha vazia.
    qualificados = [l for l in linhas if l[i_min] >= 10 and l[i_gp] >= 1]

    if len(qualificados) < MIN_JOGADORES_RECORTE:
        print(f"  {recorte['chave']:8} apenas {len(qualificados)} jogadores, desabilitado")
        return {}, {'chave': recorte['chave'], 'rotulo': recorte['rotulo'],
                    'descricao': descricao, 'disponivel': False, 'n': len(qualificados)}

    med, dev = calcular_medias_desvios(qualificados, idx)
    vals_pm = {c: [l[idx[c]] / l[i_min] for l in qualificados] for c in CATEGORIAS}
    med_pm = {c: float(np.mean(vals_pm[c])) for c in CATEGORIAS}
    dev_pm = {c: (float(np.std(vals_pm[c])) or 0.001) for c in CATEGORIAS}

    dados = {}
    for l in qualificados:
        z = {c: ((l[idx[c]] - med[c]) / dev[c]) * (-1 if c == 'tov' else 1) for c in CATEGORIAS}
        z_pm = {c: ((l[idx[c]] / l[i_min] - med_pm[c]) / dev_pm[c]) * (-1 if c == 'tov' else 1)
                for c in CATEGORIAS}
        dados[normalizar_nome(l[i_nm])] = {
            'gp': l[i_gp], 'min': round(l[i_min], 1),
            **{c: l[idx[c]] for c in CATEGORIAS},
            **{f'z_{c}': round(z[c], 3) for c in CATEGORIAS},
            **{f'z_pm_{c}': round(z_pm[c], 3) for c in CATEGORIAS},
            'rating': round(float(np.mean(list(z.values()))), 3),
            'rating_pm': round(float(np.mean(list(z_pm.values()))), 3),
        }

    # jogos medios do recorte, util para o app avisar sobre ruido
    media_gp = sum(d['gp'] for d in dados.values()) / len(dados)
    print(f"  {recorte['chave']:8} {len(dados):4} jogadores | media de {media_gp:.1f} jogos")

    return dados, {'chave': recorte['chave'], 'rotulo': recorte['rotulo'],
                   'descricao': descricao, 'disponivel': True,
                   'n': len(dados), 'media_gp': round(media_gp, 1)}


def resgatar_posicoes(nomes_sem_posicao):
    """
    Ultima fonte de posicao para quem nao aparece no PlayerIndex.

    Quem passou a temporada inteira afastado costuma nao constar no indice de
    jogadores ativos da NBA. Sem posicao, esse jogador nao consegue ocupar vaga
    na escalacao valida e some das analises de forca, mesmo tendo rating
    projetado. E por isso que este resgate existe.

    Estrategia em duas etapas:
      1. `players_static` e uma lista LOCAL do nba_api, sem chamada de rede,
         que cobre jogadores ativos e inativos. Serve para achar o ID.
      2. `commonplayerinfo` devolve a posicao. E uma chamada por jogador, por
         isso so roda para os que sobraram, tipicamente menos de vinte.
    """
    if not nomes_sem_posicao:
        return {}

    print(f"Resgatando posicao de {len(nomes_sem_posicao)} jogador(es) sem registro ativo...")
    encontrados = {}
    LIMITE = 40   # trava de seguranca contra excesso de chamadas

    for i, nome in enumerate(sorted(nomes_sem_posicao)[:LIMITE]):
        try:
            achados = players_static.find_players_by_full_name(nome)
            if not achados:
                # tenta sem sufixo de geracao
                achados = players_static.find_players_by_full_name(chave_join(nome))
            if not achados:
                continue
            pid = achados[0]['id']
            info = commonplayerinfo.CommonPlayerInfo(player_id=pid).get_dict()['resultSets'][0]
            idx = info['headers'].index('POSITION')
            pos = info['rowSet'][0][idx] if info['rowSet'] else None
            if pos:
                encontrados[normalizar_nome(nome)] = pos
                print(f"  {nome}: {pos}")
        except Exception as e:
            print(f"  {nome}: falhou ({type(e).__name__})")

    if len(nomes_sem_posicao) > LIMITE:
        print(f"  aviso: {len(nomes_sem_posicao) - LIMITE} jogador(es) alem do limite, nao consultados")
    return encontrados


def testar_conexao():
    print("Testando acesso ao stats.nba.com...")
    try:
        leaguedashplayerstats.LeagueDashPlayerStats(
            season=TEMPORADA, per_mode_detailed='PerGame', timeout=20)
        print("  OK\n")
        return True
    except Exception as e:
        print("  FALHA ao acessar stats.nba.com.")
        print(f"  {type(e).__name__}: {e}\n")
        print("  Causas provaveis:")
        print("   - rodando em servidor/nuvem (IP de datacenter bloqueado)")
        print("   - VPN ativa (saida por datacenter). Desligue e tente de novo.")
        print("   - instabilidade momentanea. Tente em alguns minutos.")
        return False


def gerar():
    if not testar_conexao():
        sys.exit(1)

    print("Baixando estatisticas da temporada...")
    res = leaguedashplayerstats.LeagueDashPlayerStats(
        season=TEMPORADA,
        per_mode_detailed='PerGame').get_dict()['resultSets'][0]
    headers, linhas = res['headers'], res['rowSet']

    idx = {c: headers.index(c.upper()) for c in CATEGORIAS}
    i_nome = headers.index('PLAYER_NAME')
    i_min = headers.index('MIN')
    i_idade = headers.index('AGE')
    i_time = headers.index('TEAM_ABBREVIATION')
    i_gp = headers.index('GP')
    i_pid = headers.index('PLAYER_ID')

    print("Baixando matriz de posicoes...")
    mapa_pos = {}
    try:
        dp = playerindex.PlayerIndex(
            season=TEMPORADA, historical_nullable='1'
        ).get_dict()['resultSets'][0]
        ph = dp['headers']
        i_fn, i_ln, i_pos = (ph.index('PLAYER_FIRST_NAME'),
                             ph.index('PLAYER_LAST_NAME'), ph.index('POSITION'))
        for l in dp['rowSet']:
            if l[i_pos]:
                mapa_pos[normalizar_nome(f"{l[i_fn]} {l[i_ln]}")] = l[i_pos]
    except Exception as e:
        print(f"  aviso: posicoes indisponiveis ({e})")

    print("Baixando logs de jogo para variancia...")
    std_dict = {}
    try:
        logs = playergamelogs.PlayerGameLogs(season_nullable=TEMPORADA).get_data_frames()[0]
        sdf = logs.groupby('PLAYER_ID')[['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M', 'TOV']] \
                  .std().reset_index().fillna(0.0)
        std_dict = sdf.set_index('PLAYER_ID').to_dict('index')
    except Exception as e:
        print(f"  aviso: variancia indisponivel ({e})")

    filt = [l for l in linhas if l[i_min] >= 10]
    print(f"  {len(filt)} jogadores com 10+ minutos por jogo")

    med, dev = calcular_medias_desvios(filt, idx)
    vals_pm = {c: [l[idx[c]] / l[i_min] for l in filt] for c in CATEGORIAS}
    med_pm = {c: float(np.mean(vals_pm[c])) for c in CATEGORIAS}
    dev_pm = {c: (float(np.std(vals_pm[c])) or 0.001) for c in CATEGORIAS}

    print("\nColetando recortes de periodo...")
    recortes_dados, recortes_info = {}, []
    for rec in RECORTES:
        if rec['chave'] == 'total':
            recortes_info.append({'chave': 'total', 'rotulo': rec['rotulo'],
                                  'descricao': rec['rotulo'], 'disponivel': True,
                                  'n': len(filt)})
            continue
        d, info = coletar_recorte(rec)
        recortes_info.append(info)
        if info['disponivel']:
            recortes_dados[rec['chave']] = d

    print("\nColetando historico de temporadas anteriores...")
    historico = coletar_historico()

    mapa_times, mapa_salarios, mapa_meta, mapa_picks = carregar_banco_fantasy()

    # ---------- jogadores COM estatistica ----------
    lista, vistos = [], set()
    for l in filt:
        nome = l[i_nome]
        chave = normalizar_nome(nome)
        # Registra a chave exata E a tolerante a sufixo, para que o jogador seja
        # reconhecido depois independentemente de como o CSV o escreveu.
        vistos.add(chave)
        vistos.add(chave_join(nome))

        z = {c: ((l[idx[c]] - med[c]) / dev[c]) * (-1 if c == 'tov' else 1)
             for c in CATEGORIAS}
        z_pm = {c: ((l[idx[c]] / l[i_min] - med_pm[c]) / dev_pm[c]) * (-1 if c == 'tov' else 1)
                for c in CATEGORIAS}
        var = std_dict.get(l[i_pid], {})

        lista.append({
            'nome': nome,
            # Busca pela chave exata; se nao achar, tenta a versao sem sufixo,
            # cobrindo a discordancia de grafia entre NBA e CSV das ligas.
            'status_fantasy': mapa_times.get(chave) or mapa_times.get(chave_join(nome), {}),
            'salarios_fantasy': mapa_salarios.get(chave) or mapa_salarios.get(chave_join(nome), {}),
            'posicao': mapa_pos.get(chave) or mapa_pos.get(chave_join(nome), 'N/D'),
            'idade': l[i_idade], 'time': l[i_time], 'gp': l[i_gp], 'min': l[i_min],
            **{c: l[idx[c]] for c in CATEGORIAS},
            **{f'z_{c}': z[c] for c in CATEGORIAS},
            **{f'z_pm_{c}': z_pm[c] for c in CATEGORIAS},
            'rating': round(float(np.mean(list(z.values()))), 3),
            'rating_pm': round(float(np.mean(list(z_pm.values()))), 3),
            **{f'desvio_{c}': float(var.get(c.upper(), 0.0)) for c in CATEGORIAS},
            'projetado': False,
        })

        # Recortes de periodo. O recorte 'total' NAO e duplicado aqui: ele ja
        # esta nos campos de topo do jogador, que sao o estado padrao do app.
        splits = {}
        for ch, mapa in recortes_dados.items():
            if chave in mapa:
                splits[ch] = mapa[chave]
        if splits:
            lista[-1]['splits'] = splits

        # Historico: temporadas anteriores + a atual, em ordem cronologica
        serie = list(historico.get(chave, []))
        serie.append({
            'temporada': TEMPORADA,
            'rating': lista[-1]['rating'],
            'gp': l[i_gp], 'min': round(l[i_min], 1),
            **{c: l[idx[c]] for c in CATEGORIAS},
        })
        lista[-1]['historico'] = serie
        lista[-1]['tendencia'] = analisar_tendencia(serie)
        lista[-1]['tendencia']['esperado_idade'] = inclinacao_esperada_por_idade(l[i_idade])

    # ---------- jogadores SEM estatistica: projecao ----------
    print("\nProjetando jogadores sem estatistica na temporada...")
    a, b, desvio_novato, n_amostra, origem = calibrar_curva_novatos()
    # Procura a ultima temporada EFETIVAMENTE jogada, nao apenas o ano anterior.
    # A primeira ocorrencia vence, portanto um jogador ausente por duas temporadas
    # recebe a posicao e a base estatistica do ano mais recente em que atuou.
    anterior = {}
    for temporadas_atras in range(1, 4):
        mapa_ano = buscar_temporada_anterior(temporadas_atras)
        for chave_ant, dados_ant in mapa_ano.items():
            anterior.setdefault(chave_ant, dados_ant)

    # Quem entrou no elenco mas nao tem posicao em nenhuma fonte conhecida
    sem_posicao = []
    for chave, ligas in mapa_times.items():
        if chave in vistos or chave_join(chave) in vistos:
            continue
        if mapa_pos.get(chave) or mapa_pos.get(chave_join(chave)):
            continue
        meta_j = mapa_meta.get(chave, {})
        if meta_j.get('posicao'):
            continue
        sem_posicao.append(meta_j.get('nome_original', chave))

    posicoes_resgatadas = resgatar_posicoes(sem_posicao)

    contagem = {'novato': 0, 'lesao': 0, 'sem_base': 0}

    for chave, ligas in mapa_times.items():
        # Casa por chave exata OU por chave sem sufixo. Sem isso, variacoes como
        # "Jr." presentes so de um lado geravam um segundo registro fantasma.
        if chave in vistos or chave_join(chave) in vistos:
            continue
        meta = mapa_meta.get(chave, {})
        nome = meta.get('nome_original', chave.title())

        base = {
            'nome': nome,
            'status_fantasy': ligas,
            'salarios_fantasy': mapa_salarios.get(chave, {}),
            # PlayerIndex atual primeiro; a posicao historica do lesionado e
            # aplicada logo abaixo, assim que sua ultima temporada e conhecida.
            'posicao': (mapa_pos.get(chave) or mapa_pos.get(chave_join(chave))
                        or posicoes_resgatadas.get(chave)
                        or posicoes_resgatadas.get(normalizar_nome(nome))
                        or (str(meta['posicao']).replace('/', '-')
                            if meta.get('posicao') else 'N/D')),
            'idade': meta.get('idade'),
            'time': 'N/D', 'gp': 0, 'min': 0,
            'posicao_csv': meta.get('posicao'),
            **{c: 0 for c in CATEGORIAS},
            **{f'z_{c}': 0 for c in CATEGORIAS},
            **{f'z_pm_{c}': 0 for c in CATEGORIAS},
            **{f'desvio_{c}': 0.0 for c in CATEGORIAS},
            'rating': None, 'rating_pm': None,
            'projetado': True,
            'origem_projecao': None,
        }

        # 1) RETORNO DE AFASTAMENTO
        #
        # DETECCAO AUTOMATICA: antes esta projecao so acontecia se a coluna
        # 'lesao' estivesse preenchida no CSV. Na pratica ninguem preenche, e
        # jogadores como Fred VanVleet acabavam zerados no sistema, sem stats,
        # sem idade e fora de todas as analises.
        #
        # Agora a regra e outra: se o jogador esta em algum elenco, NAO tem
        # estatistica nesta temporada, mas TEM temporada anterior registrada,
        # entao ele perdeu a temporada. Isso e suficiente para projeta-lo.
        # A coluna 'lesao' continua existindo, mas agora serve apenas para
        # REFINAR o desconto (LCA e Aquiles tem prognosticos diferentes).
        ant = anterior.get(chave) or anterior.get(chave_join(nome))
        if ant:
            # Sem tipo informado, usa o desconto generico, que e o mais
            # conservador dos tres. Quem quiser precisao preenche o CSV.
            tipo = str(meta.get('lesao', 'OUTRA')).upper()
            if tipo not in FATORES_LESAO:
                tipo = 'OUTRA'
            fatores = FATORES_LESAO.get(tipo, FATORES_LESAO['OUTRA'])
            ano_ret = int(meta.get('ano_retorno', 1))
            f = fatores.get(ano_ret, fatores[2])
            # Idade: projetada a partir da temporada base. Sem isso o jogador
            # aparecia com idade nula, ficava de fora da media de idade da
            # franquia e nao recebia ajuste na curva dynasty.
            if base.get('idade') in (None, 0) and ant.get('idade'):
                base['idade'] = int(ant['idade']) + int(ant.get('anos_atras', 1))

            # Posicao: para um afastado, a fonte preferida e a ultima temporada
            # em que ele realmente jogou. Isso evita depender do indice de ativos
            # atual e permite que ele ocupe corretamente uma vaga na escalacao.
            if ant.get('posicao'):
                base['posicao'] = str(ant['posicao']).replace('/', '-')
                base['origem_posicao'] = f"PlayerIndex {ant['temporada']}"
            elif base.get('posicao') in (None, '', 'N/D') and meta.get('posicao'):
                base['posicao'] = str(meta['posicao']).replace('/', '-')
                base['origem_posicao'] = 'CSV das ligas'

            # Time da NBA: usa o da ultima temporada em que atuou. E melhor que
            # 'N/D', ainda que possa estar desatualizado se ele trocou de equipe
            # durante o afastamento.
            if base.get('time') in (None, '', 'N/D') and ant.get('time'):
                base['time'] = ant['time']

            base['rating'] = round(ant['rating'] * f['prod'], 3)
            base['rating_pm'] = base['rating']
            base['gp'] = int(round(ant['gp'] * f['disp']))
            base['min'] = ant['min']
            for c in CATEGORIAS:
                base[c] = round(ant['stats'][c] * f['prod'], 1)

            # Z-Score POR CATEGORIA do jogador afastado.
            #
            # Antes so o rating geral era projetado, e os z_* ficavam zerados.
            # Isso tinha dois efeitos ruins: o mapa de calor da tabela mostrava
            # cor neutra em todas as categorias dele, e qualquer recalculo que
            # parta dos z_* (como o filtro de selecao de categorias) zerava o
            # jogador. Padronizando as stats ja descontadas contra a media da
            # temporada atual, ele passa a ter perfil por categoria coerente.
            for c in CATEGORIAS:
                sinal = -1 if c == 'tov' else 1
                base[f'z_{c}'] = round(((base[c] - med[c]) / dev[c]) * sinal, 3)
                if base['min']:
                    base[f'z_pm_{c}'] = round(
                        ((base[c] / base['min'] - med_pm[c]) / dev_pm[c]) * sinal, 3)

            base['historico'] = list(historico.get(chave, []))
            base['tendencia'] = analisar_tendencia(base['historico'])
            base['tendencia']['esperado_idade'] = inclinacao_esperada_por_idade(base.get('idade'))
            base['tipo_projecao'] = 'lesao'
            rotulo_tipo = {'LCA': 'LCA', 'AQUILES': 'tendão de Aquiles'}.get(tipo, 'afastamento')
            base['origem_projecao'] = (f"Retorno de {rotulo_tipo}, ano {ano_ret}"
                                       + ("" if meta.get('lesao') else " (detectado automaticamente)"))
            base['detalhe_projecao'] = (
                f"Base: {ant['temporada']} ({ant['rating']:+.2f} Z). "
                f"Producao x{f['prod']:.2f}, disponibilidade x{f['disp']:.2f}.")
            contagem['lesao'] += 1

        # 2) Novato com posicao de draft conhecida
        elif meta.get('draft_pick'):
            pick = int(meta['draft_pick'])
            proj = projetar_novato(pick, a, b, desvio_novato)
            base['rating'] = proj['rating']
            base['rating_pm'] = proj['rating']
            base['proj_p25'] = proj['p25']
            base['proj_p75'] = proj['p75']
            base['draft_pick'] = pick
            base['tipo_projecao'] = 'novato'
            base['origem_projecao'] = f"Novato (pick #{pick})"
            base['detalhe_projecao'] = (
                f"Projecao por posicao de draft. Faixa provavel: "
                f"{proj['p25']:+.2f} a {proj['p75']:+.2f} Z.")
            contagem['novato'] += 1

        # 3) Sem base: entra apenas para salario, idade e composicao de elenco
        else:
            base['tipo_projecao'] = 'sem_base'
            base['origem_projecao'] = 'Sem estatistica e sem base de projecao'
            contagem['sem_base'] += 1

        lista.append(base)

    # ---------- fallback e ranking ----------
    fallback = aplicar_fallback_hashtag(lista)
    print(f"  fallback Hashtag     : {fallback['hashtag']}")
    print(f"  fallback interno app : {fallback['app']}")
    com_rating = [j for j in lista if j['rating'] is not None]
    com_rating.sort(key=lambda x: x['rating'], reverse=True)
    for i, j in enumerate(com_rating):
        j['rank_absoluto'] = i + 1
    for j in lista:
        if j['rating'] is None:
            j['rank_absoluto'] = None

    saida = {
        'gerado_em': datetime.now(timezone.utc).isoformat(),
        'temporada': TEMPORADA,
        'total_jogadores': len(lista),
        'recortes': recortes_info,
        'picks': mapa_picks,
        'ordem_fallback_projecao': ['nba', 'hashtag', 'projecao_app'],
        'projecao_novatos': {
            'a': a, 'b': b, 'desvio': desvio_novato,
            'amostra': n_amostra, 'origem': origem
        },
        'jogadores': lista,
    }

    # O site aceita o JSON Hashtag separado, mas tambem guarda uma copia dentro
    # de dados.json. Assim, uma publicacao que omita acidentalmente o arquivo
    # adicional nao desabilita o seletor de fonte. O arquivo externo continua
    # util para atualizacoes independentes e retrocompatibilidade.
    if os.path.exists(ARQUIVO_HASHTAG):
        try:
            with open(ARQUIVO_HASHTAG, 'r', encoding='utf-8') as f:
                saida['hashtag_projecoes_2026_27'] = json.load(f)
            print(f"  Hashtag incorporado: {ARQUIVO_HASHTAG}")
        except (OSError, json.JSONDecodeError) as exc:
            print(f"AVISO: nao foi possivel incorporar {ARQUIVO_HASHTAG}: {exc}")

    arquivo_temporario = ARQUIVO_SAIDA + '.tmp'
    with open(arquivo_temporario, 'w', encoding='utf-8') as f:
        json.dump(saida, f, ensure_ascii=False, separators=(',', ':'))
    os.replace(arquivo_temporario, ARQUIVO_SAIDA)

    tam = os.path.getsize(ARQUIVO_SAIDA) / 1024 / 1024
    print()
    print(f"PRONTO: {ARQUIVO_SAIDA} ({tam:.1f} MB)")
    print(f"  com estatistica real : {len(filt)}")
    print(f"  novatos projetados   : {contagem['novato']}")
    print(f"  retorno de afastamento: {contagem['lesao']}")
    print(f"  sem base de projecao : {contagem['sem_base']}")
    sem_pos_final = sum(1 for j in lista if j.get('posicao') in (None, '', 'N/D'))
    if sem_pos_final:
        print(f"  ainda sem posicao   : {sem_pos_final}"
              " (preencha a coluna 'posicao' no CSV para resolver)")
    n_picks = sum(len(v) for liga in mapa_picks.values() for v in liga.values())
    print(f"  picks no livro-razao : {n_picks}"
          + ("" if n_picks else "  (preencha picks.csv para habilitar)"))
    print()
    if contagem['sem_base']:
        print("  Dica: preencha draft_pick (novatos) ou lesao/ano_retorno no CSV")
        print("        para que esses jogadores tambem recebam projecao de rating.")
    print("Proximo passo: publique dados.json junto com index.html.")


if __name__ == '__main__':
    gerar()
