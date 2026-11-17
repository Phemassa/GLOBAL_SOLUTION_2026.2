"""Teste ponta a ponta da interface, num navegador real, gerando as evidências em docs/evidencias.

Sobe a API (com a interface React compilada) num banco temporário, faz o papel do cidadão e
do gestor, e confere cada passo na tela. Falha em vez de salvar um print enganoso.

    cd src && python -m demo.e2e_interface           (requer: npm run build em src/web)
"""
import csv
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
EVIDENCIAS = RAIZ / "docs" / "evidencias"
PORTA = 8765
URL = f"http://127.0.0.1:{PORTA}"


def subir_servidor(pasta: Path):
    ambiente = {**os.environ, "ZELA_BANCO": str(pasta / "demo.db"), "ZELA_SAIDA": str(pasta / "saida")}
    processo = subprocess.Popen([sys.executable, "-m", "uvicorn", "zela.api:app", "--port", str(PORTA)],
                                cwd=RAIZ / "src", env=ambiente, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(f"{URL}/api/indicadores", timeout=1)
            return processo
        except OSError:
            time.sleep(0.5)
    processo.kill()
    raise SystemExit("API não subiu")


def popular_demonstracao():
    """Pedidos de demonstração: textos do conjunto de teste sintético em locais de pedidos reais."""
    rng = random.Random(3)
    with open(RAIZ / "data" / "sintetico" / "mensagens_teste.csv", encoding="utf-8") as f:
        textos = list(csv.DictReader(f))
    with open(RAIZ / "data" / "processed" / "mapa_sp156.csv", encoding="utf-8") as f:
        locais = [l for l in csv.DictReader(f) if l["subprefeitura"]]
    for linha in rng.sample(textos, 14):
        local = rng.choice([l for l in locais if l["categoria"] == linha["categoria"]])
        corpo = f'{{"texto": {repr(linha["texto"])!s}, "lat": {local["lat"]}, "lon": {local["lon"]}}}'.replace("'", '"')
        pedido = urllib.request.Request(f"{URL}/api/solicitacoes", data=corpo.encode(), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(pedido, timeout=10)


def main():
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as pasta:
        servidor = subir_servidor(Path(pasta))
        try:
            with sync_playwright() as p:
                navegador = p.chromium.launch(channel=os.environ.get("CANAL", "msedge"), headless=True)
                pg = navegador.new_page(viewport={"width": 1366, "height": 900}, locale="pt-BR")
                pg.goto(URL)

                # 1. Cidadão descreve o problema; a prévia mostra categoria e anonimização.
                texto = "Tem um buraco enorme na frente da escola, os carros desviam pela contramão. Me liga (11) 98765-4321"
                pg.get_by_test_id("texto").fill(texto)
                previa = pg.get_by_test_id("previa")
                expect(previa).to_contain_text("Buraco ou asfalto danificado", timeout=10000)
                expect(previa).to_contain_text("[TELEFONE]")
                caixa = pg.get_by_test_id("mapa-pedido").bounding_box()
                centro = (caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2)
                pg.mouse.click(*centro)
                expect(pg.get_by_test_id("local")).to_be_visible()
                pg.get_by_label("E-mail para receber atualizações (opcional)").fill("maria@example.com")
                pg.get_by_text("Autorizo o uso do e-mail").click()
                pg.wait_for_timeout(1500)  # azulejos do mapa
                pg.screenshot(path=EVIDENCIAS / "01_cidadao_preenche.png")
                print("OK prévia: categoria e anonimização", flush=True)

                pg.get_by_test_id("enviar").click()
                resultado = pg.get_by_test_id("resultado-pedido")
                expect(resultado).to_contain_text("Pedido registrado")
                expect(resultado).to_contain_text("SE")  # centro do mapa = Praça da Sé
                protocolo = pg.get_by_test_id("protocolo").inner_text()
                pg.screenshot(path=EVIDENCIAS / "02_protocolo_gerado.png")
                print(f"OK pedido criado: {protocolo}", flush=True)

                # 2. Outro cidadão relata o mesmo problema no mesmo lugar: vira apoio.
                pg.get_by_text("Fazer outro pedido").click()
                pg.get_by_test_id("texto").fill("o asfalto afundou aqui na rua da escola, cratera perigosa")
                expect(pg.get_by_test_id("previa")).to_contain_text("Buraco")
                pg.mouse.click(*centro)
                pg.get_by_test_id("enviar").click()
                expect(pg.get_by_test_id("resultado-pedido")).to_contain_text("já foi relatado aqui")
                expect(pg.get_by_test_id("protocolo")).to_have_text(protocolo)
                pg.screenshot(path=EVIDENCIAS / "03_pedido_agrupado.png")
                print("OK relato repetido agrupado no mesmo protocolo", flush=True)

                # 3. Texto vago vai para triagem humana.
                pg.get_by_text("Fazer outro pedido").click()
                pg.get_by_test_id("texto").fill("preciso de ajuda com uma situação aqui perto de casa")
                pg.get_by_test_id("enviar").click()
                expect(pg.get_by_test_id("resultado-pedido")).to_contain_text("um atendente vai conferir")
                print("OK texto vago foi para triagem humana", flush=True)

                popular_demonstracao()

                # 4. Painel do gestor: fila, robô, correção de categoria, prazo vencido.
                pg.get_by_test_id("aba-painel").click()
                fila = pg.get_by_test_id("fila")
                expect(fila).to_contain_text(protocolo)
                expect(pg.get_by_test_id("indicadores")).to_contain_text("Relatos agrupados")
                pg.get_by_test_id("rodar-robo").click()
                expect(pg.get_by_test_id("mensagem-robo")).to_contain_text("encaminhado(s)")
                pg.wait_for_timeout(1500)
                pg.screenshot(path=EVIDENCIAS / "04_painel_gestor.png", full_page=True)
                print("OK painel e robô RPA", flush=True)

                # Atendente revisa os dois pedidos sobre a caminhonete abandonada: confirma onde o
                # modelo acertou com pouca confiança e corrige onde errou.
                em_triagem = fila.locator("tr.linha-triagem").count()
                casos = fila.locator("tr.linha-triagem", has_text=re.compile("caminhonete", re.I))
                expect(casos).to_have_count(2)
                revisados = []
                for _ in range(2):
                    caso = fila.locator("tr.linha-triagem", has_text=re.compile("caminhonete", re.I)).first
                    numero = caso.locator("td").first.inner_text().splitlines()[0]
                    if caso.get_by_role("combobox").first.input_value() == "veiculo":
                        caso.get_by_role("button", name=re.compile("Confirmar")).click()
                    else:
                        caso.get_by_role("combobox").first.select_option("veiculo")
                    revisados.append(numero)
                    expect(fila.locator("tr.linha-triagem")).to_have_count(em_triagem - len(revisados))
                for numero in revisados:
                    expect(fila.locator("tr", has_text=numero)).to_contain_text("Veículo abandonado")
                pg.get_by_role("combobox", name=f"Situação de {protocolo}").select_option("Em atendimento")
                pg.get_by_text("Avançar 30 dias (demo)").click()
                expect(pg.get_by_test_id("mensagem-robo")).to_contain_text("escalado(s)")
                expect(fila).to_contain_text("prazo vencido")
                pg.wait_for_timeout(800)
                pg.screenshot(path=EVIDENCIAS / "05_prazo_vencido.png", full_page=True)
                print("OK triagem corrigida e prazo vencido escalado", flush=True)

                # 5. Cidadão acompanha a linha do tempo.
                pg.get_by_test_id("aba-acompanhar").click()
                pg.get_by_placeholder("ZC-20261117-ABC123").fill(protocolo)
                pg.get_by_role("button", name="Consultar").click()
                detalhe = pg.get_by_test_id("detalhe-pedido")
                expect(detalhe).to_contain_text("Novo apoio")
                expect(detalhe).to_contain_text("Encaminhado")
                expect(detalhe).to_contain_text("Escalado")
                expect(detalhe).not_to_contain_text("98765")
                pg.screenshot(path=EVIDENCIAS / "06_acompanhamento.png", full_page=True)
                print("OK linha do tempo do cidadão, sem dado pessoal", flush=True)

                oficios = list((Path(pasta) / "saida").glob("*.eml"))
                print(f"OK {len(oficios)} e-mails gerados pelo robô (ofícios, escalonamentos e avisos)", flush=True)
                (EVIDENCIAS / "exemplo_oficio.eml").write_bytes(sorted(oficios)[0].read_bytes())
                navegador.close()
        finally:
            servidor.kill()
    print("TODOS OS PASSOS PASSARAM")


if __name__ == "__main__":
    main()
