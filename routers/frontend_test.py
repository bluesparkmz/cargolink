"""
Pagina HTML simples para testar fluxos da API manualmente.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("", response_class=HTMLResponse)
def frontend_test():
    return HTMLResponse(
        """<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CargoLink API Test</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1020;
      --panel: #111827;
      --panel-2: #0f172a;
      --line: #263244;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --field: #050816;
      --accent: #38bdf8;
      --ok: #86efac;
      --err: #fca5a5;
      --warn: #fde68a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, sans-serif;
      font-size: 14px;
    }
    main { padding: 10px; margin-top: 60px; }
    h1 { font-size: 16px; margin: 0; line-height: 1; }
    h2 { font-size: 15px; margin: 0 0 8px; }
    h3 { font-size: 13px; margin: 0 0 6px; color: var(--accent); }
    a { color: var(--accent); }
    .topbar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 2;
      display: flex;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
      padding: 8px 10px;
      height: 60px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    .top-meta { display: flex; gap: 8px; flex-wrap: nowrap; align-items: center; color: var(--muted); overflow-x: auto; }
    .shell {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(360px, 42vw);
      gap: 10px;
      align-items: start;
    }
    .controls { display: grid; gap: 10px; }
    section, .output-panel {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      padding: 10px;
    }
    .output-panel {
      position: fixed;
      top: 60px;
      right: 10px;
      width: 42vw;
      max-width: calc(100vw - 380px);
      height: calc(100vh - 70px);
      max-height: calc(100vh - 70px);
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      padding: 10px;
    }
    form { display: grid; gap: 6px; margin: 0; }
    label { display: grid; gap: 3px; color: var(--muted); font-size: 12px; }
    input, select, textarea, button {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--field);
      color: var(--text);
      font: inherit;
      padding: 7px 8px;
    }
    textarea { min-height: 58px; resize: vertical; }
    button {
      cursor: pointer;
      background: #182235;
      font-weight: 700;
    }
    button:hover { border-color: var(--accent); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 6px; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 8px; }
    .row { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
    .row button { width: auto; }
    .mini { color: var(--muted); font-size: 12px; }
    code { color: var(--warn); }
    pre {
      margin: 0;
      overflow: auto;
      min-height: 240px;
      max-height: 100%;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-2);
      color: var(--text);
      font-size: 12px;
      line-height: 1.45;
    }
    dialog {
      width: min(720px, calc(100vw - 24px));
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      color: var(--text);
      padding: 12px;
      max-height: 90vh;
      overflow-y: auto;
    }
    dialog::backdrop { background: rgb(0 0 0 / 0.65); }
    .dialog-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .dialog-head button { width: auto; }
    .json-key { color: #7dd3fc; }
    .json-string { color: #86efac; }
    .json-number { color: #fde68a; }
    .json-bool { color: #f0abfc; }
    .json-null { color: #fca5a5; }
    @media (max-width: 980px) {
      .shell { grid-template-columns: 1fr; }
      .output-panel { position: relative; top: auto; right: auto; width: 100%; max-width: 100%; height: auto; max-height: 55vh; }
      pre { max-height: 55vh; }
    }
  </style>
</head>
<body>
<main>
  <header class="topbar">
    <div>
      <h1>CargoLink API Test</h1>
      <div class="mini">Estado: <strong id="statusMessage">Pronto</strong></div>
    </div>
    <div class="top-meta">
      <span>Token: <code id="tokenState">nao</code></span>
      <button type="button" onclick="document.getElementById('loginDialog').showModal()">Login</button>
      <button type="button" onclick="document.getElementById('registerDialog').showModal()">Cadastro</button>
      <button type="button" onclick="safeRun(authMe)">/auth/me</button>
      <button type="button" onclick="clearToken()">Limpar</button>
      <a href="/docs">OpenAPI</a>
      <a href="/documentation/proposals">Docs propostas</a>
    </div>
  </header>

  <div class="shell">
  <div class="controls">

  <dialog id="registerDialog">
    <div class="dialog-head">
      <h2>Cadastro</h2>
      <button type="button" onclick="document.getElementById('registerDialog').close()">Fechar</button>
    </div>
    <form onsubmit="registerUser(event)">
      <h3>POST /auth/register</h3>
      <div class="grid">
        <label>Nome <input name="name" value="Empresa Teste"></label>
        <label>Email <input name="email" value="empresa@test.com"></label>
        <label>Senha <input name="password" value="123456" type="password"></label>
        <label>Tipo
          <select name="user_type">
            <option value="empresa">empresa</option>
            <option value="cliente">cliente</option>
            <option value="motorista">motorista</option>
          </select>
        </label>
        <label>Telefone <input name="phone" value="840000001"></label>
        <label>Nome empresa <input name="company_name" value="Empresa Teste Lda"></label>
        <label>Cidade <input name="city" value="Maputo"></label>
        <label>Provincia <input name="state" value="Maputo"></label>
      </div>
      <button>Cadastrar e guardar token</button>
    </form>
  </dialog>

  <dialog id="loginDialog">
    <div class="dialog-head">
      <h2>Login</h2>
      <button type="button" onclick="document.getElementById('loginDialog').close()">Fechar</button>
    </div>
    <form onsubmit="loginUser(event)">
      <h3>POST /auth/login</h3>
      <label>Email <input name="email" value="empresa@test.com"></label>
      <label>Senha <input name="password" value="123456" type="password"></label>
      <button>Login e guardar token</button>
    </form>
  </dialog>

  <section>
    <h2>Auth</h2>
    <div class="row">
      <button type="button" onclick="document.getElementById('loginDialog').showModal()">Abrir login</button>
      <button type="button" onclick="document.getElementById('registerDialog').showModal()">Abrir cadastro</button>
      <button type="button" onclick="safeRun(authMe)">GET /auth/me</button>
    </div>
    <p class="mini">Use dialogs para trocar rapidamente entre contas cliente, empresa e motorista.</p>
  </section>

  <section>
    <h2>Veiculos</h2>
    <p class="mini">Empresa transportadora cadastra, edita e desativa camioes. Motorista apenas consulta o camiao atribuido e atualiza localizacao.</p>
    <div class="row">
      <button type="button" onclick="safeRun(() => api('/vehicles/me'))">GET /vehicles/me empresa/motorista</button>
      <button type="button" onclick="safeRun(() => api('/vehicles'))">GET /vehicles disponiveis</button>
      <button type="button" onclick="document.getElementById('vehicleDialog').showModal()">Cadastrar veiculo</button>
    </div>
  </section>

  <section>
    <h2>Cargas</h2>
    <div class="row">
      <button type="button" onclick="safeRun(() => api('/loads/types', { auth: false }))">GET /loads/types</button>
      <button type="button" onclick="safeRun(() => api('/loads/fill-types', { auth: false }))">GET /loads/fill-types</button>
      <button type="button" onclick="safeRun(() => api('/loads'))">GET /loads</button>
      <button type="button" onclick="safeRun(() => api('/loads/me'))">GET /loads/me</button>
      <button type="button" onclick="document.getElementById('loadDialog').showModal()">Publicar carga</button>
    </div>
  </section>

  <section>
    <h2>Propostas e negociacao</h2>
    <div class="row">
      <button type="button" onclick="safeRun(() => api('/proposals/me'))">GET /proposals/me</button>
      <button type="button" onclick="safeRun(() => api('/proposals/received'))">GET /proposals/received</button>
      <button type="button" onclick="document.getElementById('proposalDialog').showModal()">Enviar proposta</button>
      <button type="button" onclick="document.getElementById('counterOfferDialog').showModal()">Contraproposta</button>
      <button type="button" onclick="document.getElementById('proposalActionsDialog').showModal()">Acoes</button>
    </div>
  </section>

  <section>
    <h2>Request manual</h2>
    <button type="button" onclick="document.getElementById('manualRequestDialog').showModal()">Abrir request manual</button>
  </section>
  </div>

  <aside class="output-panel">
    <div class="row" style="justify-content: space-between;">
      <h2>Resultado</h2>
      <button type="button" onclick="write({ message: 'Resultado limpo' })">Limpar output</button>
    </div>
    <pre id="result"></pre>
  </aside>
  </div>

  <dialog id="vehicleDialog">
    <div class="dialog-head">
      <h2>Cadastrar veiculo</h2>
      <button type="button" onclick="document.getElementById('vehicleDialog').close()">Fechar</button>
    </div>
    <form onsubmit="createVehicle(event)">
      <h3>POST /vehicles empresa transportadora</h3>
      <div class="grid">
        <label>Matricula <input name="plate" value="ABC-123-MP"></label>
        <label>Motorista ID <input name="driver_id" type="number"></label>
        <label>Marca <input name="brand" value="Mercedes"></label>
        <label>Modelo <input name="model_name" value="Actros"></label>
        <label>Tipo <input name="vehicle_type" value="Camiao"></label>
        <label>Capacidade <input name="tonnage_capacity" type="number" step="0.01" value="30"></label>
        <label>Status <input name="status" value="disponivel"></label>
        <label>Lat <input name="current_lat" type="number" step="0.000001" value="-25.9692"></label>
        <label>Lng <input name="current_lng" type="number" step="0.000001" value="32.5732"></label>
        <label>Foto <input name="photo" type="file"></label>
      </div>
      <button>Cadastrar veiculo</button>
    </form>
  </dialog>

  <dialog id="loadDialog">
    <div class="dialog-head">
      <h2>Publicar carga</h2>
      <button type="button" onclick="document.getElementById('loadDialog').close()">Fechar</button>
    </div>
    <form onsubmit="createLoad(event)">
      <h3>POST /loads</h3>
      <div class="grid">
        <label>Tipo <input name="load_type" value="mercadoria_geral"></label>
        <label>Nome <input name="load_name" value="Carga teste"></label>
        <label>Origem <input name="origin" value="Maputo"></label>
        <label>Destino <input name="destination" value="Beira"></label>
        <label>Peso <input name="weight" type="number" value="150"></label>
        <label>Unidade <input name="weight_unit" value="ton"></label>
        <label>Volume <input name="volume" type="number" value="25"></label>
        <label>Valor <input name="value" type="number" value="500000"></label>
        <label>Negociavel
          <select name="negotiable">
            <option value="true">true</option>
            <option value="false">false</option>
          </select>
        </label>
        <label>Data saida <input name="departure_date" type="date" value="2026-06-15"></label>
        <label>Tipo enchimento <input name="load_fill" value="completa"></label>
        <label>Veiculo sugerido <input name="suggested_vehicle_type" value="Camiao"></label>
        <label>Origem lat <input name="origin_lat" type="number" step="0.000001" value="-25.9692"></label>
        <label>Origem lng <input name="origin_lng" type="number" step="0.000001" value="32.5732"></label>
        <label>Destino lat <input name="destination_lat" type="number" step="0.000001" value="-19.8432"></label>
        <label>Destino lng <input name="destination_lng" type="number" step="0.000001" value="34.8386"></label>
      </div>
      <label>Descricao <textarea name="description">Descricao de teste</textarea></label>
      <label>Instrucoes <textarea name="instructions">Carga fragil - manusear com cuidado</textarea></label>
      <label>Imagens <input name="images" type="file" multiple></label>
      <button>Publicar carga</button>
    </form>
  </dialog>

  <dialog id="proposalDialog">
    <div class="dialog-head">
      <h2>Enviar proposta</h2>
      <button type="button" onclick="document.getElementById('proposalDialog').close()">Fechar</button>
    </div>
    <form onsubmit="sendProposal(event)">
      <h3>POST /proposals/loads/{load_id}</h3>
      <label>Load ID <input name="load_id" type="number"></label>
      <label>Valor proposto <input name="proposed_value" type="number" step="0.01" value="28000"></label>
      <label>Motorista ID <input name="driver_id" type="number"></label>
      <label>Veiculo ID <input name="vehicle_id" type="number"></label>
      <label>Mensagem <textarea name="message">Proposta inicial</textarea></label>
      <button>Enviar proposta</button>
    </form>
  </dialog>

  <dialog id="counterOfferDialog">
    <div class="dialog-head">
      <h2>Contraproposta</h2>
      <button type="button" onclick="document.getElementById('counterOfferDialog').close()">Fechar</button>
    </div>
    <form onsubmit="counterOffer(event)">
      <h3>POST /proposals/{proposal_id}/negotiations</h3>
      <label>Proposal ID <input name="proposal_id" type="number"></label>
      <label>Valor <input name="amount" type="number" step="0.01" value="26000"></label>
      <label>Mensagem <textarea name="message">Contraproposta</textarea></label>
      <button>Criar contraproposta</button>
    </form>
  </dialog>

  <dialog id="proposalActionsDialog">
    <div class="dialog-head">
      <h2>Acoes de proposta</h2>
      <button type="button" onclick="document.getElementById('proposalActionsDialog').close()">Fechar</button>
    </div>
    <form onsubmit="proposalAction(event)">
      <label>Proposal ID <input name="proposal_id" type="number"></label>
      <label>Negotiation ID <input name="negotiation_id" type="number"></label>
      <div class="row">
        <button name="action" value="proposal-detail">Ver proposta</button>
        <button name="action" value="proposal-accept">Aceitar proposta</button>
        <button name="action" value="proposal-reject">Recusar proposta</button>
        <button name="action" value="negotiations">Ver negociacoes</button>
        <button name="action" value="negotiation-accept">Aceitar contraproposta</button>
        <button name="action" value="negotiation-reject">Recusar contraproposta</button>
      </div>
    </form>
  </dialog>

  <dialog id="manualRequestDialog">
    <div class="dialog-head">
      <h2>Request manual</h2>
      <button type="button" onclick="document.getElementById('manualRequestDialog').close()">Fechar</button>
    </div>
    <form onsubmit="manualRequest(event)">
      <div class="grid">
        <label>Metodo
          <select name="method">
            <option>GET</option>
            <option>POST</option>
            <option>PATCH</option>
            <option>DELETE</option>
          </select>
        </label>
        <label>Path <input name="path" value="/auth/me"></label>
      </div>
      <label>JSON body <textarea name="body">{}</textarea></label>
      <button>Enviar</button>
    </form>
  </dialog>
</main>

<script>
const tokenKey = "cargolink_test_token";
const result = document.getElementById("result");
const tokenState = document.getElementById("tokenState");
const statusMessage = document.getElementById("statusMessage");

function getToken() {
  return localStorage.getItem(tokenKey) || "";
}

function setToken(token) {
  localStorage.setItem(tokenKey, token);
  updateTokenState();
  setStatus("Token guardado com sucesso");
}

function clearToken() {
  localStorage.removeItem(tokenKey);
  updateTokenState();
  setStatus("Token removido");
  write({ message: "Token removido" });
}

function updateTokenState() {
  const token = getToken();
  tokenState.textContent = token ? "sim (" + token.slice(0, 18) + "...)" : "nao";
}

function write(data) {
  if (typeof data === "string") {
    result.textContent = data;
    return;
  }
  result.innerHTML = highlightJson(data);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function highlightJson(data) {
  const json = escapeHtml(JSON.stringify(data, null, 2));
  return json.replace(
    /("(?:\\\\.|[^"\\\\])*")(\\s*:)?|\\b(true|false)\\b|\\b(null)\\b|-?\\d+(?:\\.\\d+)?(?:e[+-]?\\d+)?/gi,
    (match, stringValue, colon, boolValue, nullValue) => {
      if (stringValue && colon) return '<span class="json-key">' + stringValue + '</span>' + colon;
      if (stringValue) return '<span class="json-string">' + stringValue + '</span>';
      if (boolValue) return '<span class="json-bool">' + boolValue + '</span>';
      if (nullValue) return '<span class="json-null">null</span>';
      return '<span class="json-number">' + match + '</span>';
    }
  );
}

function setStatus(message) {
  statusMessage.textContent = message;
}

async function safeRun(fn) {
  try {
    await fn();
  } catch (error) {
    setStatus(error.message || "Erro inesperado");
    write({ error: error.message || String(error) });
  }
}

function formObject(form) {
  const data = new FormData(form);
  const obj = {};
  for (const [key, value] of data.entries()) {
    if (value instanceof File) continue;
    if (value === "") continue;
    if (["proposed_value", "amount", "weight", "volume", "value", "origin_lat", "origin_lng", "destination_lat", "destination_lng", "tonnage_capacity", "current_lat", "current_lng"].includes(key)) {
      obj[key] = Number(value);
    } else if (["driver_id", "vehicle_id", "load_id", "proposal_id", "negotiation_id"].includes(key)) {
      obj[key] = Number(value);
    } else if (value === "true" || value === "false") {
      obj[key] = value === "true";
    } else {
      obj[key] = value;
    }
  }
  return obj;
}

async function api(path, options = {}) {
  const method = options.method || "GET";
  const headers = options.headers || {};
  const useAuth = options.auth !== false;
  setStatus("A enviar " + method + " " + path + "...");
  if (useAuth && getToken()) headers.Authorization = "Bearer " + getToken();
  if (options.json !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(path, {
    method,
    headers,
    body: options.json !== undefined ? JSON.stringify(options.json) : options.body,
  });
  const contentType = res.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await res.json() : await res.text();
  write({ status: res.status, ok: res.ok, body });
  if (!res.ok) {
    const detail = body && body.detail ? body.detail : "HTTP " + res.status;
    setStatus("Erro: " + detail);
    return body;
  }
  setStatus("Sucesso: " + method + " " + path);
  return body;
}

async function registerUser(event) {
  event.preventDefault();
  await safeRun(async () => {
    const body = formObject(event.target);
    if (body.user_type !== "empresa") delete body.company_name;
    const data = await api("/auth/register", { method: "POST", json: body, auth: false });
    if (data.access_token) {
      setToken(data.access_token);
      setStatus("Cadastro feito, token guardado");
      document.getElementById("registerDialog").close();
      await api("/auth/me");
      setStatus("Cadastro feito, token confirmado");
    }
  });
}

async function loginUser(event) {
  event.preventDefault();
  await safeRun(async () => {
    const data = await api("/auth/login", { method: "POST", json: formObject(event.target), auth: false });
    if (data.access_token) {
      setToken(data.access_token);
      setStatus("Login feito, token guardado");
      document.getElementById("loginDialog").close();
      await api("/auth/me");
      setStatus("Login feito, token confirmado");
    }
  });
}

async function authMe() {
  await api("/auth/me");
}

async function createVehicle(event) {
  event.preventDefault();
  await safeRun(async () => {
    const form = new FormData(event.target);
    for (const [key, value] of [...form.entries()]) {
      if (value === "" || (value instanceof File && !value.name)) form.delete(key);
    }
    await api("/vehicles", { method: "POST", body: form });
  });
}

async function createLoad(event) {
  event.preventDefault();
  await safeRun(async () => {
    const form = new FormData(event.target);
    for (const [key, value] of [...form.entries()]) {
      if (value === "" || (value instanceof File && !value.name)) form.delete(key);
    }
    await api("/loads", { method: "POST", body: form });
  });
}

async function sendProposal(event) {
  event.preventDefault();
  await safeRun(async () => {
    const data = formObject(event.target);
    const loadId = data.load_id;
    delete data.load_id;
    await api("/proposals/loads/" + loadId, { method: "POST", json: data });
  });
}

async function counterOffer(event) {
  event.preventDefault();
  await safeRun(async () => {
    const data = formObject(event.target);
    const proposalId = data.proposal_id;
    delete data.proposal_id;
    await api("/proposals/" + proposalId + "/negotiations", { method: "POST", json: data });
  });
}

async function proposalAction(event) {
  event.preventDefault();
  await safeRun(async () => {
    const action = event.submitter.value;
    const data = formObject(event.target);
    const proposalId = data.proposal_id;
    const negotiationId = data.negotiation_id;
    const map = {
      "proposal-detail": ["GET", "/proposals/" + proposalId],
      "proposal-accept": ["POST", "/proposals/" + proposalId + "/accept"],
      "proposal-reject": ["POST", "/proposals/" + proposalId + "/reject"],
      "negotiations": ["GET", "/proposals/" + proposalId + "/negotiations"],
      "negotiation-accept": ["POST", "/proposals/" + proposalId + "/negotiations/" + negotiationId + "/accept"],
      "negotiation-reject": ["POST", "/proposals/" + proposalId + "/negotiations/" + negotiationId + "/reject"],
    };
    const [method, path] = map[action];
    await api(path, { method });
  });
}

async function manualRequest(event) {
  event.preventDefault();
  await safeRun(async () => {
    const form = event.target;
    const method = form.elements.method.value;
    const path = form.elements.path.value;
    let body;
    if (method !== "GET" && method !== "DELETE") {
      body = JSON.parse(form.elements.body.value || "{}");
    }
    await api(path, { method, json: body });
  });
}

updateTokenState();
</script>
</body>
</html>"""
    )
