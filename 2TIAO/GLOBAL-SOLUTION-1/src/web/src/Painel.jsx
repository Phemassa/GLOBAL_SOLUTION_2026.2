import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip as Dica, XAxis, YAxis } from "recharts";
import { api } from "./api.js";

const STATUS = ["Recebido", "Triagem humana", "Encaminhado", "Em atendimento", "Finalizado", "Cancelado"];
const COR_URGENCIA = { alta: "#b91c1c", media: "#c2410c", normal: "#475569" };

function Indicador({ titulo, valor, detalhe }) {
  return (
    <div className="indicador">
      <span>{titulo}</span>
      <strong>{valor ?? "–"}</strong>
      {detalhe && <small>{detalhe}</small>}
    </div>
  );
}

export default function Painel() {
  const [token, setToken] = useState("zela-demo");
  const [fila, setFila] = useState([]);
  const [kpi, setKpi] = useState(null);
  const [referencia, setReferencia] = useState([]);
  const [pontos, setPontos] = useState([]);
  const [mensagem, setMensagem] = useState("");
  const [erro, setErro] = useState("");

  async function recarregar() {
    setErro("");
    try {
      const [f, k] = await Promise.all([api.listar(token), api.indicadores()]);
      setFila(f);
      setKpi(k);
    } catch (falha) {
      setErro(falha.message);
    }
  }

  useEffect(() => {
    recarregar();
    api.referencia().then(setReferencia);
    api.mapa().then(setPontos);
  }, []);

  async function mudar(protocolo, mudanca) {
    await api.atualizar(token, protocolo, mudanca);
    recarregar();
  }

  async function robo(dias = 0) {
    const r = await api.rodarRobo(token, dias);
    setMensagem(`Robô: ${r.encaminhados} encaminhado(s), ${r.escalados} escalado(s) por prazo, ` +
      `${r.avisos_cidadao} aviso(s) ao cidadão, ${r.contatos_apagados} e-mail(s) apagado(s).`);
    recarregar();
  }

  const rotulos = Object.fromEntries(referencia.map((r) => [r.categoria, r.rotulo]));
  const CURTO = { buraco: "Buraco", entulho: "Entulho", arvore: "Árvore", calcada: "Calçada", drenagem: "Drenagem", varricao: "Varrição",
    coleta: "Coleta", capinacao: "Mato alto", barulho: "Barulho", veiculo: "Veículo", sinalizacao: "Sinalização", pragas: "Pragas" };
  const prazos = referencia.map((r) => ({ nome: CURTO[r.categoria] || r.categoria, mediana: r.mediana_dias, p80: r.p80_dias }));

  return (
    <div className="painel">
      <section className="cartao linha">
        <label htmlFor="token">Token do gestor</label>
        <input id="token" value={token} onChange={(e) => setToken(e.target.value)} style={{ maxWidth: 160 }} />
        <button onClick={recarregar}>Atualizar</button>
        <button onClick={() => robo(0)} data-testid="rodar-robo">Rodar robô (RPA)</button>
        <button className="secundario" onClick={() => robo(30)} title="Só para demonstração">Avançar 30 dias (demo)</button>
      </section>
      {erro && <p className="erro" role="alert">{erro}</p>}
      {mensagem && <p className="sucesso" data-testid="mensagem-robo">{mensagem}</p>}

      {kpi && (
        <section className="indicadores" data-testid="indicadores">
          <Indicador titulo="Pedidos" valor={kpi.pedidos} />
          <Indicador titulo="Relatos agrupados" valor={kpi.relatos_agrupados} detalhe="chamados duplicados evitados" />
          <Indicador titulo="Em triagem humana" valor={kpi.por_status["Triagem humana"] || 0} />
          <Indicador titulo="Tempo médio" valor={kpi.tempo_medio_dias != null ? `${kpi.tempo_medio_dias} d` : null} detalhe="pedidos finalizados" />
          <Indicador titulo="No prazo" valor={kpi.pct_no_prazo != null ? `${kpi.pct_no_prazo}%` : null} detalhe="até o p80 real" />
          <Indicador titulo="Escalados" valor={kpi.escalados_por_prazo} detalhe="prazo vencido" />
        </section>
      )}

      <section className="cartao">
        <h2>Fila de atendimento</h2>
        <p className="pequeno">Ordenada por urgência e número de relatos.</p>
        <div className="tabela-rolagem">
          <table data-testid="fila">
            <thead><tr><th>Protocolo</th><th>Categoria</th><th>Relato</th><th>Urgência</th><th>Relatos</th><th>Responsável</th><th>Situação</th></tr></thead>
            <tbody>
              {fila.map((p) => (
                <tr key={p.protocolo} className={p.status === "Triagem humana" ? "linha-triagem" : ""}>
                  <td>{p.protocolo}{p.escalado_em && <span className="selo">prazo vencido</span>}</td>
                  <td>
                    {p.status === "Triagem humana" ? (
                      <>
                        <select aria-label={`Corrigir categoria de ${p.protocolo}`} value={p.categoria}
                          onChange={(e) => mudar(p.protocolo, { categoria: e.target.value })}>
                          {Object.entries(rotulos).map(([c, r]) => <option key={c} value={c}>{r}</option>)}
                        </select>
                        {/* Quando o modelo acertou mas com pouca confiança, o atendente só confirma. */}
                        <button className="confirmar" aria-label={`Confirmar categoria de ${p.protocolo}`}
                          onClick={() => mudar(p.protocolo, { status: "Recebido", nota: "Categoria confirmada pelo atendente" })}>
                          Confirmar
                        </button>
                      </>
                    ) : p.rotulo}
                    <small> {Math.round(p.confianca * 100)}%</small>
                  </td>
                  <td className="relato">{p.texto}</td>
                  <td style={{ color: COR_URGENCIA[p.urgencia], fontWeight: 600 }}>{p.urgencia}</td>
                  <td>{p.apoios}</td>
                  <td className="pequeno">{p.orgao}<br />{p.subprefeitura}</td>
                  <td>
                    <select aria-label={`Situação de ${p.protocolo}`} value={p.status} onChange={(e) => mudar(p.protocolo, { status: e.target.value })}>
                      {STATUS.map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
              {!fila.length && <tr><td colSpan={7}>Nenhum pedido ainda.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grade-2">
        <section className="cartao">
          <h2>Onde a cidade pede zeladoria</h2>
          <p className="pequeno">Amostra de {pontos.length} pedidos reais do SP156 (abr–set/2026), posição arredondada para ~100 m, e os pedidos desta demonstração.</p>
          <div className="mapa" data-testid="mapa-painel">
            <MapContainer center={[-23.6, -46.62]} zoom={10} style={{ height: "100%" }}>
              <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              {pontos.map((p, i) => (
                <CircleMarker key={i} center={[p.lat, p.lon]} radius={2} pathOptions={{ color: "#64748b", opacity: 0.5, fillOpacity: 0.3 }} />
              ))}
              {fila.filter((p) => p.lat).map((p) => (
                <CircleMarker key={p.protocolo} center={[p.lat, p.lon]} radius={8} pathOptions={{ color: COR_URGENCIA[p.urgencia], fillOpacity: 0.9 }}>
                  <Tooltip>{p.protocolo}: {p.rotulo}</Tooltip>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
        </section>
        <section className="cartao">
          <h2>Prazos reais por categoria (SP156)</h2>
          <p className="pequeno">Dias até a finalização, pedidos do 2º trimestre de 2026. É o prazo de referência usado pelo robô.</p>
          <div style={{ height: 460 }}>
            <ResponsiveContainer>
              <BarChart data={prazos} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" unit=" d" />
                <YAxis type="category" dataKey="nome" width={90} interval={0} />
                <Dica />
                <Legend />
                <Bar dataKey="mediana" name="Mediana" fill="#0f766e" />
                <Bar dataKey="p80" name="80% resolvidos até" fill="#94a3b8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
    </div>
  );
}
