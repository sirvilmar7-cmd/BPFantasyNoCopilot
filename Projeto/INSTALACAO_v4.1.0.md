# Atualização v4.1.0 - novo relatório executivo

## Arquivos para publicar

Copie para a raiz do projeto, substituindo as versões existentes:

1. `index.html`
2. `sw.js`
3. `dados.json`
4. `hashtag_projecoes_2026_27.json`

O `dados.json` fornecido mantém a cópia incorporada das projeções Hashtag. O
arquivo Hashtag separado continua incluído como compatibilidade.

## O que mudou

O relatório executivo deixou de ser um mosaico de indicadores e passou a ter
cinco abas:

- Resumo
- Categorias
- Escalações
- Riscos
- Plano de Ação

O relatório compara automaticamente a produção NBA 2025-26 com a projeção
Hashtag 2026-27. Power Ranking, H2H, disponibilidade, escalações, matriz de
categorias e risco de ausência são recalculados para a franquia selecionada.

O botão `Exportar relatório completo em PDF` imprime as cinco abas, uma por
página, mesmo que apenas uma aba esteja visível na tela.

## Depois do deploy

Abra o site conectado à internet e use `Ctrl + F5`. A versão exibida no rodapé
deve ser `App v4.1.0`; o service worker usa o cache `fantasy-v17`.
