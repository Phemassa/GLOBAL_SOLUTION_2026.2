"""Persistência em SQLite e as regras de negócio dos pedidos (criação, agrupamento, status)."""
import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from zela import nlp, referencia

CAMINHO_BANCO = Path(os.environ.get("ZELA_BANCO", Path(__file__).resolve().parents[2] / "data" / "runtime" / "zela.db"))
RAIO_AGRUPAMENTO_M = 30
STATUS_ABERTOS = ("Recebido", "Triagem humana", "Encaminhado", "Em atendimento")
STATUS_VALIDOS = STATUS_ABERTOS + ("Finalizado", "Cancelado")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS solicitacoes (
    protocolo TEXT PRIMARY KEY, criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL,
    texto TEXT NOT NULL,                -- só a versão anonimizada é gravada
    categoria TEXT NOT NULL, confianca REAL NOT NULL, categoria_corrigida INTEGER DEFAULT 0,
    urgencia TEXT NOT NULL, pontos_urgencia INTEGER NOT NULL,
    lat REAL, lon REAL, subprefeitura TEXT, orgao TEXT NOT NULL,
    status TEXT NOT NULL, apoios INTEGER DEFAULT 1,
    prazo_mediana REAL, prazo_p80 REAL,
    encaminhado_em TEXT, finalizado_em TEXT, escalado_em TEXT
);
CREATE TABLE IF NOT EXISTS contatos (     -- separado do pedido e apagado ao final (LGPD)
    protocolo TEXT PRIMARY KEY, email TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT, protocolo TEXT NOT NULL, quando TEXT NOT NULL,
    evento TEXT NOT NULL, detalhe TEXT
);
"""

_relogio_offset = timedelta(0)


def agora() -> datetime:
    """Relógio do sistema; o deslocamento existe para demonstrar prazos sem esperar dias."""
    return datetime.now(timezone.utc) + _relogio_offset


def avancar_relogio(dias: float):
    global _relogio_offset
    _relogio_offset += timedelta(days=dias)


@contextmanager
def conexao():
    CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(CAMINHO_BANCO)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(ESQUEMA)
        yield con
        con.commit()
    finally:
        con.close()


def _registrar(con, protocolo, evento, detalhe=""):
    con.execute("INSERT INTO historico (protocolo, quando, evento, detalhe) VALUES (?, ?, ?, ?)",
                (protocolo, agora().isoformat(), evento, detalhe))


def _novo_protocolo() -> str:
    return f"ZC-{agora():%Y%m%d}-{secrets.token_hex(3).upper()}"


def mascarar_email(email: str) -> str:
    nome, _, dominio = email.partition("@")
    return f"{nome[:1]}***@{dominio}"


def criar(texto: str, lat: float | None, lon: float | None, email: str | None = None) -> dict:
    """Classifica, anonimiza, agrupa com pedido igual aberto por perto, ou cria um novo."""
    texto_anon = nlp.anonimizar(texto.strip())
    classe = nlp.classificar(texto_anon)
    categoria = classe["categoria"]
    urg = nlp.urgencia(texto_anon)

    with conexao() as con:
        # Mesmo problema, mesmo lugar, ainda aberto: soma um apoio em vez de abrir outro pedido.
        if lat is not None and lon is not None and not classe["triagem_humana"]:
            candidatos = con.execute(
                f"SELECT * FROM solicitacoes WHERE categoria = ? AND status IN ({','.join('?' * len(STATUS_ABERTOS))}) AND lat IS NOT NULL",
                (categoria, *STATUS_ABERTOS)).fetchall()
            for c in candidatos:
                if referencia.distancia_m(lat, lon, c["lat"], c["lon"]) <= RAIO_AGRUPAMENTO_M:
                    con.execute("UPDATE solicitacoes SET apoios = apoios + 1, atualizado_em = ? WHERE protocolo = ?",
                                (agora().isoformat(), c["protocolo"]))
                    _registrar(con, c["protocolo"], "Novo apoio", "Outro cidadão relatou o mesmo problema no local")
                    if email:
                        con.execute("INSERT OR IGNORE INTO contatos VALUES (?, ?)", (c["protocolo"], email))
                    return {**detalhar(c["protocolo"], con), "agrupado": True}

        subpref = referencia.subprefeitura(lat, lon) if lat is not None else None
        prazo = referencia.prazo(categoria)
        protocolo = _novo_protocolo()
        status = "Triagem humana" if classe["triagem_humana"] else "Recebido"
        momento = agora().isoformat()
        con.execute(
            """INSERT INTO solicitacoes (protocolo, criado_em, atualizado_em, texto, categoria, confianca, urgencia,
               pontos_urgencia, lat, lon, subprefeitura, orgao, status, prazo_mediana, prazo_p80)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (protocolo, momento, momento, texto_anon, categoria, classe["confianca"], urg["nivel"], urg["pontos"],
             lat, lon, subpref, referencia.orgao(categoria, subpref), status, prazo["mediana_dias"], prazo["p80_dias"]))
        if email:
            con.execute("INSERT INTO contatos VALUES (?, ?)", (protocolo, email))
        _registrar(con, protocolo, "Pedido recebido",
                   f"Categoria {referencia.rotulo(categoria)} ({classe['confianca']:.0%} de confiança)")
        if classe["triagem_humana"]:
            _registrar(con, protocolo, "Triagem humana", "Confiança baixa: um atendente vai confirmar a categoria")
        return {**detalhar(protocolo, con), "agrupado": False, "alternativas": classe["alternativas"]}


def detalhar(protocolo: str, con=None) -> dict | None:
    if con is None:
        with conexao() as nova:
            return detalhar(protocolo, nova)
    linha = con.execute("SELECT * FROM solicitacoes WHERE protocolo = ?", (protocolo,)).fetchone()
    if not linha:
        return None
    contato = con.execute("SELECT email FROM contatos WHERE protocolo = ?", (protocolo,)).fetchone()
    historico = con.execute("SELECT quando, evento, detalhe FROM historico WHERE protocolo = ? ORDER BY id", (protocolo,)).fetchall()
    return {**dict(linha), "rotulo": referencia.rotulo(linha["categoria"]),
            "contato": mascarar_email(contato["email"]) if contato else None,
            "historico": [dict(h) for h in historico]}


def listar(status: str | None = None, categoria: str | None = None) -> list[dict]:
    filtros, valores = [], []
    if status:
        filtros.append("status = ?"); valores.append(status)
    if categoria:
        filtros.append("categoria = ?"); valores.append(categoria)
    onde = f"WHERE {' AND '.join(filtros)}" if filtros else ""
    with conexao() as con:
        linhas = con.execute(f"SELECT * FROM solicitacoes {onde} ORDER BY pontos_urgencia DESC, apoios DESC, criado_em", valores).fetchall()
    return [{**dict(l), "rotulo": referencia.rotulo(l["categoria"])} for l in linhas]


def atualizar(protocolo: str, status: str | None = None, categoria: str | None = None, nota: str | None = None) -> dict | None:
    with conexao() as con:
        atual = con.execute("SELECT * FROM solicitacoes WHERE protocolo = ?", (protocolo,)).fetchone()
        if not atual:
            return None
        momento = agora().isoformat()
        if categoria and categoria != atual["categoria"]:
            prazo = referencia.prazo(categoria)
            con.execute("""UPDATE solicitacoes SET categoria = ?, categoria_corrigida = 1, orgao = ?, prazo_mediana = ?,
                           prazo_p80 = ?, atualizado_em = ? WHERE protocolo = ?""",
                        (categoria, referencia.orgao(categoria, atual["subprefeitura"]), prazo["mediana_dias"],
                         prazo["p80_dias"], momento, protocolo))
            _registrar(con, protocolo, "Categoria corrigida", f"{referencia.rotulo(atual['categoria'])} → {referencia.rotulo(categoria)}")
            if atual["status"] == "Triagem humana" and not status:
                status = "Recebido"
        if status and status != atual["status"]:
            extra = ", finalizado_em = ?" if status == "Finalizado" else ""
            valores = [status, momento] + ([momento] if extra else []) + [protocolo]
            con.execute(f"UPDATE solicitacoes SET status = ?, atualizado_em = ?{extra} WHERE protocolo = ?", valores)
            _registrar(con, protocolo, f"Status: {status}", nota or "")
        elif nota:
            _registrar(con, protocolo, "Nota do atendimento", nota)
        return detalhar(protocolo, con)


def indicadores() -> dict:
    """Indicadores de impacto acompanhados pelo painel (ver ODS no relatório)."""
    with conexao() as con:
        total = con.execute("SELECT COUNT(*), COALESCE(SUM(apoios), 0) FROM solicitacoes").fetchone()
        por_status = dict(con.execute("SELECT status, COUNT(*) FROM solicitacoes GROUP BY status").fetchall())
        por_categoria = [dict(r) for r in con.execute(
            "SELECT categoria, COUNT(*) AS pedidos, SUM(apoios) AS relatos FROM solicitacoes GROUP BY categoria ORDER BY pedidos DESC")]
        fechados = con.execute("SELECT criado_em, finalizado_em, prazo_p80 FROM solicitacoes WHERE finalizado_em IS NOT NULL").fetchall()
        corrigidas = con.execute("SELECT COUNT(*) FROM solicitacoes WHERE categoria_corrigida = 1").fetchone()[0]
        escalados = con.execute("SELECT COUNT(*) FROM solicitacoes WHERE escalado_em IS NOT NULL").fetchone()[0]
    dias = [(datetime.fromisoformat(f["finalizado_em"]) - datetime.fromisoformat(f["criado_em"])).total_seconds() / 86400 for f in fechados]
    no_prazo = sum(1 for d, f in zip(dias, fechados) if d <= f["prazo_p80"])
    pedidos, relatos = total[0], total[1]
    for c in por_categoria:
        c["rotulo"] = referencia.rotulo(c["categoria"])
    return {
        "pedidos": pedidos,
        "relatos_recebidos": relatos,
        "relatos_agrupados": relatos - pedidos,       # retrabalho evitado
        "por_status": por_status,
        "por_categoria": por_categoria,
        "tempo_medio_dias": round(sum(dias) / len(dias), 2) if dias else None,
        "pct_no_prazo": round(100 * no_prazo / len(dias), 1) if dias else None,
        "categorias_corrigidas_por_humano": corrigidas,
        "escalados_por_prazo": escalados,
    }


def contato_hash(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()[:12]
