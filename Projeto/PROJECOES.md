# Como alimentar as projeções

O CSV `elencos_brutos.csv` ganhou quatro colunas opcionais. Elas ficam vazias
por padrão e só precisam ser preenchidas para quem não tem estatística na
temporada corrente.

| Coluna | Para quem | Exemplo |
|---|---|---|
| `draft_pick` | Novatos que ainda não estrearam | `1` (Cooper Flagg) |
| `idade` | Quem não aparece na base da NBA | `19` |
| `lesao` | Quem perdeu a temporada | `LCA`, `AQUILES` ou `OUTRA` |
| `ano_retorno` | Acompanha `lesao` | `1` = primeira temporada de volta |

## Exemplo prático

```csv
jogador,liga,equipe_fantasy,sal_2025,...,draft_pick,idade,lesao,ano_retorno
Cooper Flagg,Liga 6,Seattle RockCity,5200000,...,1,19,,
Fred VanVleet,Liga 6,Sergipe Redentores,20700000,...,,31,LCA,1
```

Depois de preencher:

```bash
python importar_csv.py
python gerar_dados.py
```

O `gerar_dados.py` avisa no final quantos jogadores ficaram sem base de
projeção, para você saber quais linhas ainda faltam preencher.

## O que cada projeção faz

**Novatos.** O rating é projetado pela posição no draft, com decaimento
logarítmico `Z = a + b·ln(pick)`. Os coeficientes são calibrados
automaticamente com os drafts de 2018 a 2023: o script busca quem foi
escolhido em cada posição e qual foi o Z-Score da temporada de estreia,
calculado pelo mesmo método da temporada atual. Se a calibração falhar
(API fora do ar, por exemplo), caem coeficientes padrão conservadores, e o
`dados.json` registra qual origem foi usada.

**Atenção ao sinal.** O intercepto é negativo de propósito. Novatos
tipicamente produzem abaixo da média da liga, então o Z projetado é negativo
mesmo para as primeiras escolhas. Isso significa que **ligar as projeções
tende a REDUZIR o score de times jovens**, não aumentar. Esse é o resultado
correto: o valor de um novato em dynasty é futuro, e quem captura isso é o
rating dynasty, não o Power Ranking.

**Retorno de lesão.** A base é a última temporada completa do jogador, com
dois descontos separados:

- **produção por jogo**: LCA ano 1 = 0,81 (queda de ~19% na eficiência)
- **disponibilidade**: LCA ano 1 = 0,62 (48,4% dos jogos contra 78,5% antes)

Os dois fatores são separados porque medem coisas diferentes, e a queda de
disponibilidade é bem maior que a de produção. No ano 2 a produção volta
praticamente ao normal (0,97), mas a disponibilidade ainda não (0,79).
Aquiles tem prognóstico pior e fatores mais severos.

Para ajustar qualquer um desses números, edite `FATORES_LESAO` no topo do
`gerar_dados.py`.

## O interruptor no Power Ranking

O botão "🔮 Projeções" no painel de Power Ranking começa **desligado**.

- **Desligado**: o ranking usa só produção medida. É a leitura de força atual.
- **Ligado**: novatos e lesionados entram no cálculo, com aviso em tela.

Independente do interruptor, jogadores projetados **sempre** contam para
salário, idade média, composição de elenco e listagem. Eles ocupam vaga e
custam dinheiro de verdade, então excluí-los dessas contas produzia erro
puro (chegava a 38% de subestimação de folha numa franquia).
