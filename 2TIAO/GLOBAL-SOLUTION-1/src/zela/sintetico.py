"""Gera mensagens SINTÉTICAS de cidadãos para treinar e testar o classificador.

Os dados abertos do SP156 não publicam o texto que o cidadão escreveu (só a categoria),
então os textos são escritos a partir de frases montadas pelo grupo. São dados de
demonstração e estão identificados como tal em todo o projeto.

Para o teste não premiar frases decoradas, cada categoria tem dois conjuntos de frases
que não se repetem: o grupo "A" gera o treino e o grupo "B" gera o teste.

    python -m zela.sintetico        # grava data/sintetico/mensagens_*.csv
"""
import csv
import random
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "data" / "sintetico"

# Para cada categoria: (frases do conjunto A, frases do conjunto B).
FRASES = {
    "buraco": (
        ["tem um buraco enorme no meio da rua", "o asfalto afundou na frente de casa", "cratera na pista, os carros desviam pela contramão",
         "buraco aberto há semanas, já estourou pneu de vizinho", "o recapeamento ficou cheio de buracos", "asfalto todo esburacado na subida",
         "abriu um buraco depois da chuva", "a rua está cheia de panelas no asfalto"],
        ["formou um afundamento grande no pavimento", "motoqueiro caiu por causa do buraco na via", "o asfalto rachou e está soltando pedaços",
         "tem uma vala no meio da rua que ninguém tapa", "a operação tapa-buraco nunca passou aqui", "pista destruída, impossível passar de carro"],
    ),
    "entulho": (
        ["jogaram entulho na calçada", "virou ponto de descarte de lixo e restos de obra", "deixaram um sofá velho e móveis na esquina",
         "caçamba de entulho largada há dias", "despejaram sacos de reboco no terreno", "tem um monte de tijolo e madeira jogado na rua",
         "pessoal descarta colchão e geladeira velha aqui"],
        ["descarte irregular de material de construção na praça", "caminhão parou e despejou restos de demolição", "acumulou entulho de reforma bloqueando a passagem",
         "montanha de móveis quebrados e pneus jogados", "a caçamba está transbordando e ninguém recolhe", "jogam restos de obra toda noite no mesmo lugar"],
    ),
    "arvore": (
        ["a árvore está inclinada e pode cair", "galhos grandes caíram na calçada", "precisa de poda, os galhos estão batendo nas casas",
         "árvore caiu e bloqueou a rua", "a raiz da árvore levantou toda a calçada", "árvore seca com risco de queda", "tronco rachado depois do vento forte"],
        ["solicito poda da árvore em frente ao número da casa", "um galho quebrou e ficou pendurado", "a copa da árvore cresceu demais e escurece a rua",
         "árvore tombou sobre um carro estacionado", "cupim tomou conta do tronco e está oco", "pedido de remoção de árvore morta"],
    ),
    "calcada": (
        ["a calçada está toda quebrada", "a guia da calçada se soltou", "a sarjeta está destruída", "fio solto pendurado no poste",
         "o poste está torto e pode cair", "fiação caída na calçada", "poste quebrado depois de uma batida",
         "calçada sem rampa para cadeirante", "piso da calçada afundado, idosos tropeçam", "degrau enorme na calçada impede a passagem"],
        ["cabos arrebentados balançando na calçada", "emaranhado de fios baixos quase encostando nos carros", "o poste está rachado na base",
         "não dá para andar no passeio de tanto buraco", "o meio-fio desmoronou depois da obra", "cadeira de rodas não passa pela calçada estreita"],
    ),
    "drenagem": (
        ["a boca de lobo está entupida", "toda chuva a rua alaga", "o bueiro está sem tampa", "água da chuva não escoa e invade as casas",
         "galeria pluvial entupida de lixo", "a grade do bueiro quebrou", "enxurrada forma um rio na esquina"],
        ["a sarjeta fica empoçada dias depois da chuva", "o córrego transbordou e entrou nas casas", "tampa do bueiro afundou e virou armadilha",
         "precisa de limpeza das bocas de lobo antes das chuvas", "a água volta pelo ralo da rua quando chove", "alagamento constante embaixo do viaduto"],
    ),
    "varricao": (
        ["a rua está muito suja, ninguém varre", "folhas e areia acumuladas na sarjeta", "a calçada da praça está imunda",
         "varrição não passa na nossa rua há semanas", "depois da feira a rua fica cheia de lixo espalhado", "sujeira acumulada no canteiro central"],
        ["pedido de limpeza da via pública", "ficou lama e terra na rua depois da obra", "a escadaria pública está cheia de sujeira",
         "solicito equipe de varrição para o quarteirão", "restos de feira apodrecendo na calçada", "papel e garrafa espalhados pela praça toda"],
    ),
    "coleta": (
        ["o caminhão do lixo não passou essa semana", "a coleta de lixo está atrasada", "os sacos de lixo estão acumulando na porta",
         "a coleta pulou a nossa rua de novo", "lixo doméstico parado há três dias", "o lixeiro não recolheu o lixo do prédio"],
        ["faz dias que a coleta domiciliar não aparece", "o horário da coleta mudou e ninguém avisou", "cachorros rasgando os sacos porque o lixo não foi recolhido",
         "a coleta recolhe só um lado da rua", "lixo residencial acumulado atraindo bichos", "o caminhão de coleta passou direto sem parar"],
    ),
    "capinacao": (
        ["o mato está alto no terreno da praça", "precisa roçar o canteiro, o capim está enorme", "mato tomou conta da calçada",
         "área verde abandonada com mato até a cintura", "capinação da praça não é feita há meses", "o mato cresceu e esconde a placa"],
        ["solicito roçada da área pública", "vegetação alta escondendo o ponto de ônibus", "o barranco está coberto de mato",
         "mato alto atrai cobra e escorpião perto das casas", "precisa de corte da grama do parque", "erva daninha cobrindo a passagem de pedestres"],
    ),
    "barulho": (
        ["o bar toca música alta até de madrugada", "barulho insuportável de som automotivo", "a igreja faz barulho alto todas as noites",
         "festa com som alto todo fim de semana", "a oficina faz barulho a partir das cinco da manhã", "baile funk na rua não deixa ninguém dormir"],
        ["poluição sonora vinda do estabelecimento comercial", "o volume do som da casa noturna atravessa as paredes", "o restaurante põe caixa de som na calçada",
         "a academia liga música alta muito cedo", "perturbação do sossego com som ligado a noite toda", "estabelecimento descumpre o horário e faz barulho"],
    ),
    "veiculo": (
        ["tem um carro abandonado na rua há meses", "carcaça de carro largada na calçada", "veículo abandonado com pneus murchos e vidro quebrado",
         "um caminhão velho está parado aqui há um ano", "carro sem placa jogado na esquina", "moto abandonada acumulando lixo"],
        ["veículo enferrujado ocupando a vaga há muito tempo", "carro depenado servindo de abrigo para ratos", "automóvel parado sem ninguém mexer desde o ano passado",
         "um ônibus velho foi largado no terreno da rua", "carro coberto de poeira e folhas, claramente abandonado", "caminhonete batida esquecida na via"],
    ),
    "sinalizacao": (
        ["o semáforo está apagado no cruzamento", "a faixa de pedestre está apagada", "a placa de pare foi derrubada",
         "o farol fica vermelho para todos os lados", "falta sinalização na frente da escola", "o semáforo está piscando amarelo o dia todo"],
        ["a pintura da faixa sumiu e os carros não param", "placa de velocidade arrancada da via", "cruzamento perigoso precisa de um semáforo",
         "o sinal de pedestres não abre", "lombada sem pintura e sem placa de aviso", "a seta da mão de direção está errada"],
    ),
    "pragas": (
        ["a rua está cheia de ratos", "apareceram escorpiões no quintal", "muito mosquito da dengue por causa da água parada",
         "infestação de baratas saindo do bueiro", "terreno com água parada e foco de mosquito", "pombos fazendo ninho e sujando tudo",
         "tem uma colmeia de abelhas no muro", "ninho de vespas no poste da esquina"],
        ["ratazanas circulando de dia perto do mercado", "achei escorpião dentro de casa de novo", "foco de dengue no imóvel abandonado ao lado",
         "caramujo africano se espalhando no terreno", "morcegos entrando nas casas da vila", "precisa de dedetização na praça por causa dos ratos"],
    ),
}

# Vocabulário extra só do conjunto A (treino), combinado em frases "tem <objeto> <estado>".
# Parte dos termos vem dos nomes oficiais dos serviços do SP156 (dado real); o resto é escrito
# pelo grupo. O conjunto B (teste) não usa estas combinações.
COMPOSICOES_A = {
    "buraco": (["buraco", "cratera", "asfalto", "pavimento", "tapa-buraco", "pista"], ["na rua", "afundado", "quebrado", "sem conserto há meses", "que ninguém arruma"]),
    "entulho": (["entulho", "restos de obra", "móveis velhos", "caçamba", "lixo grande", "tijolos"], ["jogados na via pública", "abandonados na calçada", "despejados no terreno", "largados na esquina"]),
    "arvore": (["árvore", "galho", "tronco", "raiz", "copa da árvore"], ["com risco de queda", "precisando de poda", "caído na calçada", "quebrado", "invadindo a fiação"]),
    "calcada": (["calçada", "guia", "sarjeta", "sarjetão", "poste", "fio"], ["quebrada", "solto", "danificada", "em mau estado", "atrapalhando a acessibilidade"]),
    "drenagem": (["boca de lobo", "bueiro", "galeria de água da chuva", "poço de visita", "rua"], ["entupido", "alagada", "sem tampa", "transbordando na chuva", "precisando de limpeza"]),
    "varricao": (["rua", "calçadão", "sarjeta", "praça", "sacos de varrição"], ["suja", "sem varrição", "precisando de lavagem", "cheia de folhas e areia", "sem remoção há dias"]),
    "coleta": (["coleta de lixo", "caminhão de lixo", "lixo de casa", "sacos de lixo domiciliar"], ["atrasada", "não passou", "acumulado na porta", "não recolhidos"]),
    "capinacao": (["mato", "capim", "grama da praça", "canteiro central", "área verde"], ["alto", "sem capinação", "sem roçada", "tomando a calçada"]),
    "barulho": (["som alto", "música", "barulho", "festa", "bar"], ["a noite toda", "de madrugada", "acima do permitido pelo PSIU", "perturbando os vizinhos"]),
    "veiculo": (["carro", "carcaça", "moto", "caminhão", "veículo"], ["abandonado na via", "parado há meses", "sem placa e depenado", "enferrujando na rua"]),
    "sinalizacao": (["semáforo", "placa de trânsito", "faixa de pedestre", "placa com nome da rua", "sinalização"], ["apagada", "quebrado", "sem pintura", "faltando", "com tempo errado"]),
    "pragas": (["ratos", "escorpiões", "pernilongos", "pombos", "morcegos", "abelhas"], ["infestando o local", "aparecendo nas casas", "precisando de vistoria", "em grande quantidade"]),
}

ABERTURAS_A =["", "bom dia, ", "olá, ", "prefeitura, ", "gostaria de reclamar: ", "por favor, "]
ABERTURAS_B = ["", "boa tarde. ", "oi, ", "venho informar que ", "socorro, ", "alguém pode ajudar? "]
LUGARES_A = ["na rua das flores", "perto da escola municipal", "em frente ao número 120", "na esquina com a avenida", "ao lado do posto de saúde", ""]
LUGARES_B = ["no fim da rua sem saída", "atrás do mercado", "na altura do ponto de ônibus", "próximo à creche", "na viela do bairro", ""]
FECHOS_A = ["", " já reclamei antes.", " por favor resolvam.", " é perigoso.", " obrigado."]
FECHOS_B = ["", " ninguém faz nada.", " aguardo retorno.", " moradores estão revoltados.", " urgente!"]

# Dados pessoais inventados, para testar a anonimização antes de gravar o texto.
DADOS_PESSOAIS = [" meu telefone é (11) 98765-4321.", " meu cpf é 123.456.789-09.", " me respondam no joana.silva@email.com.",
                  " contato: 11 91234-5678.", " CPF 987.654.321-00, aguardo."]


def _sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _ruido(texto, rng):
    """Erros comuns de digitação e escrita informal."""
    if rng.random() < 0.35:
        texto = _sem_acento(texto)
    if rng.random() < 0.25:
        for formal, informal in (("você", "vc"), ("porque", "pq"), ("também", "tb"), ("por favor", "pfv"), ("muito", "mto")):
            texto = texto.replace(formal, informal)
    if rng.random() < 0.2 and len(texto) > 10:
        i = rng.randrange(1, len(texto) - 1)
        texto = texto[:i] + texto[i + 1] + texto[i] + texto[i + 2:]  # troca duas letras
    if rng.random() < 0.15:
        texto = texto.upper()
    return texto


def gerar(conjunto, n_por_categoria, semente):
    rng = random.Random(semente)
    indice = 0 if conjunto == "A" else 1
    aberturas, lugares, fechos = (ABERTURAS_A, LUGARES_A, FECHOS_A) if conjunto == "A" else (ABERTURAS_B, LUGARES_B, FECHOS_B)
    linhas = []
    for categoria, pares in FRASES.items():
        frases = pares[indice]
        for _ in range(n_por_categoria):
            if conjunto == "A" and rng.random() < 0.4:
                objetos, estados = COMPOSICOES_A[categoria]
                objeto = rng.choice(objetos)
                frase = f"tem {objeto} {rng.choice(estados)}"
                grupo = f"{categoria}:composicao:{objeto}"
            else:
                frase = rng.choice(frases)
                grupo = f"{categoria}:frase:{frases.index(frase)}"
            lugar = rng.choice(lugares)
            texto = f"{rng.choice(aberturas)}{frase} {lugar}".strip() + "." + rng.choice(fechos)
            if rng.random() < 0.15:
                texto += rng.choice(DADOS_PESSOAIS)
            linhas.append({"texto": _ruido(texto, rng), "categoria": categoria, "conjunto": conjunto, "grupo": grupo, "origem": "sintetico"})
    rng.shuffle(linhas)
    return linhas


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    for nome, conjunto, n, semente in (("mensagens_treino.csv", "A", 150, 42), ("mensagens_teste.csv", "B", 50, 7)):
        linhas = gerar(conjunto, n, semente)
        with open(SAIDA / nome, "w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=["texto", "categoria", "conjunto", "grupo", "origem"])
            escritor.writeheader()
            escritor.writerows(linhas)
        print(f"{nome}: {len(linhas)} mensagens sintéticas")


if __name__ == "__main__":
    main()
