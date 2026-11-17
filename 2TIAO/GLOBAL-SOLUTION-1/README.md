# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href="https://www.fiap.com.br/">
  <img src="../../assets/logo-fiap.png"
       alt="FIAP - Faculdade de Informática e Administração Paulista"
       width="40%">
</a>
</p>

<br>

# ZelaCidade: zeladoria urbana com IA

## Grupo Zion

## 👨‍🎓 Integrantes:
- <a href="https://www.linkedin.com/in/cesar-azeredo">Cesar Martinho de Azeredo (RM568140)</a>
- <a href="https://www.linkedin.com/in/carlos-costato/">Carlos Alberto Florindo Costato (RM567005)</a>
- <a href="https://www.linkedin.com/in/phellype-massarente-13739810a/">Phellype Matheus Giacoia Flaibam Massarente (RM566826)</a>

## 👩‍🏫 Professores:

### Tutor(a)
- Andre Godoy

### Coordenador(a)
- Ana Cristina dos Santos

## 📜 Descrição

**O problema.** Buraco no asfalto, entulho na calçada, bueiro entupido, árvore com risco de queda: a zeladoria urbana é o serviço público mais presente no dia a dia de quem mora numa cidade grande. Pelos dados abertos da Prefeitura de São Paulo, o canal SP156 recebeu **316.522 pedidos de zeladoria** só entre abril e setembro de 2026, nas 12 categorias tratadas aqui. Três dificuldades aparecem nesses dados reais:

1. **O cidadão precisa saber "onde se encaixa" o problema.** São dezenas de serviços oficiais com nomes técnicos ("Guias, sarjetas e sarjetões - solicitar manutenção"), e o órgão responsável muda conforme a região.
2. **Retrabalho.** **18,4%** dos pedidos repetem um anterior da mesma categoria, no mesmo ponto, que ainda estava aberto; no caso de barulho, são 51%.
3. **Prazos muito desiguais e pouco visíveis.** A mediana vai de 1 dia (entulho) a 35 dias (veículo abandonado).

**Quem se beneficia.** Moradores, em especial quem tem pouca familiaridade com serviços digitais (escrevem do próprio jeito, sem formulário de categorias); equipes de atendimento da Prefeitura (menos triagem manual e menos chamado duplicado); e gestores públicos (indicadores de prazo e atraso).

**A solução.** O ZelaCidade é uma prova de conceito em que o cidadão descreve o problema em texto livre e marca o local no mapa. O sistema então:

| Etapa | Como | Disciplina |
|---|---|---|
| Esconde dados pessoais do texto (telefone, CPF, e-mail) antes de gravar | Expressões regulares | Governança de dados (LGPD) |
| Entende a categoria e avisa quando não tem certeza | TF-IDF + regressão logística, com triagem humana abaixo do limiar | NLP |
| Junta relatos do mesmo problema (mesma categoria, até 30 m, ainda aberto) | Distância geográfica | Python / dados |
| Descobre a subprefeitura e o órgão que de fato atende aquilo ali | Tabelas construídas com os dados reais do SP156 | Dados / governança |
| Informa o prazo típico real | Mediana e percentil 80 reais por categoria | Dados |
| Encaminha ofício, escala atraso, avisa o cidadão e apaga o e-mail no fim | Robô agendado (RPA) + e-mail | Automação de processos / RPA |
| Expõe tudo por API e interface web | FastAPI (REST) + React | APIs REST / React |

**ODS relacionados:** ODS 11 (Cidades e comunidades sustentáveis) e ODS 16 (Instituições eficazes, responsáveis e transparentes). Os indicadores de impacto estão no relatório.

**O que é real e o que é simulado:**

- **Reais:** volumes, prazos, órgãos, subprefeituras e locais, todos do SP156, com licença CC0.
- **Sintéticos:** os textos dos cidadãos, escritos pelo grupo, porque a Prefeitura não publica o relato.
- **De demonstração:** os pedidos usados nas demonstrações e os e-mails dos órgãos.

Relatório completo (PDF da entrega): [docs/GS_2026-2_GrupoZion_ZelaCidade.pdf](docs/GS_2026-2_GrupoZion_ZelaCidade.pdf).

## 📁 Estrutura de pastas

* **`data/`** Bases do projeto. `raw/` recebe os CSVs originais do SP156 (fora do Git, baixados pelo script); `processed/` tem as tabelas derivadas dos dados reais e o modelo treinado; `sintetico/` tem os textos de demonstração. Procedência em [data/README.md](data/README.md).
* **`docs/`** Relatório da entrega (PDF e fonte), roteiro do vídeo e `evidencias/` com prints e gráficos gerados pelos testes e notebooks.
* **`notebooks/`** `01_analise_sp156.ipynb` (o problema nos dados reais) e `02_modelo_nlp.ipynb` (treino, limiar e avaliação do classificador), já executados. `fontes/` guarda a versão em texto de cada notebook.
* **`src/`** Código-fonte: `zela/` (dados, NLP, regras de negócio, API e robô RPA), `web/` (interface React) e `demo/` (teste ponta a ponta da interface).
* **`tests/`** Testes automatizados do backend (pytest).
* **`README.md`** Este arquivo.

## 📎 Links e Observações

### 🔗 Links do Projeto

* **Vídeo de entrega no YouTube (não listado)**: ⚠️ `TODO(humano)`: colar o link depois de publicar o vídeo.
* **[Vídeo (arquivo)](docs/video/ZelaCidade_GrupoZion.mp4)**: o mesmo vídeo (2min50s), com [roteiro e falas](docs/video/ROTEIRO.md).
* **[Dados do SP156 - Solicitações](https://dados.prefeitura.sp.gov.br/dataset/dados-do-sp156)**: fonte dos dados reais (Prefeitura de São Paulo, CC0).

### 🧠 Decisões Técnicas

> **Categorias pelo serviço oficial, não pelo assunto.** O assunto "Sinalização e Circulação" do SP156 é 70% isenção de rodízio (não é zeladoria), e "Fiação e Postes" é quase todo manutenção de calçada. Filtrar pelo serviço oficial evitou números contaminados.
>
> **Texto sintético declarado, com teste em frases nunca vistas.** O modelo é testado em frases de um conjunto que não aparece no treino e em mensagens escritas à mão antes dos resultados. Nas frases novas, o acerto geral foi de 69%; nos pedidos encaminhados automaticamente, de 78,5%, abaixo dos 90% esperados na validação. Por isso o modelo funciona como **triagem assistida**: baixa confiança vai para um atendente, e toda categoria é corrigível no painel.
>
> **TF-IDF + regressão logística**, em vez de um modelo de linguagem grande: é treinável com poucos dados, roda em qualquer servidor, dá probabilidades para a triagem e é explicável. Pedaços de caracteres toleram erros de digitação.
>
> **Urgência por regras explícitas, não por ML.** Em risco à vida, qualquer pessoa precisa conseguir conferir por que um pedido subiu na fila.
>
> **Privacidade desde o projeto:** anonimização antes de gravar, e-mail só com consentimento, guardado em tabela separada e apagado pelo robô quando o pedido termina; coordenadas reais arredondadas para ~100 m.
>
> **FastAPI + SQLite + React:** API documentada automaticamente (`/docs`), banco em arquivo único para a POC e interface com mapa (Leaflet/OpenStreetMap) e gráficos (Recharts), servidas na mesma porta.

### 📢 Observações Gerais

* **Participação na Competição:** [x] Sim, aceitamos participar / [ ] Não vamos participar.
* *Outras observações gerais:* projeto acadêmico. Não substitui o SP156 nem foi validado pela Prefeitura de São Paulo.

## 🔧 Como executar o código

**Pré-requisitos:** Python 3.12, Node.js 20 ou superior e acesso à internet (download dos dados e mapa).

```bash
# 1. Ambiente Python
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r 2TIAO/GLOBAL-SOLUTION-1/requirements.txt

cd 2TIAO/GLOBAL-SOLUTION-1/src

# 2. Dados reais (baixa ~200 MB do SP156 e gera data/processed/) e textos sintéticos
python -m zela.dados
python -m zela.sintetico

# 3. Interface React (gera src/web/dist, servida pela própria API)
cd web && npm install && npm run build && cd ..

# 4. Sobe tudo em http://127.0.0.1:8000  (API em /docs; token do gestor: zela-demo)
uvicorn zela.api:app --port 8000

# 5. Robô RPA, em outro terminal (sem SMTP, os e-mails viram arquivos em data/runtime/saida/)
python -m zela.rpa --intervalo 30
```

**Testes:**

```bash
cd 2TIAO/GLOBAL-SOLUTION-1
python -m pytest tests                 # backend: anonimização, NLP, agrupamento, roteamento, API e RPA
cd src && python -m demo.e2e_interface  # interface no navegador, gera os prints em docs/evidencias
```

O modelo de NLP é treinado na primeira execução, se o arquivo `data/processed/modelo_nlp.joblib` não existir.

---

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/fiap-tutoria/FIAP-PORTFOLIO-AI">TEMPLATE - FIAP PORTFÓLIO AI</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">FIAP</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
