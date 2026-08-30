# Livro-razão de picks

## O problema que isso resolve

Antes, as sugestões de troca ofereciam picks genéricos ("Pick 1ª (início)")
sem saber se a franquia realmente os possuía. Se você já tinha negociado sua
primeira de 2027, a proposta era inválida e você só descobria ao tentar propor.

Além disso, todo pick de primeira rodada valia o mesmo, independentemente de
qual time o originou. Na prática, a primeira do lanterna é uma escolha de topo
e a do campeão é escolha de fim de rodada: são ativos muito diferentes com o
mesmo nome.

## Como preencher

O arquivo `picks.csv` tem cinco colunas:

```csv
liga,franquia,ano,rodada,origem
Liga 3,Los Brasas Candangos,2027,1,Los Brasas Candangos
Liga 3,Los Brasas Candangos,2027,2,Los Brasas Candangos
Liga 3,Los Brasas Candangos,2028,1,Recife Sharks
```

| Coluna | O que é |
|---|---|
| `liga` | Nome exato da liga, como no sistema |
| `franquia` | Quem **possui** o pick hoje |
| `ano` | Ano do draft |
| `rodada` | `1` ou `2` |
| `origem` | De quem era originalmente. Se for da própria franquia, repita o nome |

A coluna `origem` é a mais importante. É ela que permite estimar a posição
provável da escolha.

Depois de preencher:

```bash
python importar_csv.py
python gerar_dados.py
```

O importador avisa se houver picks de liga ou franquia desconhecida, o que
ajuda a pegar erro de digitação nos nomes.

## Como o valor é calculado

O valor de um pick passa por três camadas:

**1. Posição provável**, estimada pelo desempenho atual do time de origem no
Power Ranking. O pior colocado escolhe primeiro, então a posição é o inverso da
colocação. Numa liga de 24, o pick do último vira aproximadamente a escolha 1,
e o do primeiro colocado vira a 24.

**2. Valor base**, ancorado na produção real de jogadores em posições
equivalentes do ranking de Z-Score.

**3. Multiplicador por estágio de quem recebe.** O mesmo pick vale mais para
quem não precisa vencer agora:

| Estágio de quem recebe | 1ª rodada | 2ª rodada |
|---|---|---|
| Em Reconstrução (estágio inicial) | 1,45× | 1,25× |
| Em Reconstrução (em andamento) | 1,30× | 1,15× |
| Meio de Tabela (fim de ciclo) | 1,15× | 1,05× |
| Meio de Tabela (projeção de alta) | 1,00× | 0,95× |
| Contender de Longo Prazo | 0,85× | 0,75× |
| Contender com Urgência | 0,70× | 0,60× |

O efeito combinado é grande. Num teste com 24 franquias, a primeira rodada do
pior time valeu **2,749** contra **1,510** do melhor time, para o mesmo
comprador: uma diferença de 82%.

## O que muda no app

- As sugestões só oferecem picks que a franquia **realmente possui**
- Os rótulos mostram ano, origem e faixa: `Pick 1ª 2027 (Recife Sharks) · topo`
- O diagnóstico da franquia exibe o capital de draft, com a posição estimada de
  cada primeira rodada
- No Trade Finder por pacote, a contraparte agora pode **devolver** picks. Antes
  o retorno só podia ser jogador, o que descartava justamente as trocas mais
  típicas de reconstrução

## Sem o arquivo

`picks.csv` é opcional. Sem ele, o sistema volta ao catálogo genérico de quatro
degraus e continua funcionando normalmente. Isso permite habilitar o
livro-razão liga por liga, conforme você for levantando o dado.
