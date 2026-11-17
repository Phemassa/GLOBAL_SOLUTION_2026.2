"""NLP do ZelaCidade: anonimização, pré-processamento, classificação e urgência.

Fluxo de um texto: anonimizar (LGPD) -> normalizar -> TF-IDF -> regressão logística.
Com confiança abaixo do limiar, o pedido vai para triagem humana em vez de ser roteado
automaticamente: o modelo ajuda, mas não decide sozinho quando está em dúvida.
"""
import re
import unicodedata
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, make_pipeline

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_MODELO = RAIZ / "data" / "processed" / "modelo_nlp.joblib"
# Menor limiar com >= 90% de acerto nos pedidos automáticos, numa validação cruzada agrupada
# por frase de origem (simula frases nunca vistas). Escolhido no treino, antes de olhar o teste.
LIMIAR_CONFIANCA = 0.30

# ---------- Anonimização (antes de qualquer gravação) ----------
PADROES_PESSOAIS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "[EMAIL]"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    # Telefone exige separador entre os blocos, para não confundir com CEP (05409011): CEP é o
    # local do problema, não um dado da pessoa, e precisa continuar no texto.
    (re.compile(r"(?:\(\d{2}\)\s?|\b\d{2}\s)?\b9?\d{4}[-\s]\d{4}\b"), "[TELEFONE]"),
]


def anonimizar(texto: str) -> str:
    """Troca e-mail, CPF e telefone por marcadores. O texto anonimizado é o único guardado."""
    for padrao, marcador in PADROES_PESSOAIS:
        texto = padrao.sub(marcador, texto)
    return texto


# ---------- Pré-processamento ----------
def normalizar(texto: str) -> str:
    """Minúsculas, sem acento e sem pontuação: 'ÁRVORE caiu!!' e 'arvore caiu' viram o mesmo texto."""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\[(email|cpf|telefone)\]", " ", texto)
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def criar_modelo() -> object:
    # Palavras capturam o assunto; n-gramas de caracteres toleram erro de digitação ("pertod", "bueiro").
    vetorizador = FeatureUnion([
        ("palavras", TfidfVectorizer(preprocessor=normalizar, ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("caracteres", TfidfVectorizer(preprocessor=normalizar, analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)),
    ])
    return make_pipeline(vetorizador, LogisticRegression(C=5.0, max_iter=2000))


def treinar(caminho_treino: Path = RAIZ / "data" / "sintetico" / "mensagens_treino.csv"):
    dados = pd.read_csv(caminho_treino)
    modelo = criar_modelo().fit(dados["texto"].map(anonimizar), dados["categoria"])
    CAMINHO_MODELO.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, CAMINHO_MODELO)
    return modelo


_modelo = None


def modelo():
    global _modelo
    if _modelo is None:
        _modelo = joblib.load(CAMINHO_MODELO) if CAMINHO_MODELO.exists() else treinar()
    return _modelo


def classificar(texto: str) -> dict:
    """Categoria provável, confiança e as alternativas, para o cidadão e o gestor verem."""
    probabilidades = modelo().predict_proba([anonimizar(texto)])[0]
    classes = modelo().classes_
    ordem = probabilidades.argsort()[::-1]
    melhor = classes[ordem[0]]
    confianca = float(probabilidades[ordem[0]])
    return {
        "categoria": melhor,
        "confianca": round(confianca, 3),
        "triagem_humana": confianca < LIMIAR_CONFIANCA,
        "alternativas": [{"categoria": classes[i], "confianca": round(float(probabilidades[i]), 3)} for i in ordem[1:3]],
    }


# ---------- Urgência (regras explícitas, auditáveis) ----------
SINAIS_DE_RISCO = {
    "fio": 3, "fiacao caida": 4, "choque": 4, "faisca": 4, "caiu": 2, "cair": 2, "queda": 2, "risco": 2,
    "crianca": 2, "escola": 1, "creche": 2, "idoso": 2, "acidente": 3, "alaga": 2, "invade": 2,
    "sem tampa": 3, "bloque": 2, "perigos": 2, "escorpiao": 2, "dengue": 2, "urgente": 1,
}


def urgencia(texto: str) -> dict:
    """Pontua sinais de risco à vida ou à saúde. Regras e não ML: qualquer um pode conferir o porquê."""
    norm = normalizar(texto)
    encontrados = [termo for termo in SINAIS_DE_RISCO if termo in norm]
    pontos = sum(SINAIS_DE_RISCO[t] for t in encontrados)
    nivel = "alta" if pontos >= 4 else "media" if pontos >= 2 else "normal"
    return {"nivel": nivel, "pontos": pontos, "sinais": encontrados}
