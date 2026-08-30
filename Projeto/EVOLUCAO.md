# Evolução e tendência de 3 temporadas

## O que foi feito

O `gerar_dados.py` passa a buscar as **duas temporadas anteriores** além da
atual e grava, para cada jogador, um campo `historico` com a série cronológica
e um campo `tendencia` com a leitura.

## A decisão estatística que define tudo

**Cada temporada é padronizada contra a população daquele ano.**

Isso é essencial e não é detalhe técnico. A liga inteira muda de patamar entre
temporadas: ritmo de jogo, volume de bolas de 3, regras. Comparar estatística
bruta confundiria evolução do jogador com inflação da liga. Em Z-Score,
"+1,00 em 2022" significa exatamente o mesmo que "+1,00 em 2024": um
desvio-padrão acima dos pares da época.

## Como a trajetória é lida

Com 5 temporadas, quatro medidas independentes descrevem a curva:

| Medida | O que diz |
|---|---|
| **Inclinação** | Direção e magnitude, por regressão sobre todos os pontos |
| **R²** | O quanto uma reta explica a trajetória (0 a 1) |
| **Aderência** | Fração das variações ano a ano que seguem a direção geral |
| **Forma** | O desenho da curva |

### Por que a forma existe

A inclinação sozinha não distingue quem cresceu de forma contínua de quem
subiu e recuou. Os dois podem terminar com a **mesma inclinação** e significar
coisas opostas:

| Série | Inclinação | Forma | Leitura |
|---|---|---|---|
| 0,3 → 0,9 → 1,6 → 1,0 → 0,4 | +0,03 | pico | subiu e recuou |
| 1,4 → 0,7 → 0,2 → 0,8 → 1,5 | +0,03 | vale | caiu e se recuperou |
| 0,85 → 0,90 → 0,88 → 0,86 → 0,89 | +0,00 | platô | produção previsível |

Chamar os três de "estável" seria a leitura mais enganosa possível.

As formas possíveis são **subida**, **queda**, **pico**, **vale**, **platô** e
**oscilante**. Pico e vale só prevalecem quando não há direção clara: uma
carreira que subiu muito e apenas desacelerou no último ano continua sendo uma
ascensão, ainda que o melhor ano esteja no miolo da série.

### Momento contra trajetória

Com quatro ou mais temporadas, o painel compara o ritmo das **últimas três**
com o da carreira inteira. Quando a diferença passa de 0,20 Z por ano, isso é
informado: um jogador pode ter carreira em alta e estar caindo agora, e é essa
divergência que interessa para decidir troca.

## Comparação com a curva de idade

Cada tendência é confrontada com o que o envelhecimento sozinho explicaria,
usando a mesma curva do rating dynasty. A leitura muda completamente:

- Um jogador de 33 anos caindo −0,15 Z/ano está **dentro do esperado**
- Um jogador de 26 anos caindo −0,15 Z/ano está caindo **além da idade**, o que
  sugere perda de papel no time ou condição física, não maturação natural

O painel diz qual dos dois é o caso.

## Confiabilidade da amostra

Temporadas com menos de 25 jogos aparecem no gráfico com **círculo vazado** e
marcam a tendência como "amostra curta". O dado existe, mas uma temporada de 12
jogos não sustenta conclusão sobre trajetória.

## Onde ver

- **Painel Evolução**: até 5 jogadores no mesmo gráfico, com troca de categoria
  (Z geral, cada uma das 7 categorias, minutos e jogos)
- **Tabela principal**: seta ao lado do nome (↗ ↘ →) com a leitura no tooltip

## Custo de geração

O `gerar_dados.py` agora faz duas requisições a mais à API da NBA. Se alguma
temporada antiga estiver indisponível, o script avisa e segue: quem tiver
apenas 1 ou 2 temporadas é tratado corretamente, sem quebrar.
