# Passo a passo: ativar o contador de acessos

Tempo: cerca de 5 minutos. Custo: zero.

> **O que mudou:** antes as instruções pediam para "descomentar" um bloco de
> HTML, o que era confuso porque as duas opções estavam dentro do mesmo
> comentário. Agora basta preencher **uma linha** no `index.html`.

---

## Passo 1 — Criar a conta no GoatCounter

1. Acesse **https://www.goatcounter.com**
2. Clique em **Sign up**
3. Preencha:
   - **Code**: escolha um identificador, por exemplo `fantasyvilmar`
     (esse valor vira o endereço do seu painel)
   - **Email** e **senha**
   - Marque a opção de uso **não comercial** (o plano gratuito cobre isso)
4. Confirme o cadastro pelo email

Guarde o **Code** escolhido. É a única coisa que você vai precisar.

## Passo 2 — Preencher uma linha no index.html

Abra o `index.html` num editor de texto e procure por `GOATCOUNTER_CODIGO`
(Ctrl+F). Você vai encontrar isto, por volta da linha 1290:

```js
const GOATCOUNTER_CODIGO = '';
const CLOUDFLARE_TOKEN   = '';
```

Coloque o seu código entre as aspas da primeira linha:

```js
const GOATCOUNTER_CODIGO = 'fantasyvilmar';
const CLOUDFLARE_TOKEN   = '';
```

**Só isso.** Não mexa em mais nada, não descomente nada.

> Escreva **apenas o código**, sem `https://` e sem `.goatcounter.com`.
> Se o seu painel é `fantasyvilmar.goatcounter.com`, escreva `fantasyvilmar`.

## Passo 3 — Publicar

Suba o `index.html` para o Netlify, do jeito que você já faz.

Importante: suba também o `sw.js`, porque a versão do cache mudou. Sem isso o
celular pode continuar servindo a versão antiga por mais tempo.

## Passo 4 — Conferir que está funcionando

1. Abra o site publicado no navegador
2. Pressione **F12** → aba **Network**
3. Recarregue com **F5**
4. Filtre por `count`

Você deve ver uma requisição para `gc.zgo.at/count.js`. Se aparecer, está
registrando.

Depois acesse **https://SEUCODIGO.goatcounter.com** (com o código que você
escolheu) e veja o painel. A primeira visita costuma aparecer em segundos.

---

## Alternativa: Cloudflare Web Analytics

Se preferir, o processo é o mesmo trocando o campo:

1. Acesse **https://dash.cloudflare.com** → **Web Analytics** → **Add a site**
2. Informe o endereço do seu site no Netlify
3. Copie o **token** que aparece
4. No `index.html`, preencha o **segundo** campo, deixando o primeiro vazio:

```js
const GOATCOUNTER_CODIGO = '';
const CLOUDFLARE_TOKEN   = 'seu_token_aqui';
```

Preencha **apenas um** dos dois. Se os dois estiverem preenchidos, o
GoatCounter tem prioridade e o outro é ignorado.

Deixando os dois em branco, nenhum script externo é carregado e nada é medido.

---

## O que você vai ver no painel

- Visitas por dia
- Páginas mais acessadas
- De onde vieram (link direto, WhatsApp, etc.)
- País e idioma
- Tamanho de tela (dá para saber quantos usam celular)

Sem cookies, sem dados pessoais e sem necessidade de banner de consentimento.

## Duas ressalvas honestas

**O número vai ser menor que o real.** Depois de instalado como aplicativo, o
app abre offline em várias sessões. Sem rede, o evento não é enviado. Leia os
números como piso, não como contagem exata.

**Não distingue pessoas.** Sem cookies, o GoatCounter conta visitas e sessões
aproximadas, não usuários únicos identificados. Para saber quantos amigos
estão usando de fato, o número de visitas diárias somado à variedade de
tamanhos de tela dá uma boa noção, mas não é uma contagem de cabeças.

---

# E o filtro de período?

Esse não precisa de configuração. Ele já vem ligado, mas depende de dados que
só existem depois de você regerar o arquivo:

```bash
python gerar_dados.py
```

O script vai buscar os recortes (pós All-Star, últimos 90/60/30/15 dias) e
mostrar quantos jogadores cada um tem:

```
Coletando recortes de periodo...
  pos_asg   412 jogadores | media de 28.4 jogos
  d90       398 jogadores | media de 31.2 jogos
  d15        87 jogadores | media de  6.1 jogos
```

Recortes que voltarem com menos de 40 jogadores são desabilitados
automaticamente e nem aparecem no seletor. Isso é esperado fora de temporada:
"últimos 15 dias" sem jogos não tem o que medir.

Depois é só publicar o `dados.json` novo. O seletor aparece no topo do app.
