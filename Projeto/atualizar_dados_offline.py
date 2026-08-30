"""Atualiza vínculos, contratos e fallbacks sem consultar novamente a NBA.

Uso recomendado após converter/importar os arquivos das ligas:

    python atualizar_dados_offline.py

O script preserva as estatísticas NBA já existentes em ``dados.json``. Para
jogadores sem produção NBA, a ordem aplicada é Hashtag -> projeção interna já
existente -> registro neutro. A gravação é atômica para não corromper a base.
"""

from __future__ import annotations

import argparse
import json
import os
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


CATEGORIAS = ("pts", "reb", "ast", "stl", "blk", "fg3m", "tov")
SUFIXOS = {"jr", "sr", "ii", "iii", "iv", "v"}


def normalizar_nome(nome: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", nome or "")
        if unicodedata.category(c) != "Mn"
    ).lower().strip()


def chave_join(nome: str) -> str:
    partes = normalizar_nome(nome).replace(".", "").replace(",", "").split()
    while len(partes) > 2 and partes[-1] in SUFIXOS:
        partes.pop()
    return " ".join(partes)


def carregar_elencos(caminho: Path):
    bruto = json.loads(caminho.read_text(encoding="utf-8-sig"))
    times, salarios, metadados, picks = {}, {}, {}, {}
    nomes = {}
    for liga, franquias in bruto.items():
        for franquia, conteudo in franquias.items():
            jogadores = conteudo.get("jogadores", {}) if isinstance(conteudo, dict) else {}
            if isinstance(conteudo, dict) and conteudo.get("picks"):
                picks.setdefault(liga, {})[franquia] = conteudo["picks"]
            for nome, meta in jogadores.items():
                chave = normalizar_nome(nome)
                nomes.setdefault(chave, nome)
                times.setdefault(chave, {})[liga] = franquia
                meta = meta if isinstance(meta, dict) else {}
                if meta.get("salarios") is not None:
                    salarios.setdefault(chave, {})[liga] = meta.get("salarios") or {}
                registro = metadados.setdefault(chave, {})
                for campo in ("idade", "posicao", "draft_pick", "lesao", "ano_retorno"):
                    if meta.get(campo) is not None:
                        registro.setdefault(campo, meta[campo])
    return times, salarios, metadados, nomes, picks


def indice_unico_por_join(mapa: dict) -> dict:
    grupos = {}
    for chave in mapa:
        grupos.setdefault(chave_join(chave), []).append(chave)
    return {join: chaves[0] for join, chaves in grupos.items() if len(chaves) == 1}


def localizar_chave(nome: str, mapa: dict, unicos_join: dict) -> str | None:
    exata = normalizar_nome(nome)
    if exata in mapa:
        return exata
    return unicos_join.get(chave_join(nome))


def registro_neutro(nome: str, ligas: dict, salarios: dict, meta: dict) -> dict:
    return {
        "nome": nome,
        "status_fantasy": ligas,
        "salarios_fantasy": salarios,
        "posicao": str(meta.get("posicao") or "N/D").replace("/", "-"),
        "idade": meta.get("idade"),
        "time": "N/D",
        "gp": 0,
        "min": 0,
        **{c: 0 for c in CATEGORIAS},
        **{f"z_{c}": 0 for c in CATEGORIAS},
        **{f"z_pm_{c}": 0 for c in CATEGORIAS},
        **{f"desvio_{c}": 0 for c in CATEGORIAS},
        "rating": None,
        "rating_pm": None,
        "projetado": True,
        "origem_projecao": "Projeção subsidiária do app sem base estatística",
        "fonte_estatistica": "projecao_app",
        "historico": [],
        "splits": {},
        "rank_absoluto": None,
    }


def carregar_hashtag(caminho: Path | None):
    if not caminho or not caminho.exists():
        return None, {}, {}
    pacote = json.loads(caminho.read_text(encoding="utf-8-sig"))
    mapa = {}
    for jogador in pacote.get("jogadores", []):
        for nome in (jogador.get("nome_app"), jogador.get("nome")):
            if nome:
                mapa.setdefault(normalizar_nome(nome), jogador)
    unicos_join = indice_unico_por_join(mapa)
    return pacote, mapa, unicos_join


def aplicar_hashtag(jogador: dict, projecao: dict, atualizado_em: str | None):
    jogador["gp"] = projecao.get("gp", 0)
    jogador["min"] = projecao.get("min", 0)
    for categoria in CATEGORIAS:
        jogador[categoria] = projecao.get(categoria, 0)
        jogador[f"z_{categoria}"] = projecao.get(f"z_{categoria}", 0)
        # A fonte Hashtag é por jogo. Repetir o perfil mantém o jogador
        # analisável, mas o frontend identifica que não há medição por minuto.
        jogador[f"z_pm_{categoria}"] = projecao.get(f"z_{categoria}", 0)
    jogador["rating"] = projecao.get("rating_7cat")
    jogador["rating_pm"] = projecao.get("rating_7cat")
    jogador["posicao"] = projecao.get("posicao") or jogador.get("posicao") or "N/D"
    jogador["time"] = projecao.get("time_nba") or jogador.get("time") or "N/D"
    jogador["projetado"] = True
    jogador["tipo_projecao"] = "hashtag"
    jogador["origem_projecao"] = "Hashtag Basketball 2026-27 (fallback)"
    jogador["fonte_estatistica"] = "hashtag_fallback"
    jogador["modo_minuto_indisponivel"] = True
    data = atualizado_em or "data não informada"
    jogador["detalhe_projecao"] = (
        f"Sem produção NBA disponível. Projeção Hashtag 2026-27 atualizada em {data}."
    )


def gravar_atomico(caminho: Path, dados: dict):
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    temporario.write_text(
        json.dumps(dados, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(temporario, caminho)


def atualizar(dados_path: Path, elencos_path: Path, hashtag_path: Path | None):
    dados = json.loads(dados_path.read_text(encoding="utf-8-sig"))
    jogadores = dados.get("jogadores", [])
    times, salarios, metas, nomes, picks = carregar_elencos(elencos_path)
    joins_elenco = indice_unico_por_join(times)

    casados = set()
    for jogador in jogadores:
        chave = localizar_chave(jogador.get("nome", ""), times, joins_elenco)
        if chave:
            jogador["status_fantasy"] = times.get(chave, {})
            jogador["salarios_fantasy"] = salarios.get(chave, {})
            casados.add(chave)
        else:
            jogador["status_fantasy"] = {}
            jogador["salarios_fantasy"] = {}
        if not jogador.get("projetado"):
            jogador["fonte_estatistica"] = "nba"
        elif not jogador.get("fonte_estatistica"):
            jogador["fonte_estatistica"] = "projecao_app"

    adicionados = 0
    for chave, ligas in times.items():
        if chave in casados:
            continue
        nome = nomes[chave]
        jogadores.append(registro_neutro(
            nome, ligas, salarios.get(chave, {}), metas.get(chave, {})
        ))
        adicionados += 1

    pacote_hashtag, mapa_hashtag, joins_hashtag = carregar_hashtag(hashtag_path)
    fallback_hashtag = 0
    fallback_app = 0
    atualizado_hashtag = None
    if pacote_hashtag:
        atualizado_hashtag = pacote_hashtag.get("metadados", {}).get("atualizado_na_fonte")
    for jogador in jogadores:
        if not jogador.get("projetado") and jogador.get("rating") is not None:
            continue
        chave_h = localizar_chave(jogador.get("nome", ""), mapa_hashtag, joins_hashtag)
        if chave_h:
            aplicar_hashtag(jogador, mapa_hashtag[chave_h], atualizado_hashtag)
            fallback_hashtag += 1
        else:
            jogador["fonte_estatistica"] = "projecao_app"
            fallback_app += 1

    com_rating = sorted(
        (j for j in jogadores if j.get("rating") is not None),
        key=lambda j: j.get("rating", -99), reverse=True,
    )
    for posicao, jogador in enumerate(com_rating, 1):
        jogador["rank_absoluto"] = posicao
    for jogador in jogadores:
        if jogador.get("rating") is None:
            jogador["rank_absoluto"] = None

    agora = datetime.now(timezone.utc).isoformat()
    dados["jogadores"] = jogadores
    dados["total_jogadores"] = len(jogadores)
    dados["picks"] = picks
    dados["elencos_atualizados_em"] = agora
    dados["ordem_fallback_projecao"] = ["nba", "hashtag", "projecao_app"]
    if pacote_hashtag:
        dados["hashtag_projecoes_2026_27"] = pacote_hashtag
        dados["hashtag_atualizado_em"] = atualizado_hashtag
    gravar_atomico(dados_path, dados)

    print(json.dumps({
        "jogadores": len(jogadores),
        "novos_jogadores_de_elenco": adicionados,
        "fallback_hashtag": fallback_hashtag,
        "fallback_app": fallback_app,
        "elencos_atualizados_em": agora,
    }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dados", type=Path, default=Path("dados.json"))
    parser.add_argument("--elencos", type=Path, default=Path("elencos.json"))
    parser.add_argument("--hashtag", type=Path, default=Path("hashtag_projecoes_2026_27.json"))
    args = parser.parse_args()
    atualizar(args.dados.resolve(), args.elencos.resolve(), args.hashtag.resolve())


if __name__ == "__main__":
    main()
