# Instalação da correção v4.0.1

## Atualização mínima

Copie estes arquivos para a raiz do projeto, substituindo as versões existentes quando houver:

1. `index.html`
2. `dados.json`
3. `sw.js`
4. `hashtag_projecoes_2026_27.json` (cópia externa de compatibilidade)

Nesta correção, `dados.json` também precisa ser substituído: ele agora contém
uma cópia incorporada das 428 projeções Hashtag. O `elencos.json` atual pode ser
mantido.

Depois de publicar, abra o site conectado à internet. O `sw.js` usa o cache
`fantasy-v16`. O seletor Hashtag funciona mesmo que o arquivo JSON separado
seja omitido do deploy, pois o app usa primeiro a cópia em `dados.json`.

## Pacote completo

Também é fornecido um ZIP completo do projeto. Ele pode ser extraído em uma pasta nova e publicado diretamente. O projeto continua sem etapa de compilação: o Netlify publica a própria raiz.

## Atualizar as projeções futuramente

O `converter_hashtag.py` pode ser colocado na raiz do projeto. Com um novo TXT no mesmo formato:

```powershell
python converter_hashtag.py --origem "Ligas/Hashtag projeções.txt" --dados-app "dados.json" --saida "."
```

Isso recria `hashtag_projecoes_2026_27.json`, o CSV de conferência e atualiza
automaticamente a cópia incorporada em `dados.json`.

## Exportar um relatório executivo

1. Na tabela principal, selecione a liga.
2. Selecione a franquia.
3. Clique em `Visão Executiva / PDF`.
4. Revise a visão gerada.
5. Clique em `Gerar PDF` e escolha `Salvar como PDF` no navegador.
