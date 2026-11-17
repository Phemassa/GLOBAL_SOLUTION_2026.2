"""API REST do ZelaCidade (FastAPI). Documentação interativa em /docs.

    uvicorn zela.api:app --port 8000      (rodando de dentro de src/)

Rotas do cidadão são abertas; rotas do gestor pedem o cabeçalho X-Token
(variável ZELA_TOKEN; na demonstração, "zela-demo").
"""
import os
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from zela import db, nlp, referencia, rpa
from zela.categorias import CATEGORIAS

app = FastAPI(title="ZelaCidade API", version="1.0.0",
              description="Zeladoria urbana com IA: recebe pedidos do cidadão, classifica, agrupa, roteia e acompanha.")
TOKEN = os.environ.get("ZELA_TOKEN", "zela-demo")
WEB = Path(__file__).resolve().parents[1] / "web" / "dist"


def exigir_gestor(x_token: str = Header(default="")):
    if x_token != TOKEN:
        raise HTTPException(401, "Token de gestor inválido")


class NovoPedido(BaseModel):
    texto: str = Field(min_length=10, max_length=1000)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    email: str | None = Field(default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)
    consentimento: bool = False   # sem consentimento, o e-mail não é guardado


class Texto(BaseModel):
    texto: str = Field(min_length=3, max_length=1000)


class Atualizacao(BaseModel):
    status: str | None = None
    categoria: str | None = None
    nota: str | None = Field(default=None, max_length=500)


@app.post("/api/classificar")
def classificar(corpo: Texto):
    """Prévia enquanto o cidadão digita: nada é gravado."""
    resultado = nlp.classificar(corpo.texto)
    return {**resultado, "rotulo": referencia.rotulo(resultado["categoria"]),
            "prazo": referencia.prazo(resultado["categoria"]), "urgencia": nlp.urgencia(corpo.texto)["nivel"],
            "texto_anonimizado": nlp.anonimizar(corpo.texto)}


@app.post("/api/solicitacoes", status_code=201)
def criar(pedido: NovoPedido):
    email = pedido.email if pedido.consentimento else None
    return db.criar(pedido.texto, pedido.lat, pedido.lon, email)


@app.get("/api/solicitacoes/{protocolo}")
def consultar(protocolo: str):
    pedido = db.detalhar(protocolo.strip().upper())
    if not pedido:
        raise HTTPException(404, "Protocolo não encontrado")
    return pedido


@app.get("/api/solicitacoes", dependencies=[Depends(exigir_gestor)])
def listar(status: str | None = None, categoria: str | None = None):
    return db.listar(status, categoria)


@app.patch("/api/solicitacoes/{protocolo}", dependencies=[Depends(exigir_gestor)])
def atualizar(protocolo: str, mudanca: Atualizacao):
    if mudanca.status and mudanca.status not in db.STATUS_VALIDOS:
        raise HTTPException(422, f"Status inválido; use um de {db.STATUS_VALIDOS}")
    if mudanca.categoria and mudanca.categoria not in CATEGORIAS:
        raise HTTPException(422, "Categoria inválida")
    pedido = db.atualizar(protocolo, mudanca.status, mudanca.categoria, mudanca.nota)
    if not pedido:
        raise HTTPException(404, "Protocolo não encontrado")
    return pedido


@app.get("/api/indicadores")
def indicadores():
    return db.indicadores()


@app.post("/api/rpa/executar", dependencies=[Depends(exigir_gestor)])
def executar_rpa(avancar_dias: float = 0):
    """Roda um ciclo do robô. avancar_dias adianta o relógio, só para demonstrar prazos vencidos."""
    if avancar_dias:
        db.avancar_relogio(avancar_dias)
    return rpa.ciclo()


@app.get("/api/referencia")
def referencia_categorias():
    """Categorias com volume e prazos reais do SP156."""
    tabela = referencia.categorias().reset_index()
    return tabela.to_dict(orient="records")


@app.get("/api/mapa")
def mapa(categoria: str | None = None):
    pontos = pd.read_csv(referencia.PROCESSADO / "mapa_sp156.csv")
    if categoria:
        pontos = pontos[pontos["categoria"] == categoria]
    return pontos.fillna("").to_dict(orient="records")


# Interface React compilada, servida pela mesma porta (npm run build em src/web).
if WEB.exists():
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")

    @app.get("/{caminho:path}", include_in_schema=False)
    def interface(caminho: str):
        return FileResponse(WEB / "index.html")
