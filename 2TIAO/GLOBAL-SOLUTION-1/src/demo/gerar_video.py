"""Gera o vídeo demonstrativo (até 5 min): slides + gravação real da aplicação + narração neural pt-BR.

    cd src && python -m demo.gerar_video        (requer: npm run build em src/web; internet para a voz)

Cada cena tem uma fala; a duração da fala define a duração da cena. As cenas de demonstração
são gravadas pelo navegador enquanto a aplicação roda de verdade, num banco temporário.
"""
import asyncio
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg
from playwright.sync_api import expect, sync_playwright

from demo.e2e_interface import URL, popular_demonstracao, subir_servidor

RAIZ = Path(__file__).resolve().parents[2]
EVID = RAIZ / "docs" / "evidencias"
SAIDA = RAIZ / "docs" / "video" / "ZelaCidade_GrupoZion.mp4"
VOZ = os.environ.get("VOZ", "pt-BR-FranciscaNeural")
FF = imageio_ffmpeg.get_ffmpeg_exe()
LARGURA, ALTURA = 1280, 720
PAUSA = 0.6

FALAS = {
    "abertura": "Grupo Zion. Quero concorrer! Este é o Zela Cidade: zeladoria urbana com inteligência artificial, "
                "a nossa solução para o desafio Citizen Tech.",
    "problema": "Buraco na rua, entulho na calçada, bueiro entupido. Pelos dados abertos da Prefeitura de São Paulo, "
                "o canal cento e cinquenta e seis recebeu mais de trezentos e dezesseis mil pedidos de zeladoria em seis meses. "
                "Nesses mesmos dados, dezoito por cento dos pedidos repetem outro, no mesmo ponto, que ainda estava aberto. "
                "E o prazo varia de um dia, para entulho, a trinta e cinco dias, para veículo abandonado.",
    "cidadao": "Na prática: o cidadão escreve do próprio jeito. Enquanto ele digita, o modelo de linguagem natural mostra a categoria "
               "que entendeu, com o grau de confiança, o prazo típico real e como o telefone vai ficar oculto. "
               "Ele marca o local no mapa e envia. O sistema descobre a subprefeitura e o órgão que de fato atende esse problema ali.",
    "agrupamento": "Se outra pessoa relata o mesmo buraco, no mesmo lugar, o sistema não abre um novo chamado: soma o relato ao protocolo existente. "
                   "E quando o texto é vago, o pedido vai para triagem humana, em vez de ser encaminhado no escuro.",
    "painel": "No painel da prefeitura, a fila é ordenada por urgência e número de relatos. O robô de automação envia o ofício ao órgão "
              "responsável e avisa o cidadão. O atendente confirma ou corrige a categoria dos casos em dúvida. "
              "Simulando trinta dias, o robô escala os pedidos que passaram do prazo real da categoria.",
    "acompanhar": "O cidadão acompanha tudo pelo protocolo, numa linha do tempo, sem nenhum dado pessoal exposto. "
                  "Quando o pedido termina, o robô apaga o e-mail dele.",
    "integracao": "A solução integra as disciplinas do ano: processamento de linguagem natural para entender o relato; "
                  "automação de processos com um robô; uma A, P, I, do tipo rést, em Python; a interface em React; "
                  "e governança de dados, com anonimização, consentimento e retenção mínima, seguindo a lei geral de proteção de dados.",
    "resultados": "Fomos honestos com os resultados. Como a prefeitura não publica o texto dos cidadãos, os relatos de treino são sintéticos. "
                  "Em frases nunca vistas, o modelo acertou sessenta e nove por cento, e o valor mínimo de confiança não garantiu os noventa por cento esperados. "
                  "Por isso ele funciona como triagem assistida, com revisão humana. Todo o fluxo foi testado de forma automatizada, inclusive no navegador.",
    "ods": "O projeto contribui com os objetivos de desenvolvimento sustentável onze, cidades sustentáveis, e dezesseis, instituições eficazes. "
           "Medimos o impacto pelos chamados duplicados evitados, pelos pedidos resolvidos no prazo e pelos atrasos escalados. "
           "O próximo passo é um piloto com relatos reais. Obrigado!",
}

CSS = """*{box-sizing:border-box;margin:0}body{width:1280px;height:720px;background:#0f3d3a;color:#eef6f5;font-family:'Segoe UI',sans-serif;padding:48px 60px;overflow:hidden;position:relative}
h1{font-size:60px;margin-bottom:10px}h2{font-size:38px;color:#5eead4;margin-bottom:22px}p,li{font-size:27px;line-height:1.4}ul{padding-left:30px}li{margin-bottom:12px}
b{color:#fcd34d}img{background:#fff;border-radius:8px;display:block}.rod{position:absolute;bottom:18px;left:60px;right:60px;font-size:16px;color:#99c5c0;display:flex;justify-content:space-between}
.col{display:flex;gap:30px;align-items:flex-start}.col>div{flex:1}.grande{font-size:34px}"""
ROD = '<div class="rod"><span>ZelaCidade · Grupo Zion · Global Solution 2026.2</span><span>Dados reais: SP156/Prefeitura de São Paulo (CC0)</span></div>'


def slides():
    e = EVID.as_uri()
    return {
        "abertura": f"""<p style="margin-top:70px;font-size:30px;color:#99c5c0">Global Solution 2026.2 · CitizenTech</p>
            <h1 style="font-size:84px">ZelaCidade</h1><p class="grande">Zeladoria urbana com IA: o cidadão descreve o problema<br>com as próprias palavras, e o sistema resolve o caminho.</p>
            <p style="margin-top:50px;font-size:44px;color:#fcd34d;font-weight:700">Grupo Zion · QUERO CONCORRER</p>""",
        "problema": f"""<h2>O problema, nos dados reais do SP156</h2><div class="col"><div><ul>
            <li><b>316.522</b> pedidos de zeladoria em 6 meses (2026)</li><li><b>18,4%</b> repetem um pedido aberto no mesmo ponto</li>
            <li>Prazo de <b>1 a 35 dias</b> conforme a categoria</li></ul></div>
            <div><img src="{e}/dados_volume_prazo.png" style="width:650px"></div></div>""",
        "integracao": """<h2>Integração das disciplinas</h2><ul>
            <li><b>NLP:</b> anonimização, pré-processamento, TF-IDF e regressão logística</li>
            <li><b>Automação e RPA:</b> robô que encaminha, escala atrasos e avisa o cidadão</li>
            <li><b>API REST:</b> FastAPI com documentação automática</li>
            <li><b>React:</b> interface do cidadão e painel da prefeitura, com mapa e gráficos</li>
            <li><b>Governança de dados:</b> anonimização, consentimento, retenção mínima (LGPD)</li>
            <li><b>Dados reais:</b> prazos, órgãos e subprefeituras do SP156</li></ul>""",
        "resultados": f"""<h2>Resultados e limitações</h2><div class="col"><div><ul>
            <li>Textos dos cidadãos são <b>sintéticos</b> (a Prefeitura não publica o relato)</li>
            <li>Frases nunca vistas: <b>69%</b> de acerto; automáticos: <b>78,5%</b> (meta era 90%)</li>
            <li>Por isso: <b>triagem assistida</b>, com revisão humana</li>
            <li><b>10</b> testes do backend e teste no navegador: todos passando</li></ul></div>
            <div><img src="{e}/nlp_confusao.png" style="width:470px"></div></div>""",
        "ods": """<h2>ODS e impacto</h2><ul>
            <li><b>ODS 11</b>: cidades e comunidades sustentáveis</li><li><b>ODS 16</b>: instituições eficazes, responsáveis e transparentes</li></ul>
            <p style="margin:26px 0 12px">Como medir:</p><ul><li>chamados duplicados evitados (hoje: 18,4% de repetição)</li>
            <li>% de pedidos resolvidos até o prazo real da categoria</li><li>atrasos escalados automaticamente</li></ul>
            <p style="margin-top:34px;color:#fcd34d;font-size:32px">Próximo passo: piloto com relatos reais. Obrigado!</p>""",
    }


async def _sintetizar(texto, destino):
    await edge_tts.Communicate(texto, VOZ).save(str(destino))


CACHE_VOZ = RAIZ / "data" / "runtime" / "voz"


def narrar(pasta: Path) -> dict:
    """Sintetiza cada fala, reaproveitando o cache quando o texto e a voz não mudaram."""
    import hashlib
    import shutil
    CACHE_VOZ.mkdir(parents=True, exist_ok=True)
    duracoes = {}
    for nome, fala in FALAS.items():
        mp3, wav = pasta / f"{nome}.mp3", pasta / f"{nome}.wav"
        cache = CACHE_VOZ / (hashlib.sha1(f"{VOZ}|{fala}".encode()).hexdigest()[:16] + ".mp3")
        if cache.exists():
            shutil.copy(cache, mp3)
        for tentativa in range(0 if cache.exists() else 15):
            try:
                asyncio.run(_sintetizar(fala, mp3))
                break
            except Exception as erro:
                print(f"voz {nome}: tentativa {tentativa + 1} falhou ({type(erro).__name__})", flush=True)
                time.sleep(15)
        else:
            if not cache.exists():
                raise SystemExit("Serviço de voz indisponível")
        if not cache.exists():
            shutil.copy(mp3, cache)
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "2", "-ar", "48000", str(wav)], check=True)
        with wave.open(str(wav)) as w:
            duracoes[nome] = w.getnframes() / w.getframerate() + PAUSA
        print(f"fala {nome}: {duracoes[nome]:.1f} s", flush=True)
    return duracoes


def renderizar_slides(navegador, pasta: Path):
    pg = navegador.new_page(viewport={"width": LARGURA, "height": ALTURA})
    for nome, html in slides().items():
        arquivo = pasta / f"{nome}.html"
        arquivo.write_text(f'<!doctype html><html><head><meta charset="utf8"><style>{CSS}</style></head><body>{html}{ROD}</body></html>', encoding="utf8")
        pg.goto(arquivo.as_uri())
        pg.wait_for_timeout(400)
        pg.screenshot(path=pasta / f"{nome}.png")
    pg.close()


def gravar_cena(navegador, pasta, nome, duracao, acoes):
    """Grava a cena e garante que dure pelo menos o tempo da fala."""
    contexto = navegador.new_context(viewport={"width": LARGURA, "height": ALTURA}, locale="pt-BR",
                                     record_video_dir=str(pasta / f"bruto_{nome}"), record_video_size={"width": LARGURA, "height": ALTURA})
    pg = contexto.new_page()
    inicio = time.time()
    acoes(pg)
    restante = duracao - (time.time() - inicio)
    if restante > 0:
        pg.wait_for_timeout(restante * 1000)
    video = pg.video.path()
    contexto.close()
    return Path(video)


def main():
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pasta = Path(tmp)
        duracoes = narrar(pasta)
        print(f"Narração total: {sum(duracoes.values()):.0f} s", flush=True)
        servidor = subir_servidor(pasta)
        estado = {}
        try:
            with sync_playwright() as p:
                navegador = p.chromium.launch(channel=os.environ.get("CANAL", "msedge"), headless=True)
                renderizar_slides(navegador, pasta)

                def cena_cidadao(pg):
                    pg.goto(URL)
                    pg.wait_for_timeout(1500)
                    pg.get_by_test_id("texto").click()
                    pg.keyboard.type("Tem um buraco enorme na frente da escola, os carros desviam pela contramão. Me liga (11) 98765-4321", delay=45)
                    expect(pg.get_by_test_id("previa")).to_contain_text("Buraco", timeout=10000)
                    pg.wait_for_timeout(5000)
                    caixa = pg.get_by_test_id("mapa-pedido").bounding_box()
                    estado["centro"] = (caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2)
                    pg.mouse.click(*estado["centro"])
                    pg.wait_for_timeout(1500)
                    pg.get_by_test_id("enviar").click()
                    expect(pg.get_by_test_id("resultado-pedido")).to_contain_text("Pedido registrado")
                    estado["protocolo"] = pg.get_by_test_id("protocolo").inner_text()

                def cena_agrupamento(pg):
                    pg.goto(URL)
                    pg.get_by_test_id("texto").click()
                    pg.keyboard.type("o asfalto afundou aqui na rua da escola, cratera perigosa", delay=40)
                    expect(pg.get_by_test_id("previa")).to_contain_text("Buraco")
                    pg.mouse.click(*estado["centro"])
                    pg.wait_for_timeout(800)
                    pg.get_by_test_id("enviar").click()
                    expect(pg.get_by_test_id("resultado-pedido")).to_contain_text("já foi relatado aqui")
                    pg.wait_for_timeout(5500)
                    pg.get_by_text("Fazer outro pedido").click()
                    pg.get_by_test_id("texto").click()
                    pg.keyboard.type("preciso de ajuda com uma situação aqui perto de casa", delay=40)
                    pg.wait_for_timeout(1200)
                    pg.get_by_test_id("enviar").click()
                    expect(pg.get_by_test_id("resultado-pedido")).to_contain_text("um atendente vai conferir")

                def cena_painel(pg):
                    popular_demonstracao()
                    pg.goto(URL)
                    pg.get_by_test_id("aba-painel").click()
                    expect(pg.get_by_test_id("fila")).to_contain_text(estado["protocolo"])
                    pg.wait_for_timeout(2500)
                    pg.get_by_test_id("rodar-robo").click()
                    expect(pg.get_by_test_id("mensagem-robo")).to_contain_text("encaminhado")
                    pg.wait_for_timeout(3000)
                    fila = pg.get_by_test_id("fila")
                    caso = fila.locator("tr.linha-triagem", has_text="caminhonete").first
                    caso.scroll_into_view_if_needed()
                    pg.wait_for_timeout(1500)
                    if caso.get_by_role("combobox").first.input_value() == "veiculo":
                        caso.get_by_role("button", name="Confirmar").first.click()
                    else:
                        caso.get_by_role("combobox").first.select_option("veiculo")
                    pg.wait_for_timeout(2500)
                    pg.mouse.wheel(0, -3000)
                    pg.get_by_text("Avançar 30 dias (demo)").click()
                    expect(pg.get_by_test_id("mensagem-robo")).to_contain_text("escalado")
                    pg.wait_for_timeout(2500)
                    pg.mouse.wheel(0, 500)

                def cena_acompanhar(pg):
                    pg.goto(URL)
                    pg.get_by_test_id("aba-acompanhar").click()
                    pg.get_by_placeholder("ZC-20261117-ABC123").fill(estado["protocolo"])
                    pg.get_by_role("button", name="Consultar").click()
                    expect(pg.get_by_test_id("detalhe-pedido")).to_contain_text("Escalado")

                videos = {}
                for nome, acoes in (("cidadao", cena_cidadao), ("agrupamento", cena_agrupamento),
                                    ("painel", cena_painel), ("acompanhar", cena_acompanhar)):
                    videos[nome] = gravar_cena(navegador, pasta, nome, duracoes[nome], acoes)
                    print(f"cena {nome} gravada", flush=True)
                navegador.close()
        finally:
            servidor.kill()

        # Monta: cada cena com sua fala, cortada ou estendida (último quadro) para a duração exata.
        ordem = ["abertura", "problema", "cidadao", "agrupamento", "painel", "acompanhar", "integracao", "resultados", "ods"]
        partes = []
        for nome in ordem:
            dur = duracoes[nome]
            entrada = ["-loop", "1", "-framerate", "30", "-t", f"{dur:.3f}", "-i", str(pasta / f"{nome}.png")] if nome not in videos \
                else ["-i", str(videos[nome])]
            parte = pasta / f"parte_{nome}.mp4"
            subprocess.run([FF, "-y", "-loglevel", "error", *entrada, "-i", str(pasta / f"{nome}.wav"),
                            "-filter_complex", f"[0:v]fps=30,scale={LARGURA}:{ALTURA},format=yuv420p,tpad=stop_mode=clone:stop_duration=60,trim=duration={dur:.3f},setpts=PTS-STARTPTS[v];"
                                               f"[1:a]apad=whole_dur={dur:.3f},atrim=duration={dur:.3f}[a]",
                            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "medium",
                            "-crf", "21", "-bf", "0", "-g", "60", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", str(parte)], check=True)
            partes.append(parte)
        lista = pasta / "lista.txt"
        lista.write_text("".join(f"file '{p.as_posix()}'\n" for p in partes), encoding="utf8")
        subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                        "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-crf", "21", "-bf", "0", "-g", "60",
                        "-c:a", "aac", "-b:a", "160k", "-brand", "mp42", "-movflags", "+faststart", str(SAIDA)], check=True)
    print(f"Vídeo: {SAIDA} ({sum(duracoes.values()):.0f} s)")


if __name__ == "__main__":
    main()
