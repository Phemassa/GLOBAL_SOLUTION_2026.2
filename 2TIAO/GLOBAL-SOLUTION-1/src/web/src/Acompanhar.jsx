import { useEffect, useState } from "react";
import { api } from "./api.js";

const quando = (iso) => new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });

export default function Acompanhar({ protocoloInicial }) {
  const [protocolo, setProtocolo] = useState(protocoloInicial || "");
  const [pedido, setPedido] = useState(null);
  const [erro, setErro] = useState("");

  async function buscar(p = protocolo) {
    setErro("");
    try {
      setPedido(await api.consultar(p.trim()));
    } catch (falha) {
      setPedido(null);
      setErro(falha.message);
    }
  }

  useEffect(() => { if (protocoloInicial) buscar(protocoloInicial); }, [protocoloInicial]);

  return (
    <section className="cartao">
      <h2>Acompanhar pedido</h2>
      <form className="linha" onSubmit={(e) => { e.preventDefault(); buscar(); }}>
        <label htmlFor="protocolo" className="oculto">Protocolo</label>
        <input id="protocolo" value={protocolo} onChange={(e) => setProtocolo(e.target.value)} placeholder="ZC-20261117-ABC123" />
        <button type="submit">Consultar</button>
      </form>
      {erro && <p className="erro" role="alert">{erro}</p>}
      {pedido && (
        <div data-testid="detalhe-pedido">
          <p className="protocolo">{pedido.protocolo}: <strong>{pedido.status}</strong></p>
          <p>{pedido.rotulo} · {pedido.apoios} relato(s) · responsável {pedido.orgao}</p>
          <blockquote>{pedido.texto}</blockquote>
          <ol className="linha-do-tempo">
            {pedido.historico.filter((h) => h.evento !== "Cidadão avisado").map((h, i) => (
              <li key={i}><time>{quando(h.quando)}</time> <strong>{h.evento}</strong>{h.detalhe ? `: ${h.detalhe}` : ""}</li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
