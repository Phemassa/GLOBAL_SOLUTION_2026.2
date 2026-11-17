import { useState } from "react";
import NovoPedido from "./NovoPedido.jsx";
import Acompanhar from "./Acompanhar.jsx";
import Painel from "./Painel.jsx";

const ABAS = [
  { id: "pedido", titulo: "Fazer um pedido" },
  { id: "acompanhar", titulo: "Acompanhar" },
  { id: "painel", titulo: "Painel da prefeitura" },
];

export default function App() {
  const [aba, setAba] = useState("pedido");
  const [protocolo, setProtocolo] = useState("");

  return (
    <>
      <header className="topo">
        <div className="marca">
          <span className="logo" aria-hidden="true">◆</span>
          <div>
            <h1>ZelaCidade</h1>
            <p>Zeladoria urbana com IA: conte o problema do seu jeito, a gente encaminha.</p>
          </div>
        </div>
        <nav aria-label="Seções">
          {ABAS.map((a) => (
            <button key={a.id} className={aba === a.id ? "aba ativa" : "aba"} aria-current={aba === a.id}
              onClick={() => setAba(a.id)} data-testid={`aba-${a.id}`}>
              {a.titulo}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {aba === "pedido" && <NovoPedido aoCriar={(p) => setProtocolo(p)} irAcompanhar={(p) => { setProtocolo(p); setAba("acompanhar"); }} />}
        {aba === "acompanhar" && <Acompanhar protocoloInicial={protocolo} />}
        {aba === "painel" && <Painel />}
      </main>
      <footer>
        Projeto acadêmico (FIAP, Global Solution 2026.2). Volumes, prazos e órgãos vêm dos dados abertos do SP156;
        os pedidos desta demonstração são simulados.
      </footer>
    </>
  );
}
