"""Converte a copia textual das projecoes Hashtag em CSV/JSON normalizados.

O arquivo de origem mistura uma linha tabulada por jogador com sete linhas
numericas subsequentes. Este conversor preserva os valores da fonte e calcula
um rating separado, restrito as sete categorias utilizadas pelo app.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


CATEGORIAS = ["fg3m", "pts", "reb", "ast", "stl", "blk", "tov"]
SUFIXOS = {"jr", "sr", "ii", "iii", "iv", "v"}
MESES_INGLES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

# Variacoes confirmadas por correspondencia inequívoca com o banco atual.
# A chave e o nome da fonte; o valor e a grafia usada no app.
ALIASES_APP = {
    "alexandre sarr": "Alex Sarr",
    "nicolas claxton": "Nic Claxton",
    "ron holland ii": "Ronald Holland II",
}


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


def numero_opcional(texto: str):
    texto = (texto or "").strip()
    return float(texto) if texto else None


def data_atualizacao_fonte(linhas: list[str]) -> str | None:
    """Extrai a data declarada pelo Hashtag em vez de manter data fixa no código."""
    for linha in linhas[:80]:
        m = re.search(r"Updated:\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", linha, re.I)
        if not m:
            continue
        mes = MESES_INGLES.get(m.group(2).lower())
        if mes:
            return f"{int(m.group(3)):04d}-{mes:02d}-{int(m.group(1)):02d}"
    return None


def ler_registros(linhas: list[str]) -> tuple[list[dict], list[dict]]:
    registros = []
    erros = []
    i = 0
    while i < len(linhas):
        partes = linhas[i].split("\t")
        cabecalho_valido = (
            len(partes) == 8
            and re.fullmatch(r"\d+(?:\s+\d+)?", partes[0].strip())
        )
        if not cabecalho_valido:
            i += 1
            continue

        extras = linhas[i + 1:i + 8]
        if len(extras) != 7:
            erros.append({"linha": i + 1, "motivo": "registro incompleto"})
            break

        try:
            campo_rank = partes[0].split()
            registro = {
                "rank_hashtag": int(campo_rank[0]),
                # O TXT perdeu o icone/seta de direcao. Preservamos apenas o
                # numero visivel e nao inferimos se significa alta ou queda.
                "indicador_rank_bruto": int(campo_rank[1]) if len(campo_rank) > 1 else None,
                "nome": partes[1].strip(),
                "nome_normalizado": normalizar_nome(partes[1]),
                "chave_join": chave_join(partes[1]),
                "adp": numero_opcional(partes[2]),
                "posicao": partes[3].strip() or None,
                "time_nba": partes[4].strip() or None,
                "gp": int(partes[5]),
                "min": float(partes[6]),
                "fg3m": float(partes[7]),
                "pts": float(extras[0]),
                "reb": float(extras[1]),
                "ast": float(extras[2]),
                "stl": float(extras[3]),
                "blk": float(extras[4]),
                "tov": float(extras[5]),
                "total_hashtag": float(extras[6]),
                "linha_origem": i + 1,
            }
            registros.append(registro)
        except (TypeError, ValueError) as exc:
            erros.append({"linha": i + 1, "motivo": str(exc), "conteudo": linhas[i]})
        i += 8
    return registros, erros


def calcular_rating_7cat(registros: list[dict]) -> dict:
    medias = {c: statistics.fmean(r[c] for r in registros) for c in CATEGORIAS}
    desvios = {c: statistics.pstdev(r[c] for r in registros) or 1.0 for c in CATEGORIAS}

    for r in registros:
        for c in CATEGORIAS:
            z = (r[c] - medias[c]) / desvios[c]
            r[f"z_{c}"] = round(-z if c == "tov" else z, 6)
        rating = statistics.fmean(r[f"z_{c}"] for c in CATEGORIAS)
        bonus_gp = min((r["gp"] / 82) * 0.20, 0.20)
        rating_gp = rating * (1 + bonus_gp) if rating > 0 else rating * (1 - bonus_gp)
        r["rating_7cat"] = round(rating, 6)
        r["bonus_gp_app"] = round(bonus_gp, 6)
        r["rating_7cat_gp20"] = round(rating_gp, 6)

    por_rating = sorted(registros, key=lambda x: x["rating_7cat"], reverse=True)
    por_rating_gp = sorted(registros, key=lambda x: x["rating_7cat_gp20"], reverse=True)
    for rank, r in enumerate(por_rating, 1):
        r["rank_7cat"] = rank
    for rank, r in enumerate(por_rating_gp, 1):
        r["rank_7cat_gp20"] = rank

    return {"medias": medias, "desvios_populacionais": desvios}


def conciliar_com_app(registros: list[dict], dados_app: Path) -> dict:
    if not dados_app.exists():
        for r in registros:
            r.update({"match_app": "dados_app_indisponiveis", "nome_app": None, "ligas_fantasy": {}})
        return {"arquivo_disponivel": False}

    dados = json.loads(dados_app.read_text(encoding="utf-8-sig"))
    jogadores = dados.get("jogadores", [])
    por_exato = {}
    por_join = {}
    for jogador in jogadores:
        por_exato.setdefault(normalizar_nome(jogador.get("nome", "")), []).append(jogador)
        por_join.setdefault(chave_join(jogador.get("nome", "")), []).append(jogador)

    contagem = Counter()
    ambiguos = []
    for r in registros:
        candidatos = por_exato.get(r["nome_normalizado"], [])
        tipo = "exato"
        if not candidatos and r["nome_normalizado"] in ALIASES_APP:
            candidatos = por_exato.get(normalizar_nome(ALIASES_APP[r["nome_normalizado"]]), [])
            tipo = "alias_curado"
        if not candidatos:
            candidatos = por_join.get(r["chave_join"], [])
            tipo = "tolerante_sufixo"
        if len(candidatos) == 1:
            jogador = candidatos[0]
            r["match_app"] = tipo
            r["nome_app"] = jogador.get("nome")
            r["ligas_fantasy"] = jogador.get("status_fantasy") or {}
        elif not candidatos:
            r["match_app"] = "nao_encontrado"
            r["nome_app"] = None
            r["ligas_fantasy"] = {}
        else:
            r["match_app"] = "ambiguo"
            r["nome_app"] = None
            r["ligas_fantasy"] = {}
            ambiguos.append({"nome": r["nome"], "candidatos": [j.get("nome") for j in candidatos]})
        contagem[r["match_app"]] += 1

    return {
        "arquivo_disponivel": True,
        "temporada_app": dados.get("temporada"),
        "total_jogadores_app": len(jogadores),
        "matches": dict(contagem),
        "ambiguos": ambiguos,
    }


def serializar_csv(registros: list[dict], caminho: Path) -> None:
    campos = [
        "rank_hashtag", "indicador_rank_bruto", "nome", "nome_normalizado", "chave_join",
        "adp", "posicao", "time_nba", "gp", "min", "fg3m", "pts", "reb", "ast",
        "stl", "blk", "tov", "total_hashtag",
        "z_fg3m", "z_pts", "z_reb", "z_ast", "z_stl", "z_blk", "z_tov",
        "rating_7cat", "bonus_gp_app", "rating_7cat_gp20", "rank_7cat",
        "rank_7cat_gp20", "match_app", "nome_app", "ligas_fantasy", "linha_origem",
    ]
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        for registro in registros:
            linha = dict(registro)
            linha["ligas_fantasy"] = json.dumps(linha.get("ligas_fantasy", {}), ensure_ascii=False)
            escritor.writerow({campo: linha.get(campo) for campo in campos})


def incorporar_em_dados_app(pacote: dict, caminho: Path) -> bool:
    """Guarda uma copia das projecoes no dados.json usado pelo site."""
    if not caminho.exists():
        return False
    dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
    if not isinstance(dados, dict):
        return False
    dados["hashtag_projecoes_2026_27"] = pacote
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return True


def main() -> None:
    pasta_atual = Path.cwd()
    parser = argparse.ArgumentParser(description="Estrutura as projeções textuais do Hashtag Basketball.")
    parser.add_argument(
        "--origem", type=Path,
        default=pasta_atual / "Ligas" / "Hashtag projeções.txt",
        help="TXT exportado/copiado do Hashtag Basketball.",
    )
    parser.add_argument(
        "--dados-app", type=Path, default=pasta_atual / "dados.json",
        help="dados.json do app para conciliação de nomes e franquias.",
    )
    parser.add_argument(
        "--saida", type=Path, default=pasta_atual / "dados_hashtag",
        help="Pasta que receberá o JSON e o CSV.",
    )
    args = parser.parse_args()

    origem = args.origem.resolve()
    dados_app = args.dados_app.resolve()
    pasta_saida = args.saida.resolve()
    linhas = origem.read_text(encoding="utf-8-sig").splitlines()
    registros, erros = ler_registros(linhas)
    atualizado_na_fonte = data_atualizacao_fonte(linhas)
    if erros:
        raise RuntimeError(f"Falhas de parsing: {erros[:10]}")
    ranks = [r["rank_hashtag"] for r in registros]
    esperado = list(range(1, max(ranks) + 1))
    if ranks != esperado:
        raise RuntimeError("Ranks fora de sequencia ou registros ausentes")
    if len({r["nome_normalizado"] for r in registros}) != len(registros):
        raise RuntimeError("Nomes duplicados apos normalizacao")

    parametros = calcular_rating_7cat(registros)
    conciliacao = conciliar_com_app(registros, dados_app)

    qualidade = {
        "total_registros": len(registros),
        "ranks": {"min": min(ranks), "max": max(ranks), "sequenciais": True},
        "adp_ausente": sum(r["adp"] is None for r in registros),
        "posicao_ausente": sum(r["posicao"] is None for r in registros),
        "nomes_duplicados": 0,
        "erros_parsing": len(erros),
    }
    metadados = {
        "fonte": "Hashtag Basketball",
        "arquivo_origem": origem.name,
        "temporada": "2026-27",
        "tipo_projecao": "Rest of Season Projections",
        "base": "Averages",
        "formato": "H2H",
        "gp_penalty_fonte": 0.20,
        "atualizado_na_fonte": atualizado_na_fonte,
        "autor_na_fonte": "Joseph Mamone",
        "extraido_em": datetime.now(timezone.utc).isoformat(),
        "categorias_disponiveis": CATEGORIAS,
        "nota_total_hashtag": (
            "TOTAL foi preservado como valor da fonte. O texto informa outros multiplicadores "
            "alem das sete colunas visiveis; portanto TOTAL nao deve ser tratado como rating 7-cat."
        ),
        "nota_indicador_rank": (
            "O segundo numero ao lado do rank perdeu o icone de direcao no TXT; "
            "foi preservado sem interpretacao."
        ),
    }

    pacote = {
        "metadados": metadados,
        "qualidade": qualidade,
        "parametros_7cat": parametros,
        "conciliacao_app": conciliacao,
        "jogadores": registros,
    }

    pasta_saida.mkdir(parents=True, exist_ok=True)
    json_path = pasta_saida / "hashtag_projecoes_2026_27.json"
    csv_path = pasta_saida / "hashtag_projecoes_2026_27.csv"
    json_path.write_text(json.dumps(pacote, ensure_ascii=False, indent=2), encoding="utf-8")
    serializar_csv(registros, csv_path)
    incorporado = incorporar_em_dados_app(pacote, dados_app)

    print(f"json={json_path}")
    print(f"csv={csv_path}")
    print(f"incorporado_em_dados={incorporado}")
    print(json.dumps({"qualidade": qualidade, "conciliacao": conciliacao}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
