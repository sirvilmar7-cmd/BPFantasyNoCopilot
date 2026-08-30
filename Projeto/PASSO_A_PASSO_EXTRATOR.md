# Passo a passo: extrair elencos pelo console

Tempo estimado: 2 minutos na primeira liga, menos de 1 minuto nas seguintes.

**Requisito:** navegador de computador (Chrome, Edge ou Firefox). Não funciona
no celular, porque celular não tem console de desenvolvedor.

---

## Passo 1 — Abra a página de elencos, já logado

Entre no site da liga e navegue até a tela que mostra os elencos com os
salários, a mesma de onde você exporta o texto hoje.

Confira que os jogadores estão **visíveis na tela**. O extrator lê o que está
na página: se houver paginação ou uma aba por franquia, ele só pega o que
estiver aberto no momento (o Passo 5 resolve isso).

## Passo 2 — Abra o console

Pressione **F12** e clique na aba **Console**.

> **Chrome e Edge bloqueiam colar no console na primeira vez.** Vai aparecer um
> aviso pedindo para você digitar `allow pasting` (ou `permitir colagem`) e dar
> Enter. Faça isso uma vez e o bloqueio some.

## Passo 3 — Cole o extrator

Abra `extrator_console.js`, selecione tudo (Ctrl+A), copie (Ctrl+C), cole no
console (Ctrl+V) e pressione **Enter**.

Deve aparecer:

```
Extrator carregado.
  extrair("Liga 5")   -> extrai a pagina atual e acumula
  baixarTudo()        -> baixa o CSV com tudo que foi acumulado
  limparAcervo()      -> recomeca do zero
  diagnosticar()      -> mostra o que ha na pagina, se algo falhar
```

## Passo 4 — Limpe o acervo e extraia

Na **primeira** liga da sessão, comece zerando:

```js
limparAcervo()
```

Depois extraia, usando exatamente o nome da liga como aparece no app:

```js
extrair("Liga 5")
```

O nome precisa bater com um destes, senão o app não reconhece a liga:
`Liga 3`, `Liga 5`, `Liga 6`, `Liga 9`, `Liga Dinasty`, `Liga Camaradas`.

Você verá um resumo:

```
===== EXTRACAO CONCLUIDA =====
  liga        : Liga 5
  franquias   : 24
  jogadores   : 349
  com posicao : 349
  com salario : 349
  anos        : 2025, 2026, 2027, 2028, 2029
```

**Confira esses números.** Se as franquias vierem em número menor do que o
esperado, ou "com posição" estiver muito abaixo do total, vá para a seção
"Se algo der errado".

## Passo 5 — Repita para as outras ligas

Navegue para a próxima liga e repita **os Passos 3 e 4** (o extrator precisa ser
colado de novo a cada página, mas **não** rode `limparAcervo()` outra vez).

O acervo é guardado no navegador e sobrevive à navegação. Rodar duas vezes na
mesma página não duplica nada: jogadores repetidos são ignorados.

> **Se as ligas estiverem em sites diferentes** (por exemplo `bpfantasy.app` e
> `bskt.mudfaz.com.br`), o acervo **não** atravessa de um para o outro. Nesse
> caso, faça `baixarTudo("site1.csv")` antes de trocar de site, depois repita no
> outro site com `baixarTudo("site2.csv")` e junte os dois arquivos no fim.

## Passo 6 — Baixe o CSV

Com todas as ligas extraídas:

```js
baixarTudo()
```

Baixa `elencos_brutos.csv` com tudo junto, e mostra a conferência final:

```
===== ARQUIVO BAIXADO =====
  2101 jogadores | anos 2025 a 2030
  Liga 3: 298
  Liga 5: 349
  ...
```

## Passo 7 — Atualize o projeto

Mova o arquivo baixado para a pasta do projeto, substituindo o
`elencos_brutos.csv` atual, e rode:

```bash
python importar_csv.py
python gerar_dados.py
```

Depois publique `dados.json` e `index.html` como de costume.

---

## Se algo der errado

**Nenhuma tabela encontrada / zero jogadores**

O site provavelmente monta a lista com `<div>` em vez de `<table>`. Rode:

```js
diagnosticar()
```

e me mande a saída. Se aparecer "Tabelas encontradas: 0", me mande também o
HTML da lista:

```js
copy(document.body.outerHTML)
```

e cole num arquivo de texto.

**Franquias vindo erradas ou vazias**

O extrator procura o nome da franquia subindo no HTML acima de cada tabela.
Se o site posicionar o nome em outro lugar, force manualmente:

```js
extrair("Liga 5", { franquia: "Killer Duck" })
```

Aí você roda uma vez por franquia, com o nome correto em cada.

**"com posicao" muito abaixo do total**

As posições estão codificadas de um jeito que o extrator não reconheceu. Rode
`diagnosticar()` e me mande a linha que mostra `img src`, `alt` e `title`.
Não é crítico: o `gerar_dados.py` pega posição da API da NBA de qualquer forma,
e a coluna `posicao` do CSV é apenas um reforço.

**Números de salário estranhos**

O extrator trata `-` e vazio como ausência de contrato, e preserva `0` como
valor real. Se a plataforma usar outro símbolo para "sem contrato", me avise
qual é.
