# Publicar o Gerenciador Fantasy na internet e no celular

Guia completo, gratuito e sem cartão de crédito.

---

## Antes de tudo: por que a arquitetura mudou

Seu projeto hoje tem um backend Flask que busca dados no `stats.nba.com` quando
alguém acessa o site. **Isso não funciona de forma confiável em nenhum servidor
gratuito**, e o motivo não é limitação de plano:

- O `stats.nba.com` fica atrás da proteção Akamai, que rejeita requisições por
  **fingerprint TLS** (ou seja, identifica que não é um navegador de verdade).
- Além disso, ele **descarta silenciosamente conexões vindas de IPs de
  datacenter**. AWS, Google Cloud, Azure, Render e Heroku estão todos bloqueados.
- O sintoma é característico: funciona perfeitamente na sua máquina e trava com
  timeout no servidor. Não é bug do seu código.

A solução é inverter o fluxo. Em vez do servidor buscar os dados, **você gera os
dados na sua máquina** (cujo IP residencial funciona) e publica o resultado como
arquivo estático.

| | Antes | Agora |
|---|---|---|
| Backend | Flask no Render | Nenhum |
| Busca NBA | No servidor (bloqueada) | Na sua máquina (funciona) |
| Cold start | 30 a 60 segundos | Zero |
| Custo | Grátis com limites | Grátis de verdade |
| Offline | Não | Sim |

O `app.py` continua no projeto para você desenvolver localmente. Ele só deixa de
ser necessário em produção.

---

## PARTE 1 — Gerar os dados (5 minutos)

Na pasta do projeto, no seu computador:

```bash
pip install -r requirements.txt
python importar_csv.py     # gera elencos.json a partir do CSV
python gerar_dados.py      # gera dados.json consultando a NBA
```

O `gerar_dados.py` testa a conexão antes de começar. Se seu IP estiver
bloqueado, ele avisa e explica o motivo em vez de travar.

> **Se falhar:** desligue qualquer VPN. VPNs saem por IPs de datacenter,
> exatamente os que a NBA bloqueia.

Ao final você terá o **`dados.json`**, que é o coração do site publicado.

Repita esses dois comandos sempre que quiser atualizar (uma vez por dia basta).

---

## PARTE 2 — Publicar o site (10 minutos)

### Opção A — Netlify por arrastar e soltar (mais rápido, sem Git)

1. Junte estes arquivos numa pasta:
   - `index.html`
   - `dados.json`
   - `manifest.json`
   - `sw.js`
   - `icone-192.png` e `icone-512.png`
   - `netlify.toml`
2. Acesse **app.netlify.com/drop**
3. Arraste a pasta para a página.
4. Pronto: você recebe um endereço público em segundos.

Para atualizar depois, arraste a pasta de novo no painel do site.

### Opção B — GitHub + Netlify (recomendada, atualiza sozinho)

1. Crie um repositório em **github.com/new** (pode ser público ou privado).
2. Na pasta do projeto:

```bash
git init
git add .
git commit -m "Gerenciador Fantasy"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
git push -u origin main
```

3. Em **app.netlify.com** → *Add new site* → *Import an existing project* →
   escolha o GitHub e o repositório.
4. Build command: **deixe vazio**. Publish directory: **`.`**
5. Clique em *Deploy*.

Daí em diante, atualizar é:

```bash
python gerar_dados.py
git add dados.json && git commit -m "atualiza dados" && git push
```

O Netlify republica sozinho em segundos.

> **Alternativa:** GitHub Pages funciona igual e também é grátis. Em
> *Settings → Pages*, escolha a branch `main` e a pasta raiz. A vantagem do
> Netlify é o `netlify.toml`, que já configura o cache corretamente.

---

## PARTE 3 — Instalar no celular (2 minutos)

O site já é um **PWA**: instala como aplicativo, com ícone na tela inicial,
tela cheia sem barra do navegador e funcionamento offline. Não precisa de loja
de aplicativos, nem de taxa de desenvolvedor.

### Android (Chrome)
1. Abra o endereço do site.
2. Toque no botão verde **📲 Instalar App** que aparece no topo.
   *(ou no menu ⋮ → "Instalar aplicativo")*

### iPhone (Safari)
1. Abra o endereço **no Safari** (não funciona pelo Chrome no iOS).
2. Toque em **Compartilhar** (quadrado com seta para cima).
3. Role e toque em **"Adicionar à Tela de Início"**.

Depois de instalado, o app abre em tela cheia e continua funcionando sem
internet, usando os últimos dados baixados.

---

## Sobre publicar nas lojas de aplicativos

Só vale a pena se você quiser distribuir para estranhos. Para uso próprio e dos
amigos da liga, o PWA entrega a mesma experiência de graça.

| Caminho | Custo | Observação |
|---|---|---|
| PWA (este guia) | **R$ 0** | Instala direto pelo navegador |
| Google Play | US$ 25 (uma vez) | Empacotar com pwabuilder.com |
| App Store | US$ 99 por ano | Processo de revisão da Apple |

---

## Sobre automatizar a atualização dos dados

A tentação natural é agendar isso no GitHub Actions. **Provavelmente não vai
funcionar**: os runners do GitHub Actions rodam no Azure, que está na lista de
IPs bloqueados pela NBA.

Antes de investir tempo nisso, teste. Crie o arquivo
`.github/workflows/teste.yml` com um passo que rode `python gerar_dados.py` e
veja se passa. O script já informa claramente se o IP foi bloqueado.

Alternativas, se o teste falhar:
- **Agendador local** (mais simples): Agendador de Tarefas no Windows ou `cron`
  no Linux/Mac, rodando `gerar_dados.py` seguido de um `git push`.
- **Proxy residencial**: existem serviços com nível gratuito limitado, mas
  adicionam complexidade e um ponto de falha. Só considere se a atualização
  manual realmente incomodar.

Como seus dados de fantasy mudam no máximo uma vez por dia, rodar dois comandos
manualmente costuma ser mais confiável do que manter uma automação frágil.

---

## Estrutura final do projeto

```
seu-projeto/
├── index.html          ← o app inteiro
├── dados.json          ← gerado por gerar_dados.py  (PUBLICAR)
├── manifest.json       ← identidade do app no celular
├── sw.js               ← cache offline
├── icone-192.png
├── icone-512.png
├── netlify.toml        ← configuração de cache
│
├── gerar_dados.py      ← roda na sua máquina
├── importar_csv.py     ← roda na sua máquina
├── elencos_brutos.csv  ← sua base de elencos e salários
├── elencos.json        ← gerado por importar_csv.py
├── app.py              ← só para desenvolvimento local
└── requirements.txt
```

---

## Resolução de problemas

**O site abre mas mostra faixa vermelha de erro**
O `dados.json` não foi publicado junto. Confirme que ele está na mesma pasta do
`index.html` no servidor.

**Atualizei os dados mas o celular mostra os antigos**
O service worker está servindo do cache. Feche e reabra o app. Se persistir,
incremente `VERSAO_CACHE` no `sw.js` (de `fantasy-v1` para `fantasy-v2`) e
publique de novo.

**O botão Instalar não aparece no Android**
Ele só aparece em conexão HTTPS (Netlify e GitHub Pages já fornecem) e se o app
ainda não estiver instalado. Use o menu ⋮ → "Instalar aplicativo".

**`gerar_dados.py` dá timeout**
Seu IP foi bloqueado pela NBA. Desligue a VPN, ou tente de outra rede. Se
funcionava e parou, aguarde alguns minutos: há limite de requisições.
