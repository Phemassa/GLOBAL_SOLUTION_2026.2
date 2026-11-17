"""Gera o PDF de entrega a partir de docs/relatorio_gs.md.

    python -m demo.gerar_pdf --turma "2TIAOx" --video "https://youtu.be/..."

Sem --turma ou --video, o PDF sai com um aviso destacado no lugar, para não ser entregue incompleto.
"""
import argparse
import os
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
FONTE = RAIZ / "docs" / "relatorio_gs.md"
SAIDA = RAIZ / "docs" / "GS_2026-2_GrupoZion_ZelaCidade.pdf"
PENDENTE = '<span class="pendente">PREENCHER ANTES DE ENTREGAR</span>'

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1e293b; }
h1 { font-size: 30pt; color: #0f766e; margin: 10px 0 4px; }
h2 { font-size: 16pt; color: #0f766e; border-bottom: 2px solid #0f766e; padding-bottom: 3px; margin-top: 22px; page-break-after: avoid; }
h3 { font-size: 12.5pt; margin: 16px 0 6px; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 9.2pt; page-break-inside: avoid; }
th, td { border: 1px solid #cbd5e1; padding: 4px 6px; vertical-align: top; text-align: left; }
th { background: #f1f5f9; }
pre { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px; padding: 8px; font-size: 8.4pt; white-space: pre-wrap; page-break-inside: avoid; }
code { font-family: Consolas, "Courier New", monospace; }
p code, li code, td code { background: #f1f5f9; padding: 0 3px; }
.figura { width: 100%; border: 1px solid #cbd5e1; margin-top: 6px; page-break-inside: avoid; }
.figura-media { width: 70%; display: block; margin: 6px auto 0; border: 1px solid #cbd5e1; }
.figura-alta { width: 66%; display: block; margin: 6px auto 0; border: 1px solid #cbd5e1; }
.legenda { font-size: 8.8pt; color: #475569; margin: 3px 0 14px; text-align: center; }
.capa { page-break-after: always; padding-top: 30px; }
.logo-capa { width: 38%; }
.sobre { color: #475569; font-size: 11pt; margin-top: 30px; }
.subtitulo { font-size: 13pt; color: #334155; margin-bottom: 28px; }
.capa table { width: 70%; font-size: 10.5pt; }
.pendente { background: #fde68a; color: #92400e; font-weight: 700; padding: 1px 6px; }
"""


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--turma", default=os.environ.get("GS_TURMA"))
    args.add_argument("--video", default=os.environ.get("GS_VIDEO"))
    args = args.parse_args()

    texto = FONTE.read_text(encoding="utf-8")
    texto = texto.replace("{{TURMA}}", args.turma or PENDENTE).replace("{{VIDEO}}", args.video or PENDENTE)
    corpo = markdown.markdown(texto, extensions=["tables", "fenced_code", "md_in_html"])
    html = f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{corpo}</body></html>'
    temporario = FONTE.with_name("_relatorio.html")
    temporario.write_text(html, encoding="utf-8")
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch(channel=os.environ.get("CANAL", "msedge"), headless=True)
            pagina = navegador.new_page()
            pagina.goto(temporario.as_uri(), wait_until="networkidle")
            pagina.pdf(path=SAIDA, format="A4", print_background=True, display_header_footer=True,
                       header_template="<span></span>",
                       footer_template='<div style="font-size:8pt;color:#64748b;width:100%;text-align:center;">'
                                       'ZelaCidade · Grupo Zion · Global Solution 2026.2 · <span class="pageNumber"></span>/<span class="totalPages"></span></div>',
                       margin={"top": "16mm", "bottom": "16mm", "left": "15mm", "right": "15mm"})
            navegador.close()
    finally:
        temporario.unlink(missing_ok=True)
    pendencias = [n for n, v in (("turma", args.turma), ("vídeo", args.video)) if not v]
    print(f"PDF gerado: {SAIDA}" + (f" (PENDENTE: {', '.join(pendencias)})" if pendencias else ""))


if __name__ == "__main__":
    main()
