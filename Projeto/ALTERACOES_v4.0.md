# Gerenciador Fantasy v4.0

## 1. Mercado: livres, direitos e elenco ativo

O site agora diferencia três situações em cada liga:

- **Elenco ativo:** jogador vinculado à franquia e com contrato normal.
- **Agente livre:** jogador sem franquia cadastrada naquela liga.
- **Direitos presos:** jogador com franquia cadastrada e contrato-base zerado.

Ausência de informação salarial não é interpretada automaticamente como contrato zerado. Jogadores com direitos presos deixam de inflar escalações, idade, profundidade e Power Ranking antes de serem efetivamente contratados.

Na tabela principal, o filtro de franquia recebeu as opções `Agentes livres`, `Direitos presos` e `Todo o mercado disponível`.

## 2. Simulador de contratação

O Avaliador de Trocas recebeu uma área de contratação. Ela permite escolher liga, franquia, jogador e salário proposto. O resultado mostra:

- ganho ou perda na escalação ideal;
- Power Ranking antes e depois;
- campanha H2H antes e depois;
- radar das sete categorias;
- nova escalação ideal;
- entrada ou não do contratado entre os titulares;
- nova folha e validação do teto.

Agentes sem franquia podem ser simulados por qualquer equipe. Um jogador com direitos zerados só pode ser contratado diretamente pela franquia detentora; as demais recebem o aviso de que precisam negociar os direitos.

## 3. Mercado no Buscador de Trocas

Depois de selecionar liga e franquia, o Buscador mostra os doze jogadores disponíveis com maior impacto potencial na escalação. A lista mistura agentes livres e direitos presos, identifica o detentor e informa quando é necessária uma negociação de direitos.

## 4. Visão Hashtag 2026-27

O seletor de fonte no topo alterna todo o app entre:

- produção NBA 2025-26;
- projeções Hashtag Basketball 2026-27.

Na visão Hashtag, ranking, H2H, trocas, mercado, diagnóstico, radares e relatório executivo passam a usar as médias e z-scores projetados. A interface assume identidade âmbar/roxa e exibe um aviso permanente. Recortes de período e eficiência por minuto ficam desabilitados porque não existem na fonte Hashtag.

O arquivo `hashtag_projecoes_2026_27.json` possui 428 projeções: 423 conciliadas com o cadastro do app e cinco atletas adicionais sem vínculo fantasy conhecido.

## 5. Impacto H2H de trocas

O relatório pós-troca agora inclui, para as duas franquias:

- campanha H2H virtual antes e depois;
- nova escalação ideal de seis jogadores;
- posição no Power Ranking antes e depois;
- radares sobrepostos antes/depois já existentes.

## 6. Visão executiva e PDF

Ao abrir o diagnóstico de uma franquia, o botão `Visão Executiva / PDF` gera uma página própria com:

- posição e score no Power Ranking;
- campanha H2H;
- composição do elenco;
- radar das sete categorias;
- escalação ideal;
- pontos fortes e riscos;
- recomendação estratégica;
- principais ativos, folha e espaço no teto;
- oportunidades de mercado.

O botão `Gerar PDF` abre a impressão nativa do navegador já formatada em A4. No diálogo, escolha **Salvar como PDF**.

## Arquivos alterados ou adicionados

- `index.html`
- `sw.js`
- `netlify.toml`
- `manifest.json`
- `hashtag_projecoes_2026_27.json`
- `converter_hashtag.py`

O `dados.json` foi preservado; a visão Hashtag funciona como camada separada e reversível.

## Validação executada

- 618 jogadores carregados na visão NBA.
- 428 jogadores carregados na visão Hashtag.
- 141 direitos presos identificados na Liga Dinasty durante o teste de interface.
- Power Ranking Hashtag da Liga 6 calculado com 24 franquias.
- Filtro, mercado, contratação, avaliação H2H de troca e relatório executivo exercitados sem erros JavaScript.
- PDF executivo de Terraplanilhistas renderizado em A4 e revisado visualmente.
