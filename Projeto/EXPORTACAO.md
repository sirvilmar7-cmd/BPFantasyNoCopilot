# Exportação de tabelas

Todas as tabelas do app ganharam dois botões: **📊 Excel** e **📄 PDF**.

| Tabela | Onde |
|---|---|
| Jogadores | tela principal |
| Power Ranking (4 tabelas) | painel Power Ranking |
| Saúde Financeira e Curva de Compromisso | painel Saúde Financeira |
| Comparação de Jogadores | painel Comparar |
| Simulação H2H | painel Simulador |
| Avaliação de Troca | painel Avaliador |

## Excel: por que CSV e não .xlsx

Gerar `.xlsx` de verdade exigiria uma biblioteca externa, e o projeto é
deliberadamente sem dependências de front. O CSV abre nativamente no Excel,
no LibreOffice e no Google Sheets.

Três decisões importantes para o Excel **em português**:

**Separador ponto e vírgula.** No Excel configurado em pt-BR, a vírgula é
separador decimal. Um CSV com vírgulas abriria com todas as colunas amontoadas
numa só. Com `;` cada coluna cai no lugar certo.

**Decimais com vírgula.** `2.33` seria lido como texto ou convertido em data.
`2,33` é reconhecido como número, o que permite somar, ordenar e fazer
gráficos direto na planilha.

**BOM UTF-8** no início do arquivo, senão acentos e nomes como *Jokić* viram
símbolos.

## Nome do arquivo registra o contexto

O nome inclui o que estava ativo no momento da exportação:

```
Jogadores_2026-08-15.csv
Jogadores_Ultimos_15_dias_2026-08-15.csv
Jogadores_sem_TOV_por_minuto_2026-08-15.csv
```

Sem isso, duas exportações do mesmo painel ficariam indistinguíveis depois de
salvas, e você não saberia qual recorte gerou qual número.

## PDF

Usa a impressão nativa do navegador. A tabela é clonada para uma área isolada,
e todo o resto da página some na impressão: dos 20 blocos do corpo da página,
apenas a área de impressão fica visível.

O cabeçalho impresso traz o nome da tabela, data e hora, e o mesmo contexto de
recorte e categorias. No diálogo que abrir, escolha **Salvar como PDF**.

Para tabelas largas (Métrica 3, Curva de Compromisso), use **paisagem** nas
opções de impressão.

## Colunas ocultas

Colunas escondidas na tela, como as métricas intermediárias do Power Ranking no
celular, também não são exportadas. O arquivo reflete o que você está vendo.
