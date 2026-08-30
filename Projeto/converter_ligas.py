"""
Converte os .txt exportados das ligas para o CSV do projeto.

Ha DOIS formatos distintos entre as ligas.

FORMATO A  (Liga 3, Liga 5, Liga 6) — blocos separados por tabulacao
    Franquia<TAB>Jogador<TAB>
    R                          <- opcional: marca contrato de calouro
    PG                         <- uma linha por posicao
    <espaco>                   <- separador entre posicoes
    SG
    11.000.000 $<TAB>11.000.000 $<TAB>...   <- salarios, um por ano

FORMATO B  (Liga 9, Camaradas, Dinasty) — exportacao tabular
    Foto<TAB>Nome<TAB>Posicao<TAB>2026-2027<TAB>2027-2028<TAB>...
    Trae Young<TAB>Trae Young<TAB>img1<TAB>36.577.149<TAB>-<TAB>...

    A franquia aparece como linha solta logo apos uma linha de imagem.
    As posicoes vieram codificadas como img1/img1img2, ou seja, indicam
    apenas QUANTAS posicoes o jogador tem, nao quais. Isso e inofensivo:
    a posicao usada pelo app vem do PlayerIndex da NBA, nao deste arquivo.

DIFERENCA DE ANOS ENTRE LIGAS
    Nos arquivos de 20/08/2026, Liga 9, Camaradas e Dinasty comecam em
    2026-2027. Por isso o ano de cada coluna e lido do CABECALHO do arquivo,
    nunca assumido pela posicao da coluna.

VALORES ESPECIAIS
    '-'  ausencia de contrato naquele ano  -> celula vazia no CSV
    '0'  contrato de valor zero (existe!)  -> preservado como 0
"""

import csv
import io
import os
import re

PASTA = '.'
SAIDA = 'elencos_convertido.csv'

# arquivo -> nome da liga usado no sistema
MAPA_LIGAS = {
    'Liga 3.txt': 'Liga 3',
    'Liga 5.txt': 'Liga 5',
    'Liga 6.txt': 'Liga 6',
    'Liga 9.txt': 'Liga 9',
    'Camaradas league.txt': 'Liga Camaradas',
    'Dinasty League.txt': 'Liga Dinasty',
}

# Ano inicial do FORMATO A, que nao traz cabecalho de anos.
# CONFIRMADO por cruzamento com a base anterior: 100% dos 690 jogadores das
# Ligas 5 e 6 batem com a coluna de 2025, nao de 2026. As Ligas 9 e Camaradas,
# que trazem cabecalho, comecam em 2026-2027 — uma diferenca real entre ligas.
ANO_BASE_FORMATO_A = 2025

POSICOES = {'PG', 'SG', 'SF', 'PF', 'C'}


def limpar(txt):
    """Remove marcadores visuais que vieram junto do nome exportado."""
    txt = txt.replace('\u00ae', '').replace('\u00d0', '')
    txt = re.sub(r'\s+', ' ', txt)
    return txt.strip()


def valor(txt):
    """
    Converte texto de salario em inteiro.
    Devolve None quando nao ha contrato ('-' ou vazio).
    Preserva o zero, que e um valor real e diferente de ausencia.
    """
    t = (txt or '').replace('$', '').replace('\u00a0', ' ').strip()
    if t in ('', '-', '--'):
        return None
    t = t.replace('.', '').replace(' ', '')
    if not t.lstrip('-').isdigit():
        return None
    return int(t)


def parse_formato_a(caminho, liga):
    """Blocos: franquia+jogador, posicoes, linha de salarios."""
    linhas = io.open(caminho, encoding='utf-8', errors='replace').read().replace('\r', '').split('\n')

    # Descobre as franquias: primeiro campo das linhas que tem TAB e nome de jogador
    # Cabecalhos de jogador tem tabulacao E NAO tem cifrao. As linhas de
    # salario tambem sao tabuladas, e sem esse filtro seriam confundidas com
    # nomes de franquia (o que inflava a contagem para mais de 100).
    franquias = set()
    for l in linhas:
        if '\t' in l and '$' not in l:
            p = l.split('\t')
            if len(p) >= 2 and p[0].strip() and p[1].strip():
                franquias.add(p[0].strip())

    registros = []
    atual = None
    for l in linhas:
        bruto = l.rstrip()
        if '\t' in bruto:
            p = bruto.split('\t')
            cab = p[0].strip()
            # Cabecalho de um novo jogador (nunca contem cifrao)
            if '$' not in bruto and cab in franquias and len(p) >= 2 and p[1].strip():
                if atual:
                    registros.append(atual)
                atual = {'franquia': cab, 'jogador': limpar(p[1]), 'salarios': []}
                continue
            # Linha de salarios
            if atual is not None and '$' in bruto:
                for celula in p:
                    v = valor(celula)
                    if v is not None:
                        atual['salarios'].append(v)
                continue
        if atual is None:
            continue
        s = bruto.strip()
        if s in POSICOES or s == 'R' or s == '':
            continue
        if '$' in s:
            v = valor(s)
            if v is not None:
                atual['salarios'].append(v)

    if atual:
        registros.append(atual)

    anos = [ANO_BASE_FORMATO_A + i for i in range(5)]
    saida = []
    for r in registros:
        if not r['jogador']:
            continue
        d = {'jogador': r['jogador'], 'liga': liga, 'equipe_fantasy': r['franquia']}
        for i, ano in enumerate(anos):
            d[ano] = r['salarios'][i] if i < len(r['salarios']) else None
        saida.append(d)
    return saida, anos


def parse_formato_b(caminho, liga):
    """
    Tabular, com cabecalho declarando os anos.

    A ancora e o cabecalho `Foto<TAB>Nome<TAB>...`, nao a imagem do escudo.
    Motivo: em varias franquias a linha do escudo vem como espacos em branco,
    sem nome de arquivo. Detectar bloco pela imagem fazia franquias inteiras
    passarem despercebidas, e seus jogadores eram somados a franquia anterior
    (apareciam elencos de 31 e 35 jogadores, com folha acima do teto).

    Estrutura de cada bloco:
        <escudo: arquivo de imagem OU espacos>
        Nome da Franquia
        <linha em branco>
        <avatar do GM: arquivo de imagem OU espacos>
        Nome do GM
        <linha em branco>
        Foto<TAB>Nome<TAB>Posicao<TAB>2025-2026<TAB>...
        <linhas de jogadores>

    Logo, no trecho imediatamente anterior a cada cabecalho existem exatamente
    dois nomes: o primeiro e a franquia, o segundo e o GM.
    """
    linhas = io.open(caminho, encoding='utf-8', errors='replace').read().replace('\r', '').split('\n')

    TITULO = 'Lista de Jogadores por Franquias'

    def ehNome(l):
        t = l.strip()
        if not t or t == TITULO:
            return False
        if '\t' in l:
            return False
        if re.search(r'\.(png|jpg|jpeg|gif|webp)$', t, re.I):
            return False
        return True

    # indices dos cabecalhos
    cabecalhos = [i for i, l in enumerate(linhas)
                  if l.split('\t')[0].strip() == 'Foto' and len(l.split('\t')) > 3]

    anos = []
    saida = []

    for pos, idx in enumerate(cabecalhos):
        # anos declarados neste cabecalho
        partes = linhas[idx].split('\t')
        anos_bloco = []
        for c in partes[3:]:
            m = re.match(r'(\d{4})-\d{2,4}', c.strip())
            if m:
                anos_bloco.append(int(m.group(1)))
        if anos_bloco:
            anos = anos_bloco

        # franquia: primeiro nome no trecho anterior a este cabecalho
        inicio = 0 if pos == 0 else cabecalhos[pos - 1]
        nomes = [linhas[i].strip() for i in range(inicio, idx) if ehNome(linhas[i])]
        # o ultimo nome e o GM; a franquia e o penultimo (ou o unico disponivel)
        if len(nomes) >= 2:
            franquia = nomes[-2]
        elif nomes:
            franquia = nomes[-1]
        else:
            franquia = f'Franquia sem nome {pos + 1}'

        # jogadores ate o proximo cabecalho
        fim_bloco = cabecalhos[pos + 1] if pos + 1 < len(cabecalhos) else len(linhas)
        for i in range(idx + 1, fim_bloco):
            p = linhas[i].split('\t')
            if len(p) >= 4 and re.fullmatch(r'(img\d)+', p[2].strip()):
                jogador = limpar(p[1])
                if not jogador:
                    continue
                d = {'jogador': jogador, 'liga': liga, 'equipe_fantasy': franquia}
                for k, ano in enumerate(anos):
                    col = 3 + k
                    d[ano] = valor(p[col]) if col < len(p) else None
                saida.append(d)

    return saida, anos


def main():
    todos = []
    anos_por_liga = {}

    for arquivo, liga in MAPA_LIGAS.items():
        caminho = os.path.join(PASTA, arquivo)
        if not os.path.exists(caminho):
            print(f"AVISO: {arquivo} nao encontrado")
            continue

        texto = io.open(caminho, encoding='utf-8', errors='replace').read()
        formato = 'B' if 'Lista de Jogadores por Franquias' in texto[:200] else 'A'

        if formato == 'A':
            regs, anos = parse_formato_a(caminho, liga)
        else:
            regs, anos = parse_formato_b(caminho, liga)

        anos_por_liga[liga] = anos
        todos.extend(regs)

        franq = len({r['equipe_fantasy'] for r in regs})
        com_sal = sum(1 for r in regs if any(r.get(a) is not None for a in anos))
        print(f"{liga:16} formato {formato} | {franq:2} franquias | "
              f"{len(regs):3} jogadores | {com_sal:3} com salario | anos {anos[0]}-{anos[-1]}")

    # Uniao de todos os anos encontrados
    anos_todos = sorted({a for anos in anos_por_liga.values() for a in anos})
    campos = (['jogador', 'liga', 'equipe_fantasy']
              + [f'sal_{a}' for a in anos_todos]
              + ['draft_pick', 'idade', 'lesao', 'ano_retorno'])

    with io.open(SAIDA, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for r in todos:
            linha = {'jogador': r['jogador'], 'liga': r['liga'],
                     'equipe_fantasy': r['equipe_fantasy']}
            for a in anos_todos:
                v = r.get(a)
                linha[f'sal_{a}'] = '' if v is None else v
            for c in ('draft_pick', 'idade', 'lesao', 'ano_retorno'):
                linha[c] = ''
            w.writerow(linha)

    print()
    print(f"Gerado: {SAIDA}")
    print(f"  {len(todos)} linhas | colunas de salario: {anos_todos[0]} a {anos_todos[-1]}")
    print()
    print("Anos por liga (lidos do cabecalho quando disponivel):")
    for liga, anos in anos_por_liga.items():
        print(f"  {liga:16} {anos}")


if __name__ == '__main__':
    main()
