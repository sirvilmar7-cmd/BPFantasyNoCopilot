# Gerenciador Fantasy NBA — v4.2.0

## Dados atualizados

- Elencos das seis ligas importados do pacote de 28/08/2026.
- Projeções Hashtag atualizadas na fonte em 27/08/2026.
- 430 projeções processadas; 425 conciliadas com o banco do app e 5 mantidas
  apenas na visão Hashtag.
- `dados.json` preserva a data da coleta NBA e registra separadamente a data de
  atualização dos elencos e do Hashtag.

## Alterações funcionais

1. A visão de liga mostra salário 2026-27 e duração positiva consecutiva do
   contrato. Jogadores sem contrato atual aparecem como direitos.
2. O simulador de contratação lista agentes livres e todos os jogadores com
   direitos. A partir da correção v4.2.1, apenas nesta simulação todos são
   tratados como agentes livres comuns, sem bloqueio por negociação prévia.
3. A Saúde Financeira ganhou quantidade e qualidade dos direitos, custo de
   renovação estimado e ranking de risco. A estimativa usa a mediana dos
   contratos de jogadores de produção semelhante dentro da própria liga.
4. A ordem de fallback estatístico agora é NBA, Hashtag e projeção interna do
   app. O gerador e o atualizador offline aplicam a mesma regra. Na visão NBA,
   o selo `HASHTAG` identifica quando a projeção substituiu uma amostra ausente.
5. A carência posicional do Buscador de Trocas usa profundidade ponderada
   3/2/1. Vagas ausentes recebem piso de reposição de -0,50 Z, evitando que um
   astro sem reserva esconda uma necessidade real.
6. Rótulos foram associados aos controles, elementos clicáveis ganharam
   operação por teclado, o modal recebeu semântica de diálogo e a barra móvel
   passou a usar alvos maiores com rolagem horizontal controlada.
7. Foi criado o painel `NBA × Hashtag`, com maiores altas, quedas e divergências
   de ranking.
8. Diagnósticos, alvos e propostas agora exibem uma explicação objetiva dos
   fatores usados na recomendação.

## Arquivos principais para publicação

- `index.html`
- `dados.json`
- `hashtag_projecoes_2026_27.json`
- `manifest.json`
- `sw.js`
- `icone-192.png`
- `icone-512.png`
- `netlify.toml` quando a hospedagem for Netlify

## Atualizações futuras sem nova consulta à NBA

Depois de converter e importar novos arquivos de liga, execute:

```text
python atualizar_dados_offline.py
```

O script atualiza vínculos e contratos, aplica o fallback Hashtag e grava
`dados.json` de forma atômica. Para uma temporada NBA completamente nova,
continue usando `gerar_dados.py`.

## Verificação rápida

Antes de publicar, execute:

```text
python validar_dados.py
```

O validador confere os vínculos das seis ligas, duplicidades, sequência do
ranking Hashtag, data da fonte e distribuição do fallback estatístico.
