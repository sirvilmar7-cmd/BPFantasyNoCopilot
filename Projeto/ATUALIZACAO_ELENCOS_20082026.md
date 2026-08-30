# Atualização de elencos — 20/08/2026

Fonte: `Ligas 20082026.rar`.

## Resultado da importação

| Liga | Franquias | Vínculos de jogadores | Ano-base dos contratos |
|---|---:|---:|---:|
| Liga 3 | 24 | 360 | 2025 |
| Liga 5 | 24 | 349 | 2025 |
| Liga 6 | 24 | 341 | 2025 |
| Liga 9 | 24 | 344 | 2026 |
| Liga Camaradas | 24 | 313 | 2026 |
| Liga Dinasty | 30 | 468 | 2026 |
| **Total** | **150** | **2.175** | — |

Foram reconhecidos 540 jogadores únicos. Todos já existiam no banco estatístico da temporada 2025–26; por isso, os elencos e salários puderam ser atualizados sem uma nova consulta à API da NBA.

Em relação à planilha anterior, a importação contém 98 novos vínculos, 24 vínculos removidos e 130 mudanças de franquia.

## Ajustes adicionais

- O ano-base da Liga Dinasty passou de 2025 para 2026, conforme o cabeçalho dos arquivos recebidos.
- Foram consolidadas duas duplicidades de grafia causadas pela presença opcional do sufixo `Jr.`:
  - Labaron Philon / Labaron Philon Jr.;
  - Morez Johnson / Morez Johnson Jr.
- O banco final possui 618 registros NBA, dos quais 540 estão em pelo menos uma liga fantasy.
- O arquivo de picks disponível contém somente o cabeçalho; portanto, esta atualização não inclui escolhas de draft cadastradas.

## Arquivos que devem ser copiados

Para atualizar o site, substitua principalmente:

- `index.html`
- `dados.json`
- `elencos.json`
- `elencos_brutos.csv`

Os demais arquivos incluídos no pacote mantêm o gerador e os importadores sincronizados com a versão do site.

Não é necessário executar `gerar_dados.py` para usar esta atualização: `dados.json` já contém os elencos novos. Execute o gerador somente quando desejar renovar também as estatísticas da NBA.

## Validações realizadas

- 2.175 vínculos importados e 2.175 vínculos encontrados em `dados.json`.
- Nenhum jogador do RAR ficou sem correspondência no banco estatístico.
- Nenhuma duplicidade jogador/liga permaneceu na importação.
- Todas as 150 franquias foram reconhecidas.
- Todos os jogadores possuem salário no ano-base correspondente à sua liga.
- Sintaxe dos quatro scripts Python verificada.

