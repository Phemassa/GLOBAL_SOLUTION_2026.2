# Dados do ZelaCidade

| Pasta | Conteúdo | Origem | No Git? |
|---|---|---|---|
| `raw/` | CSVs originais do SP156, 2º e 3º trimestres de 2026 (~100 MB cada), e o dicionário de dados | **Real** | Não: baixados por `python -m zela.dados` |
| `processed/` | Tabelas derivadas dos dados reais e o modelo de NLP treinado | **Real** (derivado) | Sim |
| `sintetico/` | Textos de cidadãos para treinar e testar o classificador | **Sintético**, escrito pelo grupo | Sim |
| `runtime/` | Banco SQLite e e-mails gerados durante o uso | Gerado pela aplicação | Não |

## Fonte real

- **Conjunto:** Dados do SP156 - Solicitações
- **Publicador:** Prefeitura de São Paulo, Portal de Dados Abertos (https://dados.prefeitura.sp.gov.br/dataset/dados-do-sp156)
- **Licença:** Creative Commons CC0 (domínio público)
- **Arquivos:** "Dados do SP156 - 2º TRI 2026" e "Dados do SP156 - 3º TRI 2026" (948 mil pedidos no total; 316.522 nas 12 categorias de zeladoria)
- **Acesso:** 17/11/2026

## Tratamento (`src/zela/dados.py`)

1. **Leitura robusta:** os dois trimestres vêm em formatos diferentes (UTF-8 com vírgula e data mês/dia; Windows-1252 com ponto e vírgula e data dia/mês). O formato de data é escolhido pelo que coloca as aberturas dentro do trimestre, e a leitura falha se menos de 99,9% caírem lá. Assim, "01/04" nunca é lido como 4 de janeiro em silêncio.
2. **Filtro por serviço oficial:** cada uma das 12 categorias agrupa serviços oficiais (`src/zela/categorias.py`).
3. **Prazo:** dias entre abertura e finalização, só de pedidos finalizados do 2º trimestre. O 3º trimestre ainda tem pedidos longos em aberto.
4. **Privacidade:** coordenadas arredondadas para 3 casas (~100 m); logradouro, número e CEP não são exportados.
5. **Qualidade:** valores que não são subprefeituras ("Prefeitura Regional nao encontrada", "Departamento de Estradas de Rodagem", "Superintendencia das Usinas de Asfalto") são excluídos da grade de subprefeituras.

| Arquivo em `processed/` | O que é |
|---|---|
| `categorias_sp156.csv` | Volume, % ainda aberto, mediana e p80 de dias, órgão mais frequente por categoria |
| `roteamento_sp156.csv` | Órgão que mais atendeu cada categoria em cada subprefeitura |
| `grade_subprefeituras.csv` | Subprefeitura predominante em cada célula de ~100 m (todos os pedidos geolocalizados) |
| `duplicidade_sp156.csv` | Pedidos que repetem um anterior aberto no mesmo ponto (~11 m) |
| `mapa_sp156.csv` | Amostra de 400 pedidos por categoria para o mapa (semente fixa) |
| `modelo_nlp.joblib` | Classificador treinado com `sintetico/mensagens_treino.csv` |

## Dados sintéticos (`src/zela/sintetico.py`)

A Prefeitura **não publica o texto escrito pelo cidadão**. Por isso, os textos são escritos pelo grupo a partir de frases por categoria, com ruído de escrita informal (sem acento, abreviações, letras trocadas, caixa alta) e, em 15% dos casos, dados pessoais **inventados** para testar a anonimização.

- `mensagens_treino.csv` (1.800): frases do grupo A e combinações de vocabulário, parte dele tirada dos nomes oficiais dos serviços.
- `mensagens_teste.csv` (600): frases do grupo B, que **nunca aparecem no treino**.
- `mensagens_escritas_a_mao.csv` (36): mensagens coloquiais escritas antes de qualquer resultado. Três foram recategorizadas quando "Fiação e Postes" virou "Calçada, guia, fiação solta ou poste"; uma frase sobre lâmpada queimada foi trocada porque iluminação pública não está na base.

**Limitação:** todos os textos foram escritos pelo mesmo grupo. O desempenho com relatos reais pode ser diferente.
