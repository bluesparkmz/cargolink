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
    body { font-family: Arial, sans-serif; margin: 20px; }
    main { max-width: 1100px; margin: 0 auto; }
    section { border: 1px solid #999; padding: 12px; margin: 12px 0; }
    form { display: grid; gap: 8px; margin: 8px 0; }
    label { display: grid; gap: 4px; }
    input, select, textarea, button { font: inherit; padding: 6px; }
    textarea { min-height: 90px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 8px; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    pre { border: 1px solid #999; padding: 12px; overflow: auto; min-height: 120px; }
  </style>
</head>
<body>
<main>
  <h1>CargoLink API Test</h1>
  <p>Token guardado: <code id="tokenState">nao</code></p>
  <div class="row">
    <button type="button" onclick="authMe()">GET /auth/me</button>
    <button type="button" onclick="clearToken()">Limpar token</button>
    <a href="/docs">OpenAPI</a>
    <a href="/documentation/proposals">Docs propostas</a>
  </div>

  <section>
    <h2>Auth</h2>
    <div class="grid">
      <form onsubmit="registerUser(event)">
        <h3>POST /auth/register</h3>
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
        <button>Cadastrar e guardar token</button>
      </form>

      <form onsubmit="loginUser(event)">
        <h3>POST /auth/login</h3>
        <label>Email <input name="email" value="empresa@test.com"></label>
        <label>Senha <input name="password" value="123456" type="password"></label>
        <button>Login e guardar token</button>
      </form>
    </div>
  </section>

  <section>
    <h2>Veiculos</h2>
    <div class="row">
      <button type="button" onclick="api('/vehicles/me')">GET /vehicles/me</button>
      <button type="button" onclick="api('/vehicles')">GET /vehicles</button>
    </div>
    <form onsubmit="createVehicle(event)">
      <h3>POST /vehicles</h3>
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
  </section>

  <section>
    <h2>Cargas</h2>
    <div class="row">
      <button type="button" onclick="api('/loads/types', { auth: false })">GET /loads/types</button>
      <button type="button" onclick="api('/loads/fill-types', { auth: false })">GET /loads/fill-types</button>
      <button type="button" onclick="api('/loads')">GET /loads</button>
      <button type="button" onclick="api('/loads/me')">GET /loads/me</button>
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
  </section>

  <section>
    <h2>Propostas e negociacao</h2>
    <div class="grid">
      <form onsubmit="sendProposal(event)">
        <h3>POST /proposals/loads/{load_id}</h3>
        <label>Load ID <input name="load_id" type="number"></label>
        <label>Valor proposto <input name="proposed_value" type="number" step="0.01" value="28000"></label>
        <label>Motorista ID <input name="driver_id" type="number"></label>
        <label>Veiculo ID <input name="vehicle_id" type="number"></label>
        <label>Mensagem <textarea name="message">Proposta inicial</textarea></label>
        <button>Enviar proposta</button>
      </form>

      <form onsubmit="counterOffer(event)">
        <h3>POST /proposals/{proposal_id}/negotiations</h3>
        <label>Proposal ID <input name="proposal_id" type="number"></label>
        <label>Valor <input name="amount" type="number" step="0.01" value="26000"></label>
        <label>Mensagem <textarea name="message">Contraproposta</textarea></label>
        <button>Criar contraproposta</button>
      </form>

      <form onsubmit="proposalAction(event)">
        <h3>Acoes</h3>
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
    </div>
    <div class="row">
      <button type="button" onclick="api('/proposals/me')">GET /proposals/me</button>
      <button type="button" onclick="api('/proposals/received')">GET /proposals/received</button>
    </div>
  </section>

  <section>
    <h2>Request manual</h2>
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
  </section>

  <section>
    <h2>Resultado</h2>
    <pre id="result"></pre>
  </section>
</main>

<script>
const tokenKey = "cargolink_test_token";
const result = document.getElementById("result");
const tokenState = document.getElementById("tokenState");

function getToken() {
  return localStorage.getItem(tokenKey) || "";
}

function setToken(token) {
  localStorage.setItem(tokenKey, token);
  updateTokenState();
}

function clearToken() {
  localStorage.removeItem(tokenKey);
  updateTokenState();
  write({ message: "Token removido" });
}

function updateTokenState() {
  tokenState.textContent = getToken() ? "sim" : "nao";
}

function write(data) {
  result.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
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
  if (!res.ok) throw new Error("HTTP " + res.status);
  return body;
}

async function registerUser(event) {
  event.preventDefault();
  const body = formObject(event.target);
  if (body.user_type !== "empresa") delete body.company_name;
  const data = await api("/auth/register", { method: "POST", json: body, auth: false });
  if (data.access_token) setToken(data.access_token);
}

async function loginUser(event) {
  event.preventDefault();
  const data = await api("/auth/login", { method: "POST", json: formObject(event.target), auth: false });
  if (data.access_token) setToken(data.access_token);
}

async function authMe() {
  await api("/auth/me");
}

async function createVehicle(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  for (const [key, value] of [...form.entries()]) {
    if (value === "" || (value instanceof File && !value.name)) form.delete(key);
  }
  await api("/vehicles", { method: "POST", body: form });
}

async function createLoad(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  for (const [key, value] of [...form.entries()]) {
    if (value === "" || (value instanceof File && !value.name)) form.delete(key);
  }
  await api("/loads", { method: "POST", body: form });
}

async function sendProposal(event) {
  event.preventDefault();
  const data = formObject(event.target);
  const loadId = data.load_id;
  delete data.load_id;
  await api("/proposals/loads/" + loadId, { method: "POST", json: data });
}

async function counterOffer(event) {
  event.preventDefault();
  const data = formObject(event.target);
  const proposalId = data.proposal_id;
  delete data.proposal_id;
  await api("/proposals/" + proposalId + "/negotiations", { method: "POST", json: data });
}

async function proposalAction(event) {
  event.preventDefault();
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
}

async function manualRequest(event) {
  event.preventDefault();
  const form = event.target;
  const method = form.method.value;
  const path = form.path.value;
  let body;
  if (method !== "GET" && method !== "DELETE") {
    body = JSON.parse(form.body.value || "{}");
  }
  await api(path, { method, json: body });
}

updateTokenState();
</script>
</body>
</html>"""
    )
