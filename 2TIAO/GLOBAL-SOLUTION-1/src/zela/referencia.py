"""Conhecimento tirado dos dados reais do SP156: prazos, órgão responsável e subprefeitura."""
import math
from functools import lru_cache
from pathlib import Path

import pandas as pd

from zela.categorias import CATEGORIAS

PROCESSADO = Path(__file__).resolve().parents[2] / "data" / "processed"


@lru_cache
def categorias() -> pd.DataFrame:
    return pd.read_csv(PROCESSADO / "categorias_sp156.csv").set_index("categoria")


@lru_cache
def _roteamento() -> dict:
    tabela = pd.read_csv(PROCESSADO / "roteamento_sp156.csv")
    return {(r.categoria, r.subprefeitura): r.orgao for r in tabela.itertuples()}


@lru_cache
def _grade():
    grade = pd.read_csv(PROCESSADO / "grade_subprefeituras.csv")
    return grade["lat"].to_numpy(), grade["lon"].to_numpy(), grade["subprefeitura"].to_numpy()


def distancia_m(lat1, lon1, lat2, lon2) -> float:
    """Haversine em metros."""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def subprefeitura(lat: float, lon: float) -> str | None:
    """Subprefeitura da célula de ~100 m mais próxima na grade montada com os pedidos reais do SP156."""
    if lat is None or lon is None:
        return None
    lats, lons, subs = _grade()
    i = int(((lats - lat) ** 2 + ((lons - lon) * 0.917) ** 2).argmin())  # 0,917 = cos(23,5°)
    # Longe de qualquer pedido real (> 1 km): provavelmente fora da cidade de São Paulo.
    return subs[i] if distancia_m(lat, lon, lats[i], lons[i]) < 1000 else None


def orgao(categoria: str, subpref: str | None) -> str:
    """Órgão que de fato atendeu essa categoria nessa subprefeitura no SP156."""
    return _roteamento().get((categoria, subpref)) or categorias().loc[categoria, "orgao_mais_frequente"]


def prazo(categoria: str) -> dict:
    linha = categorias().loc[categoria]
    return {"mediana_dias": float(linha["mediana_dias"]), "p80_dias": float(linha["p80_dias"])}


def rotulo(categoria: str) -> str:
    return CATEGORIAS[categoria]["rotulo"]
