// Chamadas à API REST do ZelaCidade.
async function pedir(caminho, opcoes = {}) {
  const resposta = await fetch(caminho, {
    ...opcoes,
    headers: { "Content-Type": "application/json", ...(opcoes.headers || {}) },
  });
  const corpo = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const detalhe = Array.isArray(corpo.detail) ? corpo.detail.map((d) => d.msg).join("; ") : corpo.detail;
    throw new Error(detalhe || `Erro ${resposta.status}`);
  }
  return corpo;
}

const gestor = (token) => ({ "X-Token": token });

export const api = {
  classificar: (texto) => pedir("/api/classificar", { method: "POST", body: JSON.stringify({ texto }) }),
  criar: (dados) => pedir("/api/solicitacoes", { method: "POST", body: JSON.stringify(dados) }),
  consultar: (protocolo) => pedir(`/api/solicitacoes/${encodeURIComponent(protocolo)}`),
  listar: (token) => pedir("/api/solicitacoes", { headers: gestor(token) }),
  atualizar: (token, protocolo, mudanca) =>
    pedir(`/api/solicitacoes/${protocolo}`, { method: "PATCH", headers: gestor(token), body: JSON.stringify(mudanca) }),
  rodarRobo: (token, avancarDias = 0) =>
    pedir(`/api/rpa/executar?avancar_dias=${avancarDias}`, { method: "POST", headers: gestor(token) }),
  indicadores: () => pedir("/api/indicadores"),
  referencia: () => pedir("/api/referencia"),
  mapa: () => pedir("/api/mapa"),
};
