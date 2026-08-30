# Correções v4.1.1 - direitos com contrato zerado

## Regra consolidada

Jogadores com franquia cadastrada e contrato zerado continuam vinculados
esportivamente à franquia detentora dos direitos.

Eles agora contam normalmente em:

- escalações do Simulador H2H;
- Power Ranking e campanha H2H virtual;
- Avaliador de Trocas;
- ativos oferecidos e procurados no Buscar Trocas;
- diagnóstico e relatório executivo da franquia;
- escalação-base do Simulador de Contratação.

O contrato zerado continua sendo usado para identificá-los nos filtros de
mercado e para permitir que a própria franquia simule um novo contrato.

Ao simular a assinatura de um jogador cujos direitos já pertencem à franquia,
o app não duplica o atleta na escalação: somente a folha salarial é alterada.

## Remoção solicitada

Foi removido do Buscar Trocas o bloco `Mercado sem contrato - maior impacto
potencial`. Os jogadores com direitos continuam disponíveis nas listas de
ativos negociáveis de suas respectivas franquias.

## Publicação

Substitua `index.html` e `sw.js` na raiz do site. Os arquivos de dados incluídos
no pacote são os mesmos da versão anterior e servem apenas para facilitar uma
publicação completa.

Após o deploy, use `Ctrl + F5`. O rodapé deve mostrar `App v4.1.1` e o service
worker deve usar o cache `fantasy-v18`.
