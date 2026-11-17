"""Baixa e processa os dados abertos reais do SP156 (Prefeitura de São Paulo, licença CC0).

    python -m zela.dados            # baixa (se faltar) e gera data/processed/

Os CSVs brutos (~100 MB cada) ficam fora do Git, em data/raw/. Só os agregados vão para
data/processed/, e as coordenadas são arredondadas para ~100 m antes de sair daqui:
o projeto não precisa do endereço exato para planejar a zeladoria (minimização, LGPD).
"""
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

from zela.categorias import CATEGORIAS, SERVICO_PARA_CATEGORIA

RAIZ = Path(__file__).resolve().parents[2]
BRUTO = RAIZ / "data" / "raw"
PROCESSADO = RAIZ / "data" / "processed"

BASE = "https://dados.prefeitura.sp.gov.br/dataset/0aecfa2b-aa3a-40d4-8183-0d4351b7fd0a/resource"
ARQUIVOS = {
    "sp156_2026_t2.csv": f"{BASE}/368eb32d-ef25-4441-be8f-fce0146575a1/download/arquivo-final-2-trim-26.csv",
    "sp156_2026_t3.csv": f"{BASE}/f67fcc12-8da4-485f-92a3-d2af40cc771e/download/arquivo-final-3-trim-26.csv",
}


def baixar():
    BRUTO.mkdir(parents=True, exist_ok=True)
    for nome, url in ARQUIVOS.items():
        destino = BRUTO / nome
        if destino.exists() and destino.stat().st_size > 1_000_000:
            continue
        for tentativa in range(5):
            try:
                print(f"Baixando {nome}...", flush=True)
                urllib.request.urlretrieve(url, destino)
                break
            except OSError as erro:
                print(f"  falhou ({erro}); nova tentativa", flush=True)
                time.sleep(10)
        else:
            raise SystemExit(f"Nao foi possivel baixar {url}")


MESES_DO_TRIMESTRE = {"2026_t2": {4, 5, 6}, "2026_t3": {7, 8, 9}}


def ler_trimestre(caminho: Path, trimestre: str) -> pd.DataFrame:
    """Lê um trimestre tratando as diferenças de formato entre os arquivos da fonte.

    Cada trimestre é publicado de um jeito: UTF-8 ou Windows-1252, separador "," ou ";",
    data mês/dia ou dia/mês. Uma data como 01/04 é válida nos dois formatos, então o
    formato é escolhido pelo que coloca as aberturas dentro do trimestre, e conferido.
    """
    bruto = caminho.read_bytes()[:4096]
    try:
        bruto.decode("utf-8")
        codificacao = "utf-8"
    except UnicodeDecodeError:
        codificacao = "cp1252"
    cabecalho = bruto.decode(codificacao, errors="ignore").splitlines()[0]
    separador = ";" if cabecalho.count(";") > cabecalho.count(",") else ","
    df = pd.read_csv(caminho, dtype=str, encoding=codificacao, sep=separador)

    meses = MESES_DO_TRIMESTRE[trimestre]
    melhor = None
    for formato in ("%m/%d/%Y", "%d/%m/%Y"):
        abertura = pd.to_datetime(df["Data de Abertura"], format=formato, errors="coerce")
        dentro = abertura.dt.month.isin(meses).mean()
        if melhor is None or dentro > melhor[1]:
            melhor = (formato, dentro)
    formato, dentro = melhor
    if dentro < 0.999:
        raise ValueError(f"{caminho.name}: só {dentro:.1%} das aberturas caem no trimestre; formato de data incerto")
    for coluna, nova in (("Data de Abertura", "abertura"), ("Data de Finalização", "finalizacao")):
        df[nova] = pd.to_datetime(df[coluna], format=formato, errors="coerce")
    for coluna, nova in (("Latitude", "lat"), ("Longitude", "lon")):
        df[nova] = pd.to_numeric(df[coluna].str.replace(",", ".", regex=False), errors="coerce")
    df["trimestre"] = trimestre
    print(f"{caminho.name}: {codificacao}, separador '{separador}', datas {formato}, {len(df)} linhas", flush=True)
    return df


def carregar(devolver_brutos=False):
    partes = [ler_trimestre(BRUTO / nome, nome.removeprefix("sp156_").removesuffix(".csv")) for nome in ARQUIVOS]
    df = pd.concat(partes, ignore_index=True)
    servico = df["Serviço"].str.strip()
    df = df[servico.isin(SERVICO_PARA_CATEGORIA)].copy()
    df["categoria"] = df["Serviço"].str.strip().map(SERVICO_PARA_CATEGORIA)
    df["dias"] = (df["finalizacao"] - df["abertura"]).dt.days
    return (df, partes) if devolver_brutos else df


def resumo_categorias(df: pd.DataFrame) -> pd.DataFrame:
    """Volume, prazos reais e órgão responsável mais frequente por categoria."""
    # Prazo medido só no 2º trimestre: o 3º ainda tem pedidos recentes sem tempo para fechar,
    # o que puxaria a mediana para baixo (os casos longos ainda estão abertos).
    t2 = df[df["trimestre"] == "2026_t2"]
    linhas = []
    for chave, cat in CATEGORIAS.items():
        todos = df[df["categoria"] == chave]
        fechados = t2[(t2["categoria"] == chave) & (t2["Status"] == "Finalizada") & (t2["dias"] >= 0)]
        orgao = todos["Órgão"].value_counts()
        linhas.append({
            "categoria": chave,
            "rotulo": cat["rotulo"],
            "servicos_sp156": len(cat["servicos"]),
            "pedidos_2_trimestres": len(todos),
            "pct_ainda_aberto_t2": round(100 * (t2[t2["categoria"] == chave]["Status"].isin(["Aberto", "Em Andamento"])).mean(), 1),
            "mediana_dias": float(fechados["dias"].median()),
            "p80_dias": float(fechados["dias"].quantile(0.8)),
            "orgao_mais_frequente": orgao.index[0],
            "pct_orgao_mais_frequente": round(100 * orgao.iloc[0] / len(todos), 1),
        })
    return pd.DataFrame(linhas).sort_values("pedidos_2_trimestres", ascending=False)


def tabela_roteamento(df: pd.DataFrame) -> pd.DataFrame:
    """Órgão que de fato atendeu cada categoria em cada subprefeitura (o mais frequente)."""
    base = df.dropna(subset=["Prefeitura Operacional"])
    contagem = base.groupby(["categoria", "Prefeitura Operacional", "Órgão"]).size().rename("n").reset_index()
    total = contagem.groupby(["categoria", "Prefeitura Operacional"])["n"].transform("sum")
    contagem["pct"] = (100 * contagem["n"] / total).round(1)
    melhor = contagem.sort_values("n", ascending=False).drop_duplicates(["categoria", "Prefeitura Operacional"])
    return melhor.rename(columns={"Prefeitura Operacional": "subprefeitura", "Órgão": "orgao", "n": "pedidos"}) \
        .sort_values(["categoria", "subprefeitura"])[["categoria", "subprefeitura", "orgao", "pedidos", "pct"]]


def pontos_mapa(df: pd.DataFrame, n_por_categoria=400, semente=42) -> pd.DataFrame:
    """Amostra para o mapa, com coordenadas arredondadas (3 casas ~ 100 m)."""
    geo = df.dropna(subset=["lat", "lon"])
    geo = geo[geo["lat"].between(-24.1, -23.3) & geo["lon"].between(-47.0, -46.3)]
    amostra = geo.groupby("categoria", group_keys=False).apply(
        lambda g: g.sample(min(len(g), n_por_categoria), random_state=semente), include_groups=False)
    amostra["categoria"] = geo.loc[amostra.index, "categoria"]
    return pd.DataFrame({
        "categoria": amostra["categoria"],
        "lat": amostra["lat"].round(3),
        "lon": amostra["lon"].round(3),
        "status": amostra["Status"],
        "subprefeitura": amostra["Prefeitura Operacional"],
    }).reset_index(drop=True)


NAO_SUBPREFEITURAS = {"Prefeitura Regional nao encontrada", "Departamento de Estradas de Rodagem",
                      "Superintendencia das Usinas de Asfalto"}


def grade_subprefeituras(trimestres: list[pd.DataFrame]) -> pd.DataFrame:
    """Subprefeitura predominante em cada célula de ~100 m, usando TODOS os pedidos geolocalizados
    (não só os de zeladoria). Serve para descobrir a subprefeitura de um ponto novo."""
    geo = pd.concat(trimestres, ignore_index=True).dropna(subset=["lat", "lon", "Prefeitura Operacional"])
    geo = geo[geo["lat"].between(-24.1, -23.3) & geo["lon"].between(-47.0, -46.3)]
    # A coluna traz alguns valores que não são subprefeituras (qualidade do dado de origem).
    geo = geo[~geo["Prefeitura Operacional"].isin(NAO_SUBPREFEITURAS)]
    geo = geo.assign(lat=geo["lat"].round(3), lon=geo["lon"].round(3))
    contagem = geo.groupby(["lat", "lon", "Prefeitura Operacional"]).size().rename("n").reset_index()
    grade = contagem.sort_values("n", ascending=False).drop_duplicates(["lat", "lon"])
    return grade.rename(columns={"Prefeitura Operacional": "subprefeitura"})[["lat", "lon", "subprefeitura", "n"]]


def duplicidade(df: pd.DataFrame, raio_casas=4) -> pd.DataFrame:
    """Pedidos repetidos: mesma categoria, mesmo ponto (~11 m) enquanto o anterior seguia aberto.

    É o trabalho que o agrupamento automático do ZelaCidade evitaria.
    """
    geo = df.dropna(subset=["lat", "lon", "abertura"]).copy()
    geo["ponto"] = geo["lat"].round(raio_casas).astype(str) + "," + geo["lon"].round(raio_casas).astype(str)
    geo["fim"] = geo["finalizacao"].fillna(pd.Timestamp.max)
    geo = geo.sort_values("abertura")
    linhas = []
    for chave, g in geo.groupby("categoria"):
        repetidos = 0
        for _, ponto in g.groupby("ponto"):
            if len(ponto) < 2:
                continue
            fim_aberto = ponto["fim"].cummax().shift()
            repetidos += int((ponto["abertura"] <= fim_aberto).sum())
        linhas.append({"categoria": chave, "pedidos_com_local": len(g), "repetidos_com_anterior_aberto": repetidos,
                       "pct_repetidos": round(100 * repetidos / len(g), 1)})
    return pd.DataFrame(linhas).sort_values("pct_repetidos", ascending=False)


def main():
    sys.stdout.reconfigure(encoding="utf8")
    baixar()
    df, brutos = carregar(devolver_brutos=True)
    PROCESSADO.mkdir(parents=True, exist_ok=True)
    saidas = {
        "grade_subprefeituras.csv": grade_subprefeituras(brutos),
        "categorias_sp156.csv": resumo_categorias(df),
        "roteamento_sp156.csv": tabela_roteamento(df),
        "mapa_sp156.csv": pontos_mapa(df),
        "duplicidade_sp156.csv": duplicidade(df),
    }
    for nome, tabela in saidas.items():
        tabela.to_csv(PROCESSADO / nome, index=False, encoding="utf-8")
        print(f"{nome}: {len(tabela)} linhas")
    print(f"Pedidos de zeladoria nos 2 trimestres: {len(df)}")
    print(saidas["categorias_sp156.csv"].to_string(index=False))
    print(saidas["duplicidade_sp156.csv"].to_string(index=False))


if __name__ == "__main__":
    main()
