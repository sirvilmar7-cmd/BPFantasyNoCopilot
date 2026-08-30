# Alterações v3.4

## Arquivos para substituir

- `index.html`
- `gerar_dados.py`
- `app.py`

Depois da substituição, execute `python gerar_dados.py` para recriar o
`dados.json`. O arquivo de dados antigo não contém as novas posições históricas
e ainda foi gerado com temporadas inconsistentes.

## 1. Posição de jogadores afastados

O gerador agora consulta o `PlayerIndex` das três temporadas anteriores e usa a
posição da temporada mais recente em que o jogador efetivamente atuou. A busca
é feita do ano mais recente para o mais antigo.

Ordem prática das fontes para um jogador afastado:

1. posição da última temporada jogada;
2. índice atual/CommonPlayerInfo;
3. posição informada no CSV;
4. `N/D` somente se todas falharem.

O campo interno `origem_posicao` registra a temporada usada, facilitando uma
auditoria do `dados.json` sem exibir essa informação no site.

Também foi corrigida a importação de `posicao` existente no `elencos.json`: o
campo era gerado por `importar_csv.py`, mas não era copiado para o mapa de
metadados pelo gerador.

## 2. Gráficos de radar

Foram criados radares SVG sem biblioteca externa em dois pontos:

- diagnóstico da franquia: perfil dos seis titulares;
- simulador H2H: dois perfis sobrepostos, respeitando os jogadores selecionados.

Os sete eixos são PTS, REB, AST, STL, BLK, 3PM e TOV. Como essas estatísticas
possuem escalas incompatíveis, cada eixo é normalizado contra as escalações da
própria liga. O centro representa desempenho inferior e a borda, superior. O
eixo de turnovers é invertido, de modo que menos turnovers sempre aparece como
melhor desempenho.

O radar acompanha recortes, categorias carregadas e a opção de incluir
projeções porque seu cache é invalidado junto com o Power Ranking.

## 3. Classificação etária por terços

A idade usada pelo motor de aconselhamento agora é calculada sobre o elenco
inteiro:

- peso 3 para os seis jogadores mais fortes;
- peso 2 para os três reservas mais fortes;
- peso 1 para todo o restante do banco.

Jogadores sem idade não entram na soma nem no divisor, mas continuam ocupando
sua posição na ordem do elenco. O valor ponderado não é exibido na interface.

Dentro de cada liga, as franquias são ordenadas pela média ponderada e divididas
em três grupos de tamanho equivalente: jovem, equilibrada e envelhecida. Em
caso de quantidade não divisível por três, os primeiros grupos recebem uma
franquia adicional.

Foram adicionados três estágios intermediários:

- `Contender Equilibrada`;
- `Meio de Tabela Equilibrado`;
- `Em Reconstrução de Transição`.

Cada estágio recebeu recomendação própria, pesos entre produção atual e valor
dynasty, perfil de moedas/alvos de troca, tolerância de negociação e valor
contextual de picks. O avaliador manual também gera alertas específicos para
uma franquia de meio de tabela equilibrada.

## 4. Temporada unificada

Todas as consultas de estatísticas, posições, recortes e variância agora usam
explicitamente `2025-26`, última temporada concluída em agosto de 2026. Antes,
as estatísticas principais usavam o default `2025-26` da biblioteca, enquanto
os logs e metadados declaravam `2024-25`.

## Validações executadas

- sintaxe JavaScript do `index.html`;
- sintaxe/AST de `gerar_dados.py` e `app.py`;
- divisão artificial de seis franquias em três terços iguais;
- pesos 3/2/1 incluindo o fundo do banco;
- normalização do radar e inversão de TOV;
- geração SVG com duas séries sobrepostas;
- recuperação simulada da posição de um jogador na última temporada.

Não foi executada uma geração real do `dados.json`, pois ela depende de acesso
ao `stats.nba.com` a partir da sua conexão residencial.
