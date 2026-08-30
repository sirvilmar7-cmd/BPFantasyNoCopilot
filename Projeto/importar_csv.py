import csv
import json
import os

ARQUIVO_CSV = 'elencos_brutos.csv'
ARQUIVO_PICKS = 'picks.csv'
ARQUIVO_JSON = 'elencos.json'

# Anos de contrato suportados. Para incluir novos anos, basta adicionar aqui
# e criar a coluna correspondente (sal_ANO) no CSV.
ANOS_CONTRATO = [2025, 2026, 2027, 2028, 2029, 2030]

# Teto salarial por liga. Mantido aqui apenas como referencia/documentacao:
# quem aplica o teto e o frontend (TETOS_LIGA em index.html). Se alterar um
# valor, altere nos dois lugares.
TETOS_LIGA = {
    'Liga 3': 100_000_000,
    'Liga 5': 100_000_000,
    'Liga 6': 100_000_000,
    'Liga 9': 100_000_000,
    'Liga Dinasty': 160_000_000,
    'Liga Camaradas': 115_000_000,
}


def limpar_valor_salario(valor_bruto):
    """
    Converte o texto do CSV em numero inteiro.
    Retorna None quando o campo esta vazio, para que a ausencia de dado seja
    preservada como 'sem informacao' e nao confundida com salario igual a zero.
    """
    if valor_bruto is None:
        return None
    texto = str(valor_bruto).strip()
    if texto == '':
        return None
    texto = texto.replace('$', '').replace(' ', '')
    if ',' in texto and '.' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    elif texto.count('.') > 1:
        texto = texto.replace('.', '')
    try:
        return int(round(float(texto)))
    except ValueError:
        return None


def carregar_picks():
    """
    Le picks.csv e devolve { liga: { franquia: [ {ano, rodada, origem}, ... ] } }.

    FORMATO
        liga,franquia,ano,rodada,origem
        Liga 3,Los Brasas Candangos,2027,1,Los Brasas Candangos
        Liga 3,Los Brasas Candangos,2028,1,Recife Sharks

    'franquia' e quem POSSUI o pick hoje.
    'origem'   e de quem era originalmente. Isso importa porque o valor de um
               pick depende de quao ruim tende a ser o time de origem: a
               primeira rodada do lanterna vale muito mais que a do campeao.
               Quando a origem e a propria franquia, repita o nome.

    O arquivo e opcional. Sem ele, o sistema continua funcionando, apenas sem
    saber quais picks cada franquia realmente possui.
    """
    if not os.path.exists(ARQUIVO_PICKS):
        return {}

    picks = {}
    total = 0
    with open(ARQUIVO_PICKS, mode='r', encoding='utf-8') as arquivo:
        for linha in csv.DictReader(arquivo):
            liga = (linha.get('liga') or '').strip()
            franquia = (linha.get('franquia') or '').strip()
            origem = (linha.get('origem') or '').strip() or franquia
            try:
                ano = int(str(linha.get('ano') or '').strip())
                rodada = int(str(linha.get('rodada') or '').strip())
            except ValueError:
                continue
            if not liga or not franquia or rodada not in (1, 2):
                continue
            picks.setdefault(liga, {}).setdefault(franquia, []).append(
                {'ano': ano, 'rodada': rodada, 'origem': origem})
            total += 1

    for liga in picks:
        for fr in picks[liga]:
            picks[liga][fr].sort(key=lambda p: (p['ano'], p['rodada'], p['origem']))

    print(f"  Picks carregados: {total}")
    return picks


def importar():
    if not os.path.exists(ARQUIVO_CSV):
        print(f"ERRO: {ARQUIVO_CSV} nao encontrado.")
        return

    estrutura = {}
    total_linhas = 0
    total_com_salario = 0

    with open(ARQUIVO_CSV, mode='r', encoding='utf-8') as arquivo:
        leitor = csv.DictReader(arquivo)
        colunas = leitor.fieldnames or []

        for linha in leitor:
            jogador = (linha.get('jogador') or '').strip()
            liga = (linha.get('liga') or '').strip()
            equipe = (linha.get('equipe_fantasy') or '').strip()

            if not jogador or not liga or not equipe:
                continue

            total_linhas += 1

            # Monta o dicionario de salarios apenas com os anos que possuem valor.
            # Anos sem informacao nao entram no dicionario, e o frontend exibe
            # campo em branco nesses casos.
            salarios = {}
            for ano in ANOS_CONTRATO:
                coluna = f'sal_{ano}'
                if coluna in colunas:
                    valor = limpar_valor_salario(linha.get(coluna))
                    if valor is not None:
                        salarios[str(ano)] = valor

            if salarios:
                total_com_salario += 1

            estrutura.setdefault(liga, {})
            estrutura[liga].setdefault(equipe, {'jogadores': {}})

            # Campos opcionais de projecao. Ficam no CSV porque sao informacao
            # que voce controla e a API da NBA nao fornece de forma confiavel:
            #   draft_pick  -> posicao no draft, base da projecao de novatos
            #   idade       -> idade de quem ainda nao tem ficha na NBA
            #   lesao       -> tipo (LCA, AQUILES, OUTRA) para o desconto de retorno
            #   ano_retorno -> 1 = primeira temporada de volta, 2 = segunda
            registro = {
                'salarios': salarios,
                'anos_contrato': len(salarios)
            }
            for campo, conv in (('draft_pick', int), ('idade', int),
                                ('lesao', str), ('ano_retorno', int),
                                ('posicao', str)):
                if campo in colunas:
                    bruto = (linha.get(campo) or '').strip()
                    if bruto:
                        try:
                            registro[campo] = conv(bruto) if conv is not int else int(float(bruto))
                        except ValueError:
                            pass

            estrutura[liga][equipe]['jogadores'][jogador] = registro

    # Anexa os picks a cada franquia
    mapa_picks = carregar_picks()
    for liga, franquias in mapa_picks.items():
        if liga not in estrutura:
            print(f"  AVISO: picks para liga desconhecida '{liga}', ignorados")
            continue
        for franquia, lista in franquias.items():
            if franquia not in estrutura[liga]:
                print(f"  AVISO: picks para franquia desconhecida '{franquia}' em {liga}")
                continue
            estrutura[liga][franquia]['picks'] = lista

    with open(ARQUIVO_JSON, mode='w', encoding='utf-8') as saida:
        json.dump(estrutura, saida, ensure_ascii=False, indent=2)

    print(f"Importacao concluida: {ARQUIVO_JSON}")
    projecao = sum(1 for liga in estrutura.values() for f in liga.values()
                   for j in f['jogadores'].values()
                   if j.get('draft_pick') or j.get('lesao'))
    print(f"  Linhas processadas: {total_linhas}")
    print(f"  Com dados de projecao (draft/lesao): {projecao}")
    print(f"  Com dados de salario: {total_com_salario}")
    print(f"  Sem dados de salario: {total_linhas - total_com_salario}")
    print()
    for liga, franquias in estrutura.items():
        jogadores = sum(len(f['jogadores']) for f in franquias.values())
        com_sal = sum(
            1 for f in franquias.values()
            for j in f['jogadores'].values() if j['salarios']
        )
        teto = TETOS_LIGA.get(liga)
        teto_txt = f" | teto {teto/1_000_000:.0f}M" if teto else " | sem teto configurado"
        alerta = "" if com_sal else "  <- sem contratos: analise de teto desabilitada"
        print(f"  {liga}: {len(franquias)} franquias | {jogadores} jogadores | {com_sal} com salario{teto_txt}{alerta}")


if __name__ == '__main__':
    importar()
