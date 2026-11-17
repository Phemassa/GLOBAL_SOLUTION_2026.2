"""Categorias de zeladoria atendidas pelo ZelaCidade.

Cada categoria agrupa SERVIÇOS oficiais do SP156 (Prefeitura de São Paulo). Usar o serviço,
e não só o assunto, foi necessário: o assunto "Sinalização e Circulação" é 70% isenção de
rodízio (não é zeladoria), e "Fiação e Postes" é quase todo manutenção de calçada.
Iluminação pública não está nos dados abertos do SP156 e por isso ficou de fora.
"""

CATEGORIAS = {
    "buraco": {"rotulo": "Buraco ou asfalto danificado", "servicos": [
        "Tapa-buraco", "Tapa-buraco em faixa exclusiva ou corredor de ônibus", "Reparos em Pontes, Viadutos e Túneis"]},
    "entulho": {"rotulo": "Entulho ou descarte irregular", "servicos": [
        "Entulho e grandes objetos em via pública - solicitar remoção",
        "Denunciar descarte irregular de entulho e outros resíduos em área pública",
        "Denunciar caçamba irregular de entulho de construção"]},
    "arvore": {"rotulo": "Árvore em via pública (poda, queda, risco)", "servicos": [
        "Árvore – Solicitar avaliação em calçadas e praças para fins de poda ou remoção"]},
    "calcada": {"rotulo": "Calçada, guia, fiação solta ou poste", "servicos": [
        "Guias, sarjetas e sarjetões - solicitar manutenção", "Calçada pública - solicitar manutenção",
        "Acessibilidade - solicitar avaliação de obstáculo na calçada",
        "Calçada particular - denunciar calçada danificada ou inexistente",
        "Denunciar Fiação solta na calçada", "Denunciar Poste em mau estado"]},
    "drenagem": {"rotulo": "Boca de lobo ou alagamento", "servicos": [
        "Solicitar limpeza de bueiros, boca de lobo e poços de visita",
        "Reformar galerias de águas de chuvas (pluviais)", "Microdrenagem"]},
    "varricao": {"rotulo": "Rua suja ou falta de varrição", "servicos": [
        "Fazer reclamação de falta de varrição", "Sacos de varrição - Fazer reclamação de falta de remoção",
        "Solicitar limpeza da via pública após enchentes ou eventos",
        "Solicitar lavagem de calçadões e locais públicos", "Fazer reclamação de falta de lavagem de calçadões"]},
    "coleta": {"rotulo": "Coleta de lixo não passou", "servicos": [
        "Reclamar sobre coleta de lixo domiciliar"]},
    "capinacao": {"rotulo": "Mato alto em área pública", "servicos": [
        "Guias e sarjetas - Solicitar capinação", "Praça e canteiro central - solicitar roçada"]},
    "barulho": {"rotulo": "Barulho excessivo", "servicos": [
        "Reclamação de poluição sonora - PSIU"]},
    "veiculo": {"rotulo": "Veículo abandonado", "servicos": [
        "Solicitar remoção de veículo/carcaça abandonado na via pública"]},
    "sinalizacao": {"rotulo": "Sinalização, placa ou semáforo", "servicos": [
        "Sinalização horizontal apagada (pintura de solo) – Solicitar repintura", "Manutenção de placas de trânsito",
        "Semáforo de veículos e pedestres - Sugerir ajuste de tempo", "Manutenção de placa com nome de rua",
        "Instalação de placa com nome de rua", "Travessia de pedestres - Solicitar avaliação", "Manutenção de semáforos"]},
    "pragas": {"rotulo": "Ratos, insetos ou animais que transmitem doenças", "servicos": [
        "Ratos - Solicitar vistoria em local infestado", "Abelhas e Vespas - Solicitar vistoria em ninhos",
        "Morcegos - Reclamar sobre local com morcegos", "Escorpião - Solicitar vistoria de local com escorpiões",
        "Pombos - Solicitar vistoria em local infestado", "Pernilongo/Mosquito - Solicitar vistoria em local infestado"]},
}

SERVICO_PARA_CATEGORIA = {s: chave for chave, c in CATEGORIAS.items() for s in c["servicos"]}
