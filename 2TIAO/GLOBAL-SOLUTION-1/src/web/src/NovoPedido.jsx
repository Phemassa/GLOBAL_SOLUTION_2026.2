import { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, useMapEvents } from "react-leaflet";
import { api } from "./api.js";

const CENTRO_SP = [-23.5505, -46.6333];

function SeletorDeLocal({ local, aoEscolher }) {
  useMapEvents({ click: (e) => aoEscolher([e.latlng.lat, e.latlng.lng]) });
  return local ? <CircleMarker center={local} radius={10} pathOptions={{ color: "#c2410c", fillOpacity: 0.8 }} /> : null;
}

export default function NovoPedido({ aoCriar, irAcompanhar }) {
  const [texto, setTexto] = useState("");
  const [previa, setPrevia] = useState(null);
  const [local, setLocal] = useState(null);
  const [email, setEmail] = useState("");
  const [consentimento, setConsentimento] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState(null);
  const espera = useRef();

  // Prévia da classificação enquanto a pessoa escreve (nada é gravado nessa etapa).
  useEffect(() => {
    clearTimeout(espera.current);
    if (texto.trim().length < 12) { setPrevia(null); return; }
    espera.current = setTimeout(() => api.classificar(texto).then(setPrevia).catch(() => setPrevia(null)), 450);
    return () => clearTimeout(espera.current);
  }, [texto]);

  function usarMinhaLocalizacao() {
    navigator.geolocation?.getCurrentPosition(
      (p) => setLocal([p.coords.latitude, p.coords.longitude]),
      () => setErro("Não foi possível obter sua localização. Toque no mapa para marcar o local."));
  }

  async function enviar(e) {
    e.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      const r = await api.criar({ texto, lat: local?.[0] ?? null, lon: local?.[1] ?? null,
        email: email || null, consentimento: Boolean(email) && consentimento });
      setResultado(r);
      aoCriar(r.protocolo);
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setEnviando(false);
    }
  }

  if (resultado) {
    return (
      <section className="cartao destaque" data-testid="resultado-pedido">
        {resultado.agrupado ? (
          <>
            <h2>Esse problema já foi relatado aqui</h2>
            <p>Somamos o seu relato ao pedido existente. Agora são <strong>{resultado.apoios} relatos</strong> do mesmo problema,
              o que aumenta a prioridade sem abrir um chamado duplicado.</p>
          </>
        ) : (
          <h2>Pedido registrado</h2>
        )}
        <p className="protocolo">Protocolo <strong data-testid="protocolo">{resultado.protocolo}</strong></p>
        <dl className="resumo">
          <dt>Categoria</dt><dd>{resultado.rotulo}</dd>
          <dt>Situação</dt><dd>{resultado.status}</dd>
          <dt>Responsável</dt><dd>{resultado.orgao}{resultado.subprefeitura ? ` (subprefeitura ${resultado.subprefeitura})` : ""}</dd>
          <dt>Prazo típico</dt><dd>metade dos pedidos assim é resolvida em até {resultado.prazo_mediana} dias; 80% em até {resultado.prazo_p80} dias</dd>
        </dl>
        {resultado.status === "Triagem humana" && (
          <p className="aviso">Não tivemos certeza da categoria; um atendente vai conferir antes de encaminhar.</p>
        )}
        <div className="acoes">
          <button onClick={() => irAcompanhar(resultado.protocolo)}>Acompanhar este pedido</button>
          <button className="secundario" onClick={() => { setResultado(null); setTexto(""); setLocal(null); }}>Fazer outro pedido</button>
        </div>
      </section>
    );
  }

  return (
    <form className="grade-2" onSubmit={enviar}>
      <section className="cartao">
        <h2>O que está acontecendo?</h2>
        <label htmlFor="texto">Descreva o problema com as suas palavras</label>
        <textarea id="texto" data-testid="texto" rows={5} value={texto} onChange={(e) => setTexto(e.target.value)}
          placeholder="Ex.: tem um buraco enorme na frente da escola e os carros desviam pela contramão" required minLength={10} />
        {previa && (
          <div className="previa" data-testid="previa" aria-live="polite">
            <p>Entendemos: <strong>{previa.rotulo}</strong> ({Math.round(previa.confianca * 100)}% de confiança)</p>
            {previa.triagem_humana && <p className="aviso">Com essa descrição, um atendente vai confirmar a categoria.</p>}
            {previa.urgencia !== "normal" && <p>Urgência <strong>{previa.urgencia}</strong> pelos sinais de risco descritos.</p>}
            <p className="pequeno">Prazo típico real (SP156): {previa.prazo.mediana_dias} dias na metade dos casos.</p>
            {previa.texto_anonimizado !== texto && (
              <p className="pequeno">Seus dados pessoais no texto serão ocultados: “{previa.texto_anonimizado}”</p>
            )}
          </div>
        )}
        <label htmlFor="email">E-mail para receber atualizações (opcional)</label>
        <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="voce@exemplo.com" />
        {email && (
          <label className="caixa">
            <input type="checkbox" checked={consentimento} onChange={(e) => setConsentimento(e.target.checked)} />
            Autorizo o uso do e-mail só para avisos deste pedido. Ele é apagado quando o pedido termina.
          </label>
        )}
      </section>
      <section className="cartao">
        <h2>Onde?</h2>
        <p className="pequeno">Toque no mapa para marcar o local do problema.</p>
        <div className="mapa" data-testid="mapa-pedido">
          <MapContainer center={CENTRO_SP} zoom={12} style={{ height: "100%" }}>
            <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <SeletorDeLocal local={local} aoEscolher={setLocal} />
          </MapContainer>
        </div>
        <div className="acoes">
          <button type="button" className="secundario" onClick={usarMinhaLocalizacao}>Usar minha localização</button>
          {local && <span className="pequeno" data-testid="local">Local: {local[0].toFixed(4)}, {local[1].toFixed(4)}</span>}
        </div>
        {erro && <p className="erro" role="alert">{erro}</p>}
        <button type="submit" className="enviar" disabled={enviando || texto.trim().length < 10} data-testid="enviar">
          {enviando ? "Enviando..." : "Enviar pedido"}
        </button>
      </section>
    </form>
  );
}
