# Roteiro do vídeo (até 5 minutos)

O arquivo [ZelaCidade_GrupoZion.mp4](ZelaCidade_GrupoZion.mp4) (2min49s) foi gerado por `src/demo/gerar_video.py`:

- **Slides** com dados e gráficos reais.
- **Demonstração** gravada no navegador enquanto a aplicação roda de verdade.
- **Narração** com voz neural sintética pt-BR (Microsoft Francisca). Se o grupo preferir narrar, use as falas abaixo; o enunciado pede que o nome do grupo e "QUERO CONCORRER" sejam ditos nos primeiros segundos.

**Publicação:** YouTube como **não listado**; o link vai no fim do PDF de entrega e no README.

| Tempo | Cena | Na tela | Fala |
|---|---|---|---|
| 0:00 | Abertura | Título e "Grupo Zion · QUERO CONCORRER" | Grupo Zion. Quero concorrer! Este é o ZelaCidade: zeladoria urbana com inteligência artificial, a nossa solução para o desafio CitizenTech. |
| 0:11 | Problema | Dados reais do SP156 e gráfico de volume e prazo | Buraco na rua, entulho na calçada, bueiro entupido. Pelos dados abertos da Prefeitura de São Paulo, o canal 156 recebeu mais de 316 mil pedidos de zeladoria em seis meses. Nesses mesmos dados, 18% dos pedidos repetem outro, no mesmo ponto, que ainda estava aberto. E o prazo varia de um dia, para entulho, a 35 dias, para veículo abandonado. |
| 0:36 | Cidadão | Digitação, prévia da categoria, mapa e envio | Na prática: o cidadão escreve do próprio jeito. Enquanto ele digita, o modelo de linguagem natural mostra a categoria que entendeu, com o grau de confiança, o prazo típico real e como o telefone vai ficar oculto. Ele marca o local no mapa e envia. O sistema descobre a subprefeitura e o órgão que de fato atende esse problema ali. |
| 0:57 | Agrupamento e triagem | Segundo relato agrupado; texto vago em triagem | Se outra pessoa relata o mesmo buraco, no mesmo lugar, o sistema não abre um novo chamado: soma o relato ao protocolo existente. E quando o texto é vago, o pedido vai para triagem humana, em vez de ser encaminhado no escuro. |
| 1:12 | Painel | Fila, robô RPA, confirmação de categoria, prazo vencido | No painel da prefeitura, a fila é ordenada por urgência e número de relatos. O robô de automação envia o ofício ao órgão responsável e avisa o cidadão. O atendente confirma ou corrige a categoria dos casos em dúvida. Simulando trinta dias, o robô escala os pedidos que passaram do prazo real da categoria. |
| 1:32 | Acompanhamento | Linha do tempo do protocolo | O cidadão acompanha tudo pelo protocolo, numa linha do tempo, sem nenhum dado pessoal exposto. Quando o pedido termina, o robô apaga o e-mail dele. |
| 1:43 | Integração | Lista das disciplinas | A solução integra as disciplinas do ano: processamento de linguagem natural para entender o relato; automação de processos com um robô; uma API REST em Python; a interface em React; e governança de dados, com anonimização, consentimento e retenção mínima, seguindo a LGPD. |
| 2:03 | Resultados | Números do modelo e matriz de confusão | Fomos honestos com os resultados. Como a prefeitura não publica o texto dos cidadãos, os relatos de treino são sintéticos. Em frases nunca vistas, o modelo acertou 69%, e o valor mínimo de confiança não garantiu os 90% esperados. Por isso ele funciona como triagem assistida, com revisão humana. Todo o fluxo foi testado de forma automatizada, inclusive no navegador. |
| 2:28 | ODS e impacto | ODS 11 e 16; indicadores | O projeto contribui com os ODS 11, cidades sustentáveis, e 16, instituições eficazes. Medimos o impacto pelos chamados duplicados evitados, pelos pedidos resolvidos no prazo e pelos atrasos escalados. O próximo passo é um piloto com relatos reais. Obrigado! |
