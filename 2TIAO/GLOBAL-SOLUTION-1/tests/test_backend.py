"""Testes do backend: anonimização, classificação, agrupamento, roteamento real, API e RPA."""
import email
import importlib
import sys
from email import policy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Pontos sem ambiguidade de divisa: Praça da Sé e Largo da Batata (Pinheiros).
PRACA_DA_SE = (-23.5503, -46.6339)
LARGO_DA_BATATA = (-23.5672, -46.6936)


@pytest.fixture
def app(tmp_path, monkeypatch):
    """API com banco e caixa de saída isolados em uma pasta temporária."""
    monkeypatch.setenv("ZELA_BANCO", str(tmp_path / "teste.db"))
    monkeypatch.setenv("ZELA_SAIDA", str(tmp_path / "saida"))
    monkeypatch.delenv("SMTP_HOST", raising=False)
    from zela import db, rpa, api
    importlib.reload(db)
    importlib.reload(rpa)
    importlib.reload(api)
    from fastapi.testclient import TestClient
    return TestClient(api.app), tmp_path


GESTOR = {"X-Token": "zela-demo"}


def test_anonimizacao():
    from zela import nlp
    texto = "ligue (11) 98765-4321 ou 11 91234-5678, cpf 123.456.789-09, ana@x.com.br, cep 05409011"
    assert nlp.anonimizar(texto) == "ligue [TELEFONE] ou [TELEFONE], cpf [CPF], [EMAIL], cep 05409011"


@pytest.mark.parametrize("texto,categoria", [
    ("tem um buraco enorme na rua e o asfalto afundou", "buraco"),
    ("jogaram entulho de obra na calçada", "entulho"),
    ("o bar toca som alto de madrugada", "barulho"),
    ("a boca de lobo está entupida e a rua alaga", "drenagem"),
])
def test_classificacao_casos_claros(texto, categoria):
    from zela import nlp
    resultado = nlp.classificar(texto)
    assert resultado["categoria"] == categoria
    assert not resultado["triagem_humana"]


def test_urgencia_por_regras_explicitas():
    from zela import nlp
    assert nlp.urgencia("fio caído perto da creche, risco de choque")["nivel"] == "alta"
    assert nlp.urgencia("a rua está suja")["nivel"] == "normal"


def test_roteamento_usa_dados_reais():
    from zela import referencia
    sub = referencia.subprefeitura(*PRACA_DA_SE)
    assert sub == "SE"
    assert referencia.subprefeitura(*LARGO_DA_BATATA) == "PINHEIROS"
    assert referencia.orgao("buraco", sub)
    assert referencia.subprefeitura(-22.9, -43.2) is None  # Rio de Janeiro: fora de SP


def test_fluxo_completo_cidadao_gestor_rpa(app):
    cliente, pasta = app
    novo = cliente.post("/api/solicitacoes", json={
        "texto": "tem um buraco enorme no meio da rua, me liga (11) 98765-4321",
        "lat": PRACA_DA_SE[0], "lon": PRACA_DA_SE[1], "email": "maria@example.com", "consentimento": True}).json()
    protocolo = novo["protocolo"]
    assert novo["categoria"] == "buraco" and novo["status"] == "Recebido"
    assert "[TELEFONE]" in novo["texto"] and "98765" not in novo["texto"]  # só o texto anonimizado é gravado
    assert novo["contato"] == "m***@example.com"
    assert novo["subprefeitura"] == "SE"

    # Outro cidadão relata o mesmo buraco a ~10 m: vira apoio, não um pedido novo.
    repetido = cliente.post("/api/solicitacoes", json={
        "texto": "buraco grande no asfalto aqui na rua", "lat": PRACA_DA_SE[0] + 0.00009, "lon": PRACA_DA_SE[1]}).json()
    assert repetido["agrupado"] and repetido["protocolo"] == protocolo and repetido["apoios"] == 2
    # Longe (> 30 m), é outro pedido.
    longe = cliente.post("/api/solicitacoes", json={
        "texto": "buraco grande no asfalto aqui na rua", "lat": PRACA_DA_SE[0] + 0.001, "lon": PRACA_DA_SE[1]}).json()
    assert longe["protocolo"] != protocolo

    # O robô encaminha ao órgão e avisa o cidadão.
    resumo = cliente.post("/api/rpa/executar", headers=GESTOR).json()
    assert resumo["encaminhados"] == 2 and resumo["avisos_cidadao"] == 1
    oficios = list((pasta / "saida").glob("*.eml"))
    assuntos = [email.message_from_bytes(o.read_bytes(), policy=policy.default)["Subject"] for o in oficios]
    assert any(f"Ofício {protocolo}" in a for a in assuntos)
    assert cliente.get(f"/api/solicitacoes/{protocolo}").json()["status"] == "Encaminhado"

    # Rodar de novo não duplica ofício nem aviso.
    assert cliente.post("/api/rpa/executar", headers=GESTOR).json() == {
        "encaminhados": 0, "escalados": 0, "avisos_cidadao": 0, "contatos_apagados": 0}

    # Prazo de referência vencido: o robô escala.
    p80 = novo["prazo_p80"]
    escalado = cliente.post(f"/api/rpa/executar?avancar_dias={p80 + 1}", headers=GESTOR).json()
    assert escalado["escalados"] == 2

    # Gestor finaliza; o robô avisa e apaga o e-mail (retenção mínima).
    cliente.patch(f"/api/solicitacoes/{protocolo}", headers=GESTOR, json={"status": "Finalizado", "nota": "Buraco tapado"})
    final = cliente.post("/api/rpa/executar", headers=GESTOR).json()
    assert final["avisos_cidadao"] == 1 and final["contatos_apagados"] == 1
    assert cliente.get(f"/api/solicitacoes/{protocolo}").json()["contato"] is None

    kpi = cliente.get("/api/indicadores").json()
    assert kpi["pedidos"] == 2 and kpi["relatos_agrupados"] == 1 and kpi["escalados_por_prazo"] == 2
    assert kpi["pct_no_prazo"] == 0.0


def test_triagem_humana_e_correcao(app):
    cliente, _ = app
    duvida = cliente.post("/api/solicitacoes", json={"texto": "preciso de ajuda com um problema aqui perto de casa"}).json()
    assert duvida["status"] == "Triagem humana"
    # Fica fora do encaminhamento automático até um atendente confirmar.
    assert cliente.post("/api/rpa/executar", headers=GESTOR).json()["encaminhados"] == 0
    corrigido = cliente.patch(f"/api/solicitacoes/{duvida['protocolo']}", headers=GESTOR, json={"categoria": "drenagem"}).json()
    assert corrigido["categoria"] == "drenagem" and corrigido["status"] == "Recebido" and corrigido["categoria_corrigida"] == 1
    assert cliente.get("/api/indicadores").json()["categorias_corrigidas_por_humano"] == 1


def test_seguranca_e_validacao(app):
    cliente, _ = app
    assert cliente.get("/api/solicitacoes").status_code == 401
    assert cliente.get("/api/solicitacoes", headers={"X-Token": "errado"}).status_code == 401
    assert cliente.post("/api/solicitacoes", json={"texto": "curto"}).status_code == 422
    assert cliente.post("/api/solicitacoes", json={"texto": "buraco grande na rua", "lat": 999}).status_code == 422
    assert cliente.get("/api/solicitacoes/ZC-NAO-EXISTE").status_code == 404
    # Sem consentimento, o e-mail não é guardado.
    sem = cliente.post("/api/solicitacoes", json={"texto": "buraco grande no asfalto da rua", "email": "x@example.com"}).json()
    assert sem["contato"] is None
    pedido = sem["protocolo"]
    assert cliente.patch(f"/api/solicitacoes/{pedido}", headers=GESTOR, json={"status": "Voando"}).status_code == 422
