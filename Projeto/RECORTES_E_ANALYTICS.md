# Recortes de período e estatísticas de uso

## 1. Filtro de período

Um seletor no cabeçalho aplica o recorte a **todas** as análises ao mesmo
tempo: tabela principal, Power Ranking, H2H, buscador de trocas, avaliador de
trocas, comparador e diagnóstico interno das franquias.

Recortes disponíveis: temporada inteira (padrão), pós All-Star Game,
últimos 90, 60, 30 e 15 dias.

### A decisão que sustenta a análise

Cada recorte tem **seu próprio Z-Score**, calculado contra os jogadores que
atuaram naquele período. Um Z de +1,00 nos últimos 15 dias significa "um
desvio-padrão acima de quem jogou nesses 15 dias", não acima da média da
temporada inteira. Sem isso, comparar períodos seria comparar coisas
diferentes: em janelas curtas o elenco ativo muda (lesionados somem, reservas
ganham minutos) e a média de referência se desloca.

### O aviso de ruído não é decoração

Em 15 dias um jogador faz de 5 a 8 partidas. Com amostra assim, uma partida
atípica desloca a média inteira e o Z-Score vira ruído. O app calcula a média
de jogos do recorte e:

- abaixo de 10 jogos: alerta explícito de que serve para detectar mudança de
  papel ou volta de lesão, **não** para avaliar valor de jogador
- entre 10 e 20 jogos: aviso de amostra curta

Recortes com menos de 40 jogadores qualificados são desabilitados
automaticamente. Fora de temporada, "últimos 15 dias" volta vazio, e é melhor
esconder o recorte do que exibir um Z calculado sobre 3 jogadores.

### Quem não jogou no período

Sai das análises de força (ranking, escalação, confrontos), mas continua no
elenco para salário, idade e composição. O aviso mostra quantos estão nessa
situação.

### O que NÃO muda com o recorte

Salário, contrato, idade e o histórico de 3 temporadas. São atributos do
jogador ou de temporadas inteiras, não do período analisado.

---

## 2. Estatísticas de uso

O bloco está no `<head>` do `index.html`, comentado. Escolha uma opção,
descomente e preencha.

### Opção A — GoatCounter (recomendada aqui)

Gratuito para uso não comercial, script de cerca de 3,5 KB, sem cookies e sem
necessidade de banner de consentimento.

1. Crie a conta em `https://www.goatcounter.com`
2. Escolha um código (vira `SEUCODIGO.goatcounter.com`)
3. Substitua `SEUCODIGO` no `index.html` e descomente a linha

### Opção B — Cloudflare Web Analytics

Também gratuito e sem cookies, sem limite de visitas. Funciona mesmo sem usar
a Cloudflare como hospedagem. Pegue o token no painel deles.

### Duas observações honestas

**O service worker não atrapalha.** Ele guarda em cache apenas arquivos do
próprio domínio. Os scripts de analytics vêm de domínios externos e passam
direto pela rede. Não é preciso mexer no `sw.js`.

**O número medido será menor que o real.** Depois de instalado como
aplicativo, o app abre offline em muitas sessões. Sem rede, o evento não é
enviado. Trate os números como piso, não como contagem exata.
