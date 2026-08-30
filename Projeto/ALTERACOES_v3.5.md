# NBA Fantasy GM — alterações da versão 3.5

## Arquivos para substituir

- `index.html`
- `gerar_dados.py`
- `app.py`

Depois de copiar os arquivos para a pasta do projeto, execute:

```powershell
python gerar_dados.py
```

Isso recria `dados.json` com a temporada e o histórico usados pelas novas previsões. Em seguida, abra o site normalmente ou execute `python app.py`.

## 1. Radar antes/depois no relatório de troca

- O relatório pós-simulação agora mostra um cartão para cada franquia envolvida.
- Cada radar sobrepõe o estado anterior à troca (cinza) e o estado posterior (cor da franquia no relatório).
- Os sete eixos são os mesmos do restante do site: PTS, REB, AST, STL, BLK, 3PM e controle de turnovers.
- O bloco aparece antes de **Análise Inteligente da Troca (Avaliação de Contexto)**.
- A simulação do radar e a projeção do Power Ranking utilizam o mesmo elenco pós-troca, evitando resultados divergentes entre as seções.

## 2. Previsão da evolução

### Jogador

- A curva usa até cinco temporadas reais e acrescenta a próxima temporada como ponto previsto.
- O trecho até a previsão é tracejado, e o ponto previsto é um losango.
- O cálculo combina:
  - 55% da tendência individual dos últimos cinco anos;
  - 35% da mediana observada em jogadores de posição compatível e idade entre um ano abaixo e um ano acima, usando transições das últimas cinco temporadas;
  - 10% da curva etária já calculada pelo projeto, quando a categoria é o rating geral.
- A parcela dos pares só entra quando existem ao menos oito transições comparáveis com 15 ou mais jogos em ambas as temporadas.
- Variações extremas são limitadas por categoria para reduzir previsões pouco realistas causadas por amostras curtas.

### Franquia

- Foi incluída, ao lado do radar dos seis titulares, uma curva de evolução da franquia com até cinco temporadas e a previsão da próxima.
- Em cada temporada, o elenco é ordenado pelo rating daquela temporada e recebe os pesos internos solicitados:
  - peso 3 para os seis melhores;
  - peso 2 para os três seguintes;
  - peso 1 para o fundo do banco.
- Esses pesos são usados somente no cálculo; a média ponderada não é exposta como informação gerencial no site.

### Limitação dos dados atuais

O projeto não mantém snapshots históricos de quais jogadores pertenciam a cada franquia em cada temporada. Por isso, a curva da franquia mostra a trajetória histórica do **elenco atual**, aplicando a produção de cada atleta nas temporadas anteriores. Para reconstruir a história real da franquia, seria necessário passar a armazenar os elencos ao final de cada temporada.

## 3. Buscador de contrapartidas

- Corrigida a referência a uma variável inexistente no caminho **Eu ofereço / pacote de saída**, que interrompia a avaliação dos picks de retorno.
- Jogadores sem rating válido deixam de entrar nos pacotes.
- A tolerância de diferença Dynasty agora é proporcional ao tamanho do pacote, com limites de segurança, permitindo propostas reais de 2x1 sem liberar combinações absurdas.
- A aceitação considera a tolerância de negociação de cada estágio de franquia, em vez de um corte único excessivamente restritivo.
- Quando não houver retorno, a mensagem explica os filtros que podem ter eliminado as opções.

## Verificações realizadas

- Sintaxe JavaScript do `index.html`.
- Sintaxe Python de `gerar_dados.py` e `app.py`.
- Construção da série de jogador e da série de franquia com dados reais do projeto.
- Ordem do radar antes da análise contextual e uso do mesmo banco simulado para radar e Power Ranking.
- Correção da variável do buscador e presença dos novos critérios de tolerância.

