"""Validação rápida dos arquivos publicados pelo Gerenciador Fantasy.

Execute na pasta do projeto:
    python validar_dados.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


RAIZ = Path(__file__).resolve().parent


def carregar(nome: str):
    with (RAIZ / nome).open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def main() -> None:
    dados = carregar("dados.json")
    elencos = carregar("elencos.json")
    hashtag = carregar("hashtag_projecoes_2026_27.json")
    jogadores = dados["jogadores"]

    nomes = [j["nome"] for j in jogadores]
    assert len(nomes) == len(set(nomes)), "Há jogadores duplicados em dados.json"

    total_elencos = sum(
        len(franquia.get("jogadores", {}))
        for liga in elencos.values()
        for franquia in liga.values()
    )
    total_vinculos = sum(len(j.get("status_fantasy", {})) for j in jogadores)
    assert total_elencos == total_vinculos, (
        f"Elencos têm {total_elencos} vínculos, mas dados.json tem {total_vinculos}"
    )

    por_liga_elencos = {
        liga: sum(len(f.get("jogadores", {})) for f in franquias.values())
        for liga, franquias in elencos.items()
    }
    por_liga_dados = {
        liga: sum(liga in j.get("status_fantasy", {}) for j in jogadores)
        for liga in elencos
    }
    assert por_liga_elencos == por_liga_dados, "Contagens por liga não conferem"

    fonte = Counter(j.get("fonte_estatistica") for j in jogadores)
    assert set(fonte) <= {"nba", "hashtag_fallback", "projecao_app"}, (
        f"Fonte estatística desconhecida: {fonte}"
    )
    assert dados.get("ordem_fallback_projecao") == ["nba", "hashtag", "projecao_app"]

    registros_hashtag = hashtag["jogadores"]
    ranks = [j["rank_hashtag"] for j in registros_hashtag]
    assert ranks == list(range(1, len(registros_hashtag) + 1)), "Ranking Hashtag não é sequencial"
    data_hashtag = hashtag["metadados"]["atualizado_na_fonte"]
    assert dados.get("hashtag_atualizado_em") == data_hashtag

    direitos = {}
    for liga in elencos:
        direitos[liga] = sum(
            1
            for j in jogadores
            if liga in j.get("status_fantasy", {})
            and float(j.get("salarios_fantasy", {}).get(liga, {}).get("2026", 0) or 0) <= 0
        )

    print("VALIDAÇÃO CONCLUÍDA")
    print(f"Jogadores no app: {len(jogadores)}")
    print(f"Vínculos de elenco: {total_vinculos} em {len(elencos)} ligas")
    print(f"Projeções Hashtag: {len(registros_hashtag)} · fonte atualizada em {data_hashtag}")
    print("Fontes estatísticas:", dict(fonte))
    print("Direitos sem contrato 2026-27:", direitos)


if __name__ == "__main__":
    main()
