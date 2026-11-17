"""Robô (RPA) que faz o trabalho repetitivo de acompanhamento dos pedidos.

A cada ciclo:
  1. encaminha pedidos novos ao órgão responsável, gerando o ofício por e-mail;
  2. escala pedidos que passaram do prazo real (p80 do SP156) para a coordenação;
  3. avisa o cidadão de cada mudança de status;
  4. apaga o e-mail do cidadão quando o pedido termina (LGPD: guardar só enquanto precisa).

Sem SMTP configurado (variável SMTP_HOST), os e-mails viram arquivos .eml em data/runtime/saida/.

    python -m zela.rpa                 # um ciclo
    python -m zela.rpa --intervalo 30  # ciclo a cada 30 s
"""
import argparse
import os
import smtplib
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from zela import db, referencia

PASTA_SAIDA = Path(os.environ.get("ZELA_SAIDA", Path(__file__).resolve().parents[2] / "data" / "runtime" / "saida"))
REMETENTE = "zelacidade@example.com"


def _caixa_do_orgao(orgao: str) -> str:
    """Endereço fictício do órgão (os reais não são públicos na base)."""
    return "".join(c for c in orgao.lower() if c.isalnum()) + "@orgaos.example.com"


def enviar(para: str, assunto: str, corpo: str) -> str:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = REMETENTE, para, assunto
    msg.set_content(corpo)
    if os.environ.get("SMTP_HOST"):
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "25")), timeout=10) as smtp:
            smtp.send_message(msg)
        return f"smtp:{para}"
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_SAIDA / f"{time.time_ns()}.eml"
    caminho.write_bytes(bytes(msg))
    return str(caminho)


def ciclo() -> dict:
    resumo = {"encaminhados": 0, "escalados": 0, "avisos_cidadao": 0, "contatos_apagados": 0}
    agora = db.agora()
    with db.conexao() as con:
        # 1. Encaminhamento ao órgão
        for p in con.execute("SELECT * FROM solicitacoes WHERE status = 'Recebido'").fetchall():
            corpo = (f"Protocolo {p['protocolo']} - {referencia.rotulo(p['categoria'])}\n"
                     f"Subprefeitura: {p['subprefeitura'] or 'não identificada'}\n"
                     f"Local aproximado: {p['lat']}, {p['lon']}\n"
                     f"Urgência: {p['urgencia']} | Relatos do mesmo problema: {p['apoios']}\n"
                     f"Prazo de referência (p80 real do SP156): {p['prazo_p80']:.0f} dias\n\n"
                     f"Relato (anonimizado): {p['texto']}\n")
            enviar(_caixa_do_orgao(p["orgao"]), f"[ZelaCidade] Ofício {p['protocolo']} - {referencia.rotulo(p['categoria'])}", corpo)
            con.execute("UPDATE solicitacoes SET status = 'Encaminhado', encaminhado_em = ?, atualizado_em = ? WHERE protocolo = ?",
                        (agora.isoformat(), agora.isoformat(), p["protocolo"]))
            db._registrar(con, p["protocolo"], "Status: Encaminhado", f"Ofício enviado a {p['orgao']}")
            resumo["encaminhados"] += 1

        # 2. Escalonamento por prazo vencido
        for p in con.execute("""SELECT * FROM solicitacoes WHERE status IN ('Encaminhado', 'Em atendimento')
                                AND escalado_em IS NULL AND encaminhado_em IS NOT NULL""").fetchall():
            limite = datetime.fromisoformat(p["encaminhado_em"]) + timedelta(days=p["prazo_p80"])
            if agora > limite:
                enviar(f"coordenacao.{(p['subprefeitura'] or 'geral').lower().replace(' ', '')}@orgaos.example.com",
                       f"[ZelaCidade] Prazo vencido {p['protocolo']}",
                       f"O pedido {p['protocolo']} ({referencia.rotulo(p['categoria'])}) passou do prazo de referência "
                       f"de {p['prazo_p80']:.0f} dias sem conclusão. Órgão: {p['orgao']}. Relatos: {p['apoios']}.")
                con.execute("UPDATE solicitacoes SET escalado_em = ?, pontos_urgencia = pontos_urgencia + 2 WHERE protocolo = ?",
                            (agora.isoformat(), p["protocolo"]))
                db._registrar(con, p["protocolo"], "Escalado", "Prazo de referência vencido: coordenação avisada e prioridade elevada")
                resumo["escalados"] += 1

        # 3. Aviso ao cidadão sobre mudanças ainda não comunicadas
        pendentes = con.execute("""SELECT h.id, h.protocolo, h.evento, h.detalhe, c.email FROM historico h
                                   JOIN contatos c ON c.protocolo = h.protocolo
                                   WHERE h.evento LIKE 'Status:%' AND h.id NOT IN
                                   (SELECT CAST(detalhe AS INTEGER) FROM historico WHERE evento = 'Cidadão avisado')""").fetchall()
        for h in pendentes:
            enviar(h["email"], f"[ZelaCidade] Atualização do protocolo {h['protocolo']}",
                   f"Seu pedido {h['protocolo']} mudou: {h['evento'].removeprefix('Status: ')}. {h['detalhe'] or ''}\n"
                   "Acompanhe pelo número do protocolo no ZelaCidade.")
            db._registrar(con, h["protocolo"], "Cidadão avisado", str(h["id"]))
            resumo["avisos_cidadao"] += 1

        # 4. Retenção mínima: pedido encerrado e cidadão avisado -> apaga o e-mail
        apagados = con.execute("""DELETE FROM contatos WHERE protocolo IN
                                  (SELECT protocolo FROM solicitacoes WHERE status IN ('Finalizado', 'Cancelado'))""").rowcount
        resumo["contatos_apagados"] = apagados
    return resumo


def main():
    args = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    args.add_argument("--intervalo", type=float, help="segundos entre ciclos; sem ele, roda um ciclo só")
    args = args.parse_args()
    while True:
        print(f"[RPA] {db.agora():%Y-%m-%d %H:%M:%S} {ciclo()}", flush=True)
        if not args.intervalo:
            break
        time.sleep(args.intervalo)


if __name__ == "__main__":
    main()
