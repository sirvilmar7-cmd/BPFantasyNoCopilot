# Instalação da versão 4.0

## Atualização mínima

Copie estes arquivos para a raiz do projeto, substituindo as versões existentes quando houver:

1. `index.html`
2. `sw.js`
3. `netlify.toml`
4. `manifest.json`
5. `hashtag_projecoes_2026_27.json`

O `dados.json` e o `elencos.json` atuais podem ser mantidos.

Depois de publicar, abra o site conectado à internet. O `sw.js` usa o cache `fantasy-v15`, assume a nova versão e passa a buscar o JSON Hashtag pela rede antes de recorrer ao cache.

## Pacote completo

Também é fornecido um ZIP completo do projeto. Ele pode ser extraído em uma pasta nova e publicado diretamente. O projeto continua sem etapa de compilação: o Netlify publica a própria raiz.

## Atualizar as projeções futuramente

O `converter_hashtag.py` pode ser colocado na raiz do projeto. Com um novo TXT no mesmo formato:

```powershell
python converter_hashtag.py --origem "Ligas/Hashtag projeções.txt" --dados-app "dados.json" --saida "."
```

Isso recria `hashtag_projecoes_2026_27.json` e o CSV de conferência.

## Exportar um relatório executivo

1. Na tabela principal, selecione a liga.
2. Selecione a franquia.
3. Clique em `Visão Executiva / PDF`.
4. Revise a visão gerada.
5. Clique em `Gerar PDF` e escolha `Salvar como PDF` no navegador.
