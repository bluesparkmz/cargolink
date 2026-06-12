"""
Teste frontend para FLUXO COMPLETO:
1. Negociação de proposta (cliente, empresa, motorista)
2. Aceitar proposta (cria Trip)
3. Iniciar viagem com WebSocket e GPS em tempo real
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
  <title>CargoLink API Test - Completo</title>
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
      /* Métodos HTTP — tons suaves alinhados ao tema escuro */
      --method-get: #38bdf8;
      --method-get-bg: rgba(56, 189, 248, 0.14);
      --method-get-border: rgba(56, 189, 248, 0.45);
      --method-post: #6ee7b7;
      --method-post-bg: rgba(110, 231, 183, 0.12);
      --method-post-border: rgba(110, 231, 183, 0.38);
      --method-patch: #fbbf24;
      --method-patch-bg: rgba(251, 191, 36, 0.12);
      --method-patch-border: rgba(251, 191, 36, 0.45);
      --method-put: #fb923c;
      --method-put-bg: rgba(251, 146, 60, 0.12);
      --method-put-border: rgba(251, 146, 60, 0.4);
      --method-delete: #f87171;
      --method-delete-bg: rgba(248, 113, 113, 0.12);
      --method-delete-border: rgba(248, 113, 113, 0.45);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, sans-serif;
      font-size: 13px;
    }
    main { padding: 10px; margin-top: 60px; }
    h1 { font-size: 16px; margin: 0; line-height: 1; }
    h2 { font-size: 14px; margin: 8px 0 6px; font-weight: bold; color: var(--accent); border-bottom: 1px solid var(--line); padding-bottom: 4px; }
    h3 { font-size: 12px; margin: 0 0 4px; color: var(--muted); }
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
    .top-meta { display: flex; gap: 6px; flex-wrap: nowrap; align-items: center; color: var(--muted); overflow-x: auto; font-size: 12px; }
    .shell {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(320px, 38vw);
      gap: 8px;
      align-items: start;
    }
    .controls { display: grid; gap: 8px; }
    section, .output-panel {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 6px;
      padding: 8px;
    }
    .output-panel {
      position: fixed;
      top: 60px;
      right: 10px;
      width: 38vw;
      max-width: calc(100vw - 350px);
      height: calc(100vh - 70px);
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }
    form { display: grid; gap: 4px; margin: 0; }
    label { display: grid; gap: 2px; color: var(--muted); font-size: 11px; }
    input, select, textarea, button {
      border: 1px solid var(--line);
      border-radius: 4px;
      background: var(--field);
      color: var(--text);
      font: inherit;
      padding: 5px 6px;
    }
    input, select, textarea { width: 100%; }
    textarea { min-height: 50px; resize: vertical; }
    button {
      cursor: pointer;
      background: #182235;
      font-weight: 600;
      width: auto;
      padding: 6px 10px;
      border-left-width: 3px;
      transition: background 0.15s, border-color 0.15s, color 0.15s;
    }
    button:not([class*="method-"]):hover { border-color: var(--accent); }
    button.method-get {
      color: #e0f2fe;
      background: var(--method-get-bg);
      border-color: var(--method-get-border);
      border-left-color: var(--method-get);
    }
    button.method-get:hover {
      background: rgba(56, 189, 248, 0.24);
      border-color: var(--method-get);
    }
    button.method-post {
      color: #d1fae5;
      background: var(--method-post-bg);
      border-color: var(--method-post-border);
      border-left-color: var(--method-post);
    }
    button.method-post:hover {
      background: rgba(110, 231, 183, 0.2);
      border-color: var(--method-post);
    }
    button.method-patch {
      color: #fef3c7;
      background: var(--method-patch-bg);
      border-color: var(--method-patch-border);
      border-left-color: var(--method-patch);
    }
    button.method-patch:hover {
      background: rgba(251, 191, 36, 0.22);
      border-color: var(--method-patch);
    }
    button.method-put {
      color: #ffedd5;
      background: var(--method-put-bg);
      border-color: var(--method-put-border);
      border-left-color: var(--method-put);
    }
    button.method-put:hover {
      background: rgba(251, 146, 60, 0.22);
      border-color: var(--method-put);
    }
    button.method-delete {
      color: #fee2e2;
      background: var(--method-delete-bg);
      border-color: var(--method-delete-border);
      border-left-color: var(--method-delete);
    }
    button.method-delete:hover {
      background: rgba(248, 113, 113, 0.22);
      border-color: var(--method-delete);
    }
    select.method-get, select.method-post, select.method-patch, select.method-delete, select.method-put {
      font-weight: 600;
    }
    select.method-get { border-left: 3px solid var(--method-get); color: #bae6fd; }
    select.method-post { border-left: 3px solid var(--method-post); color: #a7f3d0; }
    select.method-patch { border-left: 3px solid var(--method-patch); color: #fde68a; }
    select.method-put { border-left: 3px solid var(--method-put); color: #fed7aa; }
    select.method-delete { border-left: 3px solid var(--method-delete); color: #fecaca; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 4px; }
    .row { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
    .row button { width: auto; }
    .mini { color: var(--muted); font-size: 11px; margin: 2px 0; }
    .row-compact { display: flex; gap: 4px; flex-wrap: wrap; }
    .row-compact button { padding: 4px 8px; font-size: 11px; }
    .workflow {
      margin: 6px 0 8px;
      padding: 8px 10px;
      border: 1px dashed var(--method-post-border);
      border-radius: 6px;
      background: var(--method-post-bg);
    }
    .workflow-title {
      display: block;
      font-size: 12px;
      font-weight: 700;
      color: var(--method-post);
      margin-bottom: 4px;
    }
    .workflow ol {
      margin: 0 0 8px 18px;
      padding: 0;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.5;
    }
    .workflow .row-compact button.btn-action {
      font-size: 12px;
      padding: 8px 14px;
    }
    code { color: var(--warn); font-size: 11px; }
    pre {
      margin: 0;
      overflow: auto;
      min-height: 200px;
      max-height: 100%;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: var(--panel-2);
      font-size: 11px;
      line-height: 1.4;
    }
    /* WebSocket Styles */
    .ws-container {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 350px;
      gap: 8px;
      margin-top: 10px;
    }
    .ws-chat-panel {
      border: 2px solid #6ee7b7;
      border-radius: 6px;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr) auto;
      height: 400px;
      background: var(--panel);
    }
    .ws-chat-header {
      padding: 8px;
      border-bottom: 1px solid var(--line);
      color: #6ee7b7;
      font-weight: bold;
      font-size: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .ws-status-badge {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #fca5a5;
      margin-right: 4px;
    }
    .ws-status-badge.connected {
      background: #86efac;
    }
    .ws-messages {
      overflow-y: auto;
      padding: 8px;
      font-size: 11px;
      line-height: 1.4;
    }
    .ws-message {
      margin-bottom: 6px;
      padding: 4px 6px;
      background: var(--panel-2);
      border-left: 2px solid #38bdf8;
      border-radius: 2px;
      word-wrap: break-word;
    }
    .ws-message.error {
      border-left-color: #fca5a5;
      color: #fca5a5;
    }
    .ws-message.success {
      border-left-color: #86efac;
      color: #86efac;
    }
    .ws-message.location {
      border-left-color: #fbbf24;
      color: #fde68a;
    }
    .ws-message.chat {
      border-left-color: #6ee7b7;
      color: #d1fae5;
    }
    .ws-message-time {
      font-size: 9px;
      color: var(--muted);
      margin-right: 4px;
    }
    .ws-input-area {
      border-top: 1px solid var(--line);
      padding: 6px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 4px;
    }
    .ws-input-area input {
      padding: 4px 6px;
      font-size: 11px;
    }
    .ws-input-area button {
      padding: 4px 8px;
      font-size: 10px;
      width: auto;
    }
    .gps-logs {
      border: 2px solid #fbbf24;
      border-radius: 6px;
      padding: 8px;
      background: var(--panel);
      max-height: 400px;
      overflow-y: auto;
      font-size: 10px;
    }
    .gps-log-entry {
      margin-bottom: 6px;
      padding: 4px 6px;
      background: var(--panel-2);
      border-left: 2px solid #fbbf24;
      border-radius: 2px;
      font-family: monospace;
    }
    dialog {
      width: min(800px, calc(100vw - 20px));
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--text);
      padding: 10px;
      max-height: 90vh;
      overflow-y: auto;
    }
    dialog::backdrop { background: rgb(0 0 0 / 0.7); }
    .dialog-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .dialog-head h2 { margin: 0; border: none; padding: 0; }
    .dialog-head button { width: auto; padding: 4px 8px; }
    .json-key { color: #7dd3fc; }
    .json-string { color: #86efac; }
    .json-number { color: #fde68a; }
    .json-bool { color: #f0abfc; }
    .json-null { color: #fca5a5; }
    .section-group { margin-bottom: 6px; }
    @media (max-width: 1200px) {
      .shell { grid-template-columns: 1fr; }
      .output-panel { position: relative; top: auto; right: auto; width: 100%; max-width: 100%; height: 45vh; margin-top: 8px; }
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
      <button onclick="document.getElementById('loginDialog').showModal()">Login</button>
      <button onclick="document.getElementById('registerDialog').showModal()">Cadastro</button>
      <button onclick="safeRun(authMe)">/auth/me</button>
      <button onclick="clearToken()">Limpar</button>
      <a href="/docs">OpenAPI</a>
    </div>
  </header>

  <div class="shell">
  <div class="controls">

  <!-- DIALOGS -->
  <dialog id="registerDialog">
    <div class="dialog-head">
      <h2>Cadastro</h2>
      <button onclick="document.getElementById('registerDialog').close()">✕</button>
    </div>
    <form onsubmit="registerUser(event)">
      <div class="grid">
        <label>Nome <input name="name" value="Empresa Teste"></label>
        <label>Email <input name="email" value=""></label>
        <label>Senha <input name="password" value="" type="password"></label>
        <label>Telefone <input name="phone" value=""></label>
      </div>
      <button>Cadastrar</button>
    </form>
  </dialog>

  <dialog id="loginDialog">
    <div class="dialog-head">
      <h2>Login</h2>
      <button onclick="document.getElementById('loginDialog').close()">✕</button>
    </div>
    <form onsubmit="loginUser(event)">
      <label>Email <input name="email" value="empresa@test.com"></label>
      <label>Senha <input name="password" value="123456" type="password"></label>
      <button>Login</button>
    </form>
  </dialog>

  <!-- USERS DIALOGS -->
  <dialog id="userUpdateDialog">
    <div class="dialog-head">
      <h2>Atualizar Utilizador</h2>
      <button onclick="document.getElementById('userUpdateDialog').close()">✕</button>
    </div>
    <form onsubmit="updateUser(event)">
      <label>Nome <input name="name" value=""></label>
      <label>Telefone <input name="phone" value=""></label>
      <button>Atualizar</button>
    </form>
  </dialog>

  <dialog id="passwordChangeDialog">
    <div class="dialog-head">
      <h2>Alterar Senha</h2>
      <button onclick="document.getElementById('passwordChangeDialog').close()">✕</button>
    </div>
    <form onsubmit="changePassword(event)">
      <label>Senha Atual <input name="old_password" type="password"></label>
      <label>Nova Senha <input name="new_password" type="password"></label>
      <label>Confirmar <input name="confirm_password" type="password"></label>
      <button>Alterar</button>
    </form>
  </dialog>

  <!-- VEHICLES DIALOGS -->
  <dialog id="vehicleCreateDialog">
    <div class="dialog-head">
      <h2>Criar Veiculo</h2>
      <button onclick="document.getElementById('vehicleCreateDialog').close()">✕</button>
    </div>
    <form onsubmit="createVehicle(event)">
      <div class="grid">
        <label>Matricula <input name="plate" value="ABC-123-MP"></label>
        <label>Email motorista <input name="driver_email" type="email" placeholder="opcional — da frota"></label>
        <label>Marca <input name="brand" value="Mercedes"></label>
        <label>Modelo <input name="model_name" value="Actros"></label>
        <label>Tipo <input name="vehicle_type" value="Camiao"></label>
        <label>Capacidade (ton) <input name="tonnage_capacity" type="number" step="0.1" value="30"></label>
        <label>Status <input name="status" value="disponivel"></label>
        <label>Lat <input name="current_lat" type="number" step="0.000001" value="-25.9692"></label>
        <label>Lng <input name="current_lng" type="number" step="0.000001" value="32.5732"></label>
      </div>
      <button>Criar</button>
    </form>
  </dialog>

  <dialog id="vehicleUpdateDialog">
    <div class="dialog-head">
      <h2>Editar Veiculo</h2>
      <button onclick="document.getElementById('vehicleUpdateDialog').close()">✕</button>
    </div>
    <form onsubmit="updateVehicle(event)">
      <label>Vehicle ID <input id="vehicleId" name="vehicle_id" type="number" readonly></label>
      <div class="grid">
        <label>Email motorista <input name="driver_email" type="email" placeholder="vazio = nao alterar"></label>
        <label>Marca <input name="brand" value=""></label>
        <label>Modelo <input name="model_name" value=""></label>
        <label>Status <input name="status" value=""></label>
        <label>Capacidade (ton) <input name="tonnage_capacity" type="number" step="0.1"></label>
      </div>
      <button>Atualizar</button>
    </form>
  </dialog>

  <dialog id="companyAttachDriverDialog">
    <div class="dialog-head">
      <h2>Associar Motorista a Empresa</h2>
      <button onclick="document.getElementById('companyAttachDriverDialog').close()">✕</button>
    </div>
    <form onsubmit="attachCompanyDriver(event)">
      <p class="mini">Email de login do motorista (conta tipo motorista). So quem conhece o email pode associar.</p>
      <label>Email do motorista <input name="email" type="email" required placeholder="motorista@email.com"></label>
      <button>Associar</button>
    </form>
  </dialog>

  <dialog id="vehicleAssignDriverDialog">
    <div class="dialog-head">
      <h2>Atribuir Motorista ao Camiao</h2>
      <button onclick="document.getElementById('vehicleAssignDriverDialog').close()">✕</button>
    </div>
    <form onsubmit="assignVehicleDriver(event)">
      <p class="mini">Motorista deve pertencer a sua empresa (POST /companies/me/drivers antes). Camiao deve ser da empresa (GET /vehicles/me).</p>
      <label>Vehicle ID <input name="vehicle_id" type="number" required></label>
      <label>Email do motorista <input name="driver_email" type="email" required placeholder="motorista@email.com"></label>
      <button>Atribuir</button>
    </form>
  </dialog>

  <dialog id="vehicleLocationDialog">
    <div class="dialog-head">
      <h2>Atualizar Localizacao</h2>
      <button onclick="document.getElementById('vehicleLocationDialog').close()">✕</button>
    </div>
    <form onsubmit="updateVehicleLocation(event)">
      <label>Vehicle ID <input id="vehicleLocId" name="vehicle_id" type="number"></label>
      <label>Latitude <input name="current_lat" type="number" step="0.000001" value="-25.9692"></label>
      <label>Longitude <input name="current_lng" type="number" step="0.000001" value="32.5732"></label>
      <button>Atualizar</button>
    </form>
  </dialog>

  <!-- LOADS DIALOGS -->
  <dialog id="loadCreateDialog">
    <div class="dialog-head">
      <h2>Publicar Carga</h2>
      <button onclick="document.getElementById('loadCreateDialog').close()">✕</button>
    </div>
    <form onsubmit="createLoad(event)">
      <div class="grid">
        <label>Tipo <input name="load_type" value="mercadoria_geral"></label>
        <label>Nome <input name="load_name" value="Carga teste"></label>
        <label>Origem <input name="origin" value="Maputo"></label>
        <label>Destino <input name="destination" value="Beira"></label>
        <label>Peso (ton) <input name="weight" type="number" value="150"></label>
        <label>Volume (m³) <input name="volume" type="number" value="25"></label>
        <label>Valor <input name="value" type="number" value="500000"></label>
        <label>Negociavel <select name="negotiable">
          <option value="true">Sim</option>
          <option value="false">Nao</option>
        </select></label>
        <label>Data Saida <input name="departure_date" type="date" value="2026-06-15"></label>
        <label>Enchimento <input name="load_fill" value="completa"></label>
        <label>Veiculo <input name="suggested_vehicle_type" value="Camiao"></label>
        <label>Origem Lat <input name="origin_lat" type="number" step="0.000001" value="-25.9692"></label>
        <label>Origem Lng <input name="origin_lng" type="number" step="0.000001" value="32.5732"></label>
        <label>Destino Lat <input name="destination_lat" type="number" step="0.000001" value="-19.8432"></label>
        <label>Destino Lng <input name="destination_lng" type="number" step="0.000001" value="34.8386"></label>
      </div>
      <label>Descricao <textarea name="description">Descricao de teste</textarea></label>
      <label>Instrucoes <textarea name="instructions">Carga fragil</textarea></label>
      <button>Publicar</button>
    </form>
  </dialog>

  <dialog id="loadUpdateDialog">
    <div class="dialog-head">
      <h2>Editar Carga</h2>
      <button onclick="document.getElementById('loadUpdateDialog').close()">✕</button>
    </div>
    <form onsubmit="updateLoad(event)">
      <label>Load ID <input id="loadId" name="load_id" type="number" readonly></label>
      <label>Status <input name="status" value=""></label>
      <label>Valor <input name="value" type="number"></label>
      <label>Descricao <textarea name="description"></textarea></label>
      <button>Atualizar</button>
    </form>
  </dialog>

  <!-- PROPOSALS DIALOGS -->
  <dialog id="proposalCreateDialog">
    <div class="dialog-head">
      <h2>Enviar Proposta</h2>
      <button onclick="document.getElementById('proposalCreateDialog').close()">✕</button>
    </div>
    <form onsubmit="createProposal(event)">
      <label>Load ID <input name="load_id" type="number"></label>
      <label>Valor Proposto <input name="proposed_value" type="number" step="0.01" value="28000"></label>
      <label>Motorista ID <input name="driver_id" type="number"></label>
      <label>Veiculo ID <input name="vehicle_id" type="number"></label>
      <label>Mensagem <textarea name="message">Proposta inicial</textarea></label>
      <button>Enviar</button>
    </form>
  </dialog>

  <dialog id="negotiationDialog">
    <div class="dialog-head">
      <h2>Contraproposta</h2>
      <button onclick="document.getElementById('negotiationDialog').close()">✕</button>
    </div>
    <form onsubmit="createNegotiation(event)">
      <label>Proposal ID <input name="proposal_id" type="number"></label>
      <label>Valor <input name="amount" type="number" step="0.01" value="26000"></label>
      <label>Mensagem <textarea name="message">Contraproposta</textarea></label>
      <button>Enviar</button>
    </form>
  </dialog>

  <!-- TRIPS DIALOGS -->
  <dialog id="tripStartDialog">
    <div class="dialog-head">
      <h2>Iniciar Viagem</h2>
      <button onclick="document.getElementById('tripStartDialog').close()">✕</button>
    </div>
    <form onsubmit="startTrip(event)">
      <label>Trip ID <input id="tripId" name="trip_id" type="number"></label>
      <label>Latitude <input name="current_lat" type="number" step="0.000001" value="-25.9692"></label>
      <label>Longitude <input name="current_lng" type="number" step="0.000001" value="32.5732"></label>
      <button>Iniciar</button>
    </form>
  </dialog>

  <!-- LOCATION DIALOG -->
  <dialog id="locationDialog">
    <div class="dialog-head">
      <h2>Localização para Cálculo de Distâncias</h2>
      <button onclick="document.getElementById('locationDialog').close()">✕</button>
    </div>
    <form onsubmit="setCustomLocation(event)">
      <div class="row-compact" style="margin-bottom: 8px;">
        <button type="button" onclick="useCurrentLocation()">📍 Usar Localização Atual</button>
      </div>
      <label>Latitude <input id="customLat" name="lat" type="number" step="0.000001" value="-25.9692"></label>
      <label>Longitude <input id="customLng" name="lng" type="number" step="0.000001" value="32.5732"></label>
      <button>Guardar Localização</button>
    </form>
  </dialog>

  <dialog id="driverUpdateDialog">
    <div class="dialog-head">
      <h2>Atualizar Motorista</h2>
      <button onclick="document.getElementById('driverUpdateDialog').close()">✕</button>
    </div>
    <form onsubmit="updateDriver(event)">
      <div class="grid">
        <label>Carta <input name="license_number" value=""></label>
        <label>Validade carta <input name="license_expiry" type="date"></label>
        <label>Anos experiencia <input name="years_experience" type="number"></label>
        <label>Disponivel <select name="available">
          <option value="">(nao alterar)</option>
          <option value="true">sim</option>
          <option value="false">nao</option>
        </select></label>
      </div>
      <button>Atualizar</button>
    </form>
  </dialog>

  <dialog id="driverLocationDialog">
    <div class="dialog-head">
      <h2>Localizacao Motorista</h2>
      <button onclick="document.getElementById('driverLocationDialog').close()">✕</button>
    </div>
    <form onsubmit="updateDriverLocation(event)">
      <label>Latitude <input name="latitude" type="number" step="0.000001" value="-25.9692"></label>
      <label>Longitude <input name="longitude" type="number" step="0.000001" value="32.5732"></label>
      <label>Sincronizar veiculos <select name="sync_vehicles">
        <option value="true">sim</option>
        <option value="false">nao</option>
      </select></label>
      <button>Atualizar</button>
    </form>
  </dialog>

  <dialog id="driverAvailabilityDialog">
    <div class="dialog-head">
      <h2>Disponibilidade</h2>
      <button onclick="document.getElementById('driverAvailabilityDialog').close()">✕</button>
    </div>
    <form onsubmit="updateDriverAvailability(event)">
      <label>Disponivel <select name="available">
        <option value="true">sim</option>
        <option value="false">nao</option>
      </select></label>
      <button>Atualizar</button>
    </form>
  </dialog>

  <!-- MAIN SECTIONS -->
  <section>
    <h2>Auth & Users</h2>
    <div class="row-compact">
      <button onclick="document.getElementById('loginDialog').showModal()">Login</button>
      <button onclick="document.getElementById('registerDialog').showModal()">Cadastro</button>
      <button onclick="safeRun(() => api('/auth/me'))">GET /auth/me</button>
      <button onclick="document.getElementById('locationDialog').showModal()">📍 Localização</button>
    </div>
  </section>

  <section>
    <h2>Utilizadores</h2>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/users/me/profile'))">GET /users/me/profile</button>
      <button onclick="document.getElementById('userUpdateDialog').showModal()">PATCH /users/me</button>
      <button onclick="safeRun(() => requestById('/users/', 'User ID'))">GET /users/{id}</button>
    </div>
  </section>

  <section>
    <h2>Clientes</h2>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/clients/me'))">GET /clients/me</button>
      <button onclick="document.getElementById('userUpdateDialog').showModal()">PATCH /clients/me</button>
      <button onclick="safeRun(() => api('/clients'))">GET /clients</button>
      <button onclick="safeRun(() => requestById('/clients/', 'Client ID'))">GET /clients/{id}</button>
      <button onclick="safeRun(() => api('/clients/me/stats'))">GET /clients/me/stats</button>
      <button onclick="safeRun(() => api('/clients/me/activities'))">GET /clients/me/activities</button>
    </div>
  </section>

  <section>
    <h2>Empresas</h2>
    <div class="workflow">
      <span class="workflow-title">Como associar motorista a esta empresa</span>
      <ol>
        <li>Faca <strong>Login</strong> com conta tipo <code>empresa</code> (token no topo)</li>
        <li>Peca o <strong>email de login</strong> do motorista (nao ha lista publica de motoristas)</li>
        <li>Clique no botao verde <strong>Associar motorista a empresa</strong> e informe o email</li>
        <li>Confirme com <em>GET motoristas da empresa</em> (lista so da sua frota)</li>
        <li>Depois, em <strong>Veiculos</strong>: atribua o camiao ao motorista</li>
      </ol>
      <div class="row-compact">
        <button type="button" data-method="post" class="btn-action" onclick="document.getElementById('companyAttachDriverDialog').showModal()">Associar motorista a empresa</button>
        <button type="button" data-method="get" onclick="safeRun(() => api('/companies/me/drivers'))">GET motoristas da empresa</button>
        <button type="button" data-method="delete" onclick="safeRun(detachCompanyDriver)">Remover motorista</button>
      </div>
    </div>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/companies/me'))">GET /companies/me</button>
      <button onclick="safeRun(() => api('/companies'))">GET /companies</button>
      <button onclick="safeRun(() => requestById('/companies/', 'Company ID'))">GET /companies/{id}</button>
      <button onclick="safeRun(() => api('/companies/me/proposals'))">GET /companies/me/proposals</button>
      <button onclick="safeRun(() => api('/companies/me/trips'))">GET /companies/me/trips</button>
    </div>
  </section>

  <section>
    <h2>Motoristas</h2>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/drivers/me'))">GET /drivers/me</button>
      <button onclick="document.getElementById('driverUpdateDialog').showModal()">PATCH /drivers/me</button>
      <button onclick="document.getElementById('driverLocationDialog').showModal()">PATCH /drivers/me/location</button>
      <button onclick="document.getElementById('driverAvailabilityDialog').showModal()">PATCH /drivers/me/availability</button>
      <button onclick="safeRun(() => api('/drivers'))">GET /drivers (so frota da empresa)</button>
      <button onclick="safeRun(() => requestById('/drivers/', 'Driver ID da frota'))">GET /drivers/{id}</button>
    </div>
  </section>

  <section>
    <h2>Veiculos</h2>
    <p class="mini">Motorista na frota (email). Criar: POST /vehicles com driver_email. Ja criado: PATCH motorista.</p>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/vehicles'))">GET /vehicles disponiveis</button>
      <button onclick="safeRun(() => api('/vehicles/me'))">GET /vehicles/me</button>
      <button onclick="safeRun(() => requestById('/vehicles/', 'Vehicle ID'))">GET /vehicles/{id}</button>
      <button onclick="document.getElementById('vehicleCreateDialog').showModal()">POST /vehicles</button>
      <button onclick="document.getElementById('vehicleAssignDriverDialog').showModal()">PATCH /vehicles/{id} motorista</button>
      <button onclick="document.getElementById('vehicleUpdateDialog').showModal()">PATCH /vehicles/{id}</button>
      <button onclick="document.getElementById('vehicleLocationDialog').showModal()">PATCH location</button>
      <button onclick="safeRun(() => deleteById('/vehicles/', 'Vehicle ID'))">DELETE /vehicles/{id}</button>
    </div>
  </section>

  <section>
    <h2>Cargas</h2>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/loads/types', { auth: false }))">GET /loads/types</button>
      <button onclick="safeRun(() => api('/loads/fill-types', { auth: false }))">GET /loads/fill-types</button>
      <button onclick="safeRun(listLoadsWithDistance)">GET /loads com km</button>
      <button onclick="safeRun(() => api('/loads'))">GET /loads (sem km)</button>
      <button onclick="safeRun(() => api('/loads/me'))">GET /loads/me</button>
      <button onclick="safeRun(() => requestById('/loads/', 'Load ID'))">GET /loads/{id}</button>
      <button onclick="safeRun(() => requestById('/loads/', 'Load ID', '/tracking'))">GET /loads/{id}/tracking</button>
      <button onclick="document.getElementById('loadCreateDialog').showModal()">POST /loads</button>
      <button onclick="document.getElementById('loadUpdateDialog').showModal()">PATCH /loads/{id}</button>
      <button onclick="safeRun(() => deleteById('/loads/', 'Load ID'))">DELETE /loads/{id}</button>
    </div>
  </section>

  <section>
    <h2>Propostas</h2>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/proposals/me'))">GET /proposals/me</button>
      <button onclick="safeRun(() => api('/proposals/received'))">GET /proposals/received</button>
      <button onclick="safeRun(() => requestById('/proposals/', 'Proposal ID'))">GET /proposals/{id}</button>
      <button onclick="safeRun(() => requestById('/proposals/', 'Proposal ID', '/negotiations'))">GET negotiations</button>
      <button onclick="document.getElementById('proposalCreateDialog').showModal()">POST proposta</button>
      <button onclick="document.getElementById('negotiationDialog').showModal()">POST negotiation</button>
      <button onclick="safeRun(() => proposalAction('accept'))">POST accept</button>
      <button onclick="safeRun(() => proposalAction('reject'))">POST reject</button>
    </div>
  </section>

  <section>
    <h2>Viagens</h2>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/trips/me'))">GET /trips/me</button>
      <button onclick="safeRun(() => requestById('/trips/', 'Trip ID'))">GET /trips/{id}</button>
      <button onclick="document.getElementById('tripStartDialog').showModal()">PATCH /trips/start</button>
      <button onclick="safeRun(() => requestById('/trips/', 'Trip ID', '/locations'))">GET locations</button>
      <button onclick="safeRun(() => requestById('/driver-trips/', 'Trip ID'))">GET /driver-trips/{id}</button>
      <button onclick="safeRun(() => api('/driver-trips'))">GET /driver-trips</button>
      <button onclick="safeRun(() => api('/driver-trips/stops/types', { auth: false }))">GET stop types</button>
    </div>
  </section>

  <section>
    <h2>Documentos</h2>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/documents/types', { auth: false }))">GET /documents/types</button>
      <button onclick="safeRun(() => api('/documents/me'))">GET /documents/me</button>
      <button onclick="safeRun(() => requestById('/documents/me/', 'Document ID'))">GET /documents/me/{id}</button>
      <button onclick="safeRun(() => deleteById('/documents/me/', 'Document ID'))">DELETE /documents/me/{id}</button>
    </div>
  </section>

  <section>
    <h2>Mensagens</h2>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/messages/summary'))">GET /messages/summary</button>
      <button onclick="safeRun(() => api('/messages'))">GET /messages (conversas)</button>
      <button onclick="safeRun(() => requestById('/messages/loads/', 'Load ID'))">GET /messages/loads/{id}</button>
    </div>
  </section>

  <section>
    <h2>Notificacoes</h2>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/notifications'))">GET /notifications</button>
      <button onclick="safeRun(() => api('/notifications/unread-count'))">GET unread-count</button>
      <button onclick="safeRun(() => api('/notifications/read-all', { method: 'PATCH' }))">PATCH read-all</button>
    </div>
  </section>

  <section>
    <h2>Carteira</h2>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/wallet'))">GET /wallet (saldo)</button>
      <button onclick="safeRun(() => api('/wallet/transactions'))">GET /wallet/transactions</button>
      <button onclick="safeRun(() => api('/wallet/deposits', { method: 'POST', json: { amount: 10000, phone: '' } }))">POST deposit</button>
    </div>
  </section>

  <section>
    <h2>Stats</h2>
    <div class="row-compact">
      <button onclick="safeRun(() => api('/stats/dashboard'))">GET /stats/dashboard</button>
    </div>
  </section>

  <!-- WORKFLOW: NEGOCIAÇÃO COMPLETA -->
  <section id="negotiationSection">
    <h2>🔄 Workflow: Negociação → Viagem → GPS</h2>
    <div class="workflow" style="border-color: #6ee7b7; background: rgba(110, 231, 183, 0.08);">
      <span class="workflow-title" style="color: #6ee7b7;">Fluxo Completo de Negociação</span>
      <ol style="color: #d1fae5;">
        <li><strong>1. Cliente publica carga</strong> (POST /loads)</li>
        <li><strong>2. Empresa vê cargas disponíveis</strong> (GET /loads)</li>
        <li><strong>3. Empresa envia proposta</strong> (POST /loads/{id}/proposals)</li>
        <li><strong>4. Cliente vê propostas</strong> (GET /proposals/received)</li>
        <li><strong>5. Cliente aceita proposta</strong> (POST /loads/{id}/proposals/{id}/accept)</li>
        <li><strong>6. Trip é criada automaticamente</strong></li>
        <li><strong>7. Motorista inicia viagem</strong> (PATCH /trips/{id}/start)</li>
        <li><strong>8. Motorista envia localização GPS</strong> em tempo real</li>
      </ol>
      <div class="row-compact">
        <button type="button" class="btn-action method-post" onclick="negotiationDemo()" style="background: rgba(110, 231, 183, 0.12); border-color: rgba(110, 231, 183, 0.38);">▶️ Demo Completo</button>
      </div>
    </div>

    <h3 style="margin-top: 15px; color: #6ee7b7;">📋 Estado Atual</h3>
    <pre id="negotiationState" style="font-size: 10px; background: rgba(110, 231, 183, 0.05); border: 1px solid rgba(110, 231, 183, 0.3); padding: 8px; border-radius: 4px; max-height: 200px; overflow-y: auto;">Nenhuma negociação iniciada</pre>

    <h3 style="margin-top: 15px; color: #6ee7b7;">1️⃣ Cliente Publica Carga</h3>
    <form onsubmit="stepPublishLoad(event)" style="margin: 8px 0;">
      <div class="grid">
        <label>Nome Carga <input name="load_name" value="Componentes Eletrônicos" style="font-size: 11px;"></label>
        <label>Tipo <select name="load_type" style="font-size: 11px;">
          <option value="eletronica">Eletrônica</option>
          <option value="alimentos">Alimentos</option>
          <option value="construcao">Construção</option>
        </select></label>
        <label>Peso (ton) <input name="weight" type="number" value="50" style="font-size: 11px;"></label>
        <label>Valor (MT) <input name="value" type="number" value="50000" style="font-size: 11px;"></label>
        <label>Origem <input name="origin" value="Maputo" style="font-size: 11px;"></label>
        <label>Destino <input name="destination" value="Beira" style="font-size: 11px;"></label>
      </div>
      <button style="font-size: 11px; width: 100%;">Publicar Carga</button>
    </form>

    <h3 style="margin-top: 15px; color: #f0abfc;">2️⃣ Empresa Vê Cargas & Envia Proposta</h3>
    <div class="row-compact" style="margin-bottom: 8px;">
      <button onclick="stepListLoads()" class="method-get" style="font-size: 11px;">GET Cargas Disponíveis</button>
      <button onclick="stepListLoadDetails()" class="method-get" style="font-size: 11px;">GET Detalhes Carga</button>
    </div>
    <div id="loadsListDiv" style="background: var(--panel-2); border: 1px solid var(--line); border-radius: 4px; padding: 8px; margin-bottom: 8px; max-height: 150px; overflow-y: auto; font-size: 10px; display: none;">
      <strong style="color: #6ee7b7;">Cargas Disponíveis:</strong>
      <div id="loadsList"></div>
    </div>
    <div class="row-compact" style="margin-bottom: 8px;">
      <button type="button" onclick="refreshProposalFleetOptions()" class="method-get" style="font-size: 11px;">Atualizar frota (drivers/veículos)</button>
    </div>
    <form onsubmit="stepSendProposal(event)" style="margin: 8px 0;">
      <div class="grid">
        <label>Load ID <input id="proposalLoadId" name="load_id" type="number" placeholder="ex: 1" style="font-size: 11px;"></label>
        <label>Valor Proposto (MT) <input name="proposed_value" type="number" value="45000" style="font-size: 11px;"></label>
        <label>Driver ID
          <select id="proposalDriverId" name="driver_id" style="font-size: 11px;">
            <option value="">Selecione motorista</option>
          </select>
        </label>
        <label>Vehicle ID
          <select id="proposalVehicleId" name="vehicle_id" style="font-size: 11px;">
            <option value="">Selecione veículo</option>
          </select>
        </label>
      </div>
      <p class="mini" id="proposalFleetHint">Faça login como empresa e clique em "Atualizar frota".</p>
      <button style="font-size: 11px; width: 100%;">Enviar Proposta</button>
    </form>

    <h3 style="margin-top: 15px; color: #fbbf24;">3️⃣ Cliente Vê Propostas & Aceita</h3>
    <div class="row-compact" style="margin-bottom: 8px;">
      <button onclick="stepListProposals()" class="method-get" style="font-size: 11px;">GET Propostas Recebidas</button>
    </div>
    <div id="proposalsListDiv" style="background: var(--panel-2); border: 1px solid var(--line); border-radius: 4px; padding: 8px; margin-bottom: 8px; max-height: 150px; overflow-y: auto; font-size: 10px; display: none;">
      <strong style="color: #fbbf24;">Propostas Recebidas:</strong>
      <div id="proposalsList"></div>
    </div>
    <form onsubmit="stepAcceptProposal(event)" style="margin: 8px 0;">
      <div class="grid">
        <label>Load ID <input id="acceptLoadId" name="load_id" type="number" placeholder="ex: 1" style="font-size: 11px;"></label>
        <label>Proposal ID <input id="acceptProposalId" name="proposal_id" type="number" placeholder="ex: 1" style="font-size: 11px;"></label>
      </div>
      <button style="font-size: 11px; width: 100%; background: rgba(134, 239, 172, 0.12); border-color: rgba(134, 239, 172, 0.38); color: #d1fae5;">✅ Aceitar Proposta (Cria Trip)</button>
    </form>

    <h3 style="margin-top: 15px; color: #38bdf8;">4️⃣ Motorista Inicia Viagem</h3>
    <div class="row-compact" style="margin-bottom: 8px;">
      <button onclick="stepListTrips()" class="method-get" style="font-size: 11px;">GET Minhas Viagens</button>
    </div>
    <div id="tripsListDiv" style="background: var(--panel-2); border: 1px solid var(--line); border-radius: 4px; padding: 8px; margin-bottom: 8px; max-height: 150px; overflow-y: auto; font-size: 10px; display: none;">
      <strong style="color: #38bdf8;">Viagens do Motorista:</strong>
      <div id="tripsList"></div>
    </div>
    <form onsubmit="stepStartTrip(event)" style="margin: 8px 0;">
      <div class="grid">
        <label>Trip ID <input id="startTripId" name="trip_id" type="number" placeholder="ex: 1" style="font-size: 11px;"></label>
        <label>Latitude <input name="latitude" type="number" step="0.000001" value="-25.9692" style="font-size: 11px;"></label>
        <label>Longitude <input name="longitude" type="number" step="0.000001" value="32.5732" style="font-size: 11px;"></label>
      </div>
      <button style="font-size: 11px; width: 100%; background: rgba(56, 189, 248, 0.12); border-color: rgba(56, 189, 248, 0.38); color: #bae6fd;">🚗 Iniciar Viagem</button>
    </form>
  </section>

  <section>
    <h2>WebSocket - Chat em Tempo Real & GPS</h2>
    <div class="row-compact" style="margin-bottom: 8px;">
      <button onclick="connectWebSocket()" class="method-post">🔌 Conectar WebSocket</button>
      <button onclick="disconnectWebSocket()" class="method-delete">❌ Desconectar</button>
      <button onclick="clearGPSLogs()" class="method-delete">Limpar Logs GPS</button>
    </div>
    <div class="row-compact">
      <label style="flex: 1;">Trip ID para rastrear: <input id="tripIdWS" type="number" value="1" style="width: 100%; padding: 4px;"></label>
      <button onclick="subscribeTrip()" class="method-post">Subscribe Viagem</button>
      <button onclick="unsubscribeTrip()" class="method-delete">Unsubscribe</button>
    </div>
    <div class="ws-container">
      <div></div>
      <div class="ws-chat-panel">
        <div class="ws-chat-header">
          <span><span class="ws-status-badge" id="wsStatus"></span>Chat - WebSocket</span>
          <span id="wsConnectionTime" style="font-size: 10px; color: var(--muted);">-</span>
        </div>
        <div class="ws-messages" id="wsChatMessages"></div>
        <div class="ws-input-area">
          <input id="wsChatInput" type="text" placeholder="Mensagem...">
          <button onclick="sendWSMessage()">Enviar</button>
        </div>
      </div>
    </div>
    
    <h3 style="margin-top: 10px; color: #fbbf24;">📍 Logs de GPS em Tempo Real</h3>
    <div class="row-compact" style="margin-bottom: 8px;">
      <label style="flex: 1;">Latitude: <input id="driverLat" type="number" step="0.000001" value="-25.9692" style="width: 100%; padding: 4px;"></label>
      <label style="flex: 1;">Longitude: <input id="driverLng" type="number" step="0.000001" value="32.5732" style="width: 100%; padding: 4px;"></label>
      <button onclick="sendDriverLocation()" class="method-post">Enviar Localização</button>
    </div>
    <div class="gps-logs" id="gpsLogs">
      <div style="color: var(--muted); text-align: center; padding: 20px;">Logs de GPS aparecem aqui...</div>
    </div>
  </section>

  <section>
    <h2>Request Manual</h2>
    <form onsubmit="manualRequest(event)">
      <div class="grid">
        <label>Metodo <select name="method">
          <option>GET</option>
          <option>POST</option>
          <option>PATCH</option>
          <option>DELETE</option>
        </select></label>
        <label>Path <input name="path" value="/auth/me"></label>
      </div>
      <label>JSON body <textarea name="body">{}</textarea></label>
      <button>Enviar</button>
    </form>
  </section>

  </div>

  <aside class="output-panel">
    <div class="row" style="justify-content: space-between;">
      <h3 style="margin: 0;">Resultado</h3>
      <button onclick="write({ message: 'Limpo' })" style="padding: 3px 6px; font-size: 11px;">Limpar</button>
    </div>
    <pre id="result"></pre>
  </aside>
  </div>
</main>

<script>
const tokenKey = "cargolink_test_token";
const result = document.getElementById("result");
const tokenState = document.getElementById("tokenState");
const statusMessage = document.getElementById("statusMessage");

function getToken() { return localStorage.getItem(tokenKey) || ""; }
function setToken(token) { localStorage.setItem(tokenKey, token); updateTokenState(); setStatus("Token guardado"); }
function clearToken() { localStorage.removeItem(tokenKey); updateTokenState(); write({ message: "Token removido" }); }
function updateTokenState() {
  const token = getToken();
  tokenState.textContent = token ? "sim (" + token.slice(0, 15) + "...)" : "nao";
}

async function rawApi(path, options = {}) {
  const method = options.method || "GET";
  const headers = options.headers || {};
  if (options.auth !== false && getToken()) headers.Authorization = "Bearer " + getToken();
  if (options.json) headers["Content-Type"] = "application/json";

  const res = await fetch(path, {
    method,
    headers,
    body: options.json ? JSON.stringify(options.json) : options.body,
  });
  const ct = res.headers.get("content-type") || "";
  const body = ct.includes("application/json") ? await res.json() : await res.text();
  return { ok: res.ok, status: res.status, body };
}

function write(data) {
  if (typeof data === "string") { result.textContent = data; return; }
  result.innerHTML = highlightJson(data);
}

function escapeHtml(v) {
  return String(v).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function highlightJson(data) {
  const json = escapeHtml(JSON.stringify(data, null, 2));
  return json.replace(
    /("(?:\\\\.|[^"\\\\])*")(\\s*:)?|\\b(true|false)\\b|\\b(null)\\b|-?\\d+(?:\\.\\d+)?(?:e[+-]?\\d+)?/gi,
    (m, s, c, b, n) => {
      if (s && c) return '<span class="json-key">' + s + '</span>' + c;
      if (s) return '<span class="json-string">' + s + '</span>';
      if (b) return '<span class="json-bool">' + b + '</span>';
      if (n) return '<span class="json-null">null</span>';
      return '<span class="json-number">' + m + '</span>';
    }
  );
}

function setStatus(msg) { statusMessage.textContent = msg; }

async function safeRun(fn) {
  try { await fn(); } catch (e) { 
    setStatus(e.message); 
    write({ error: e.message }); 
  }
}

function formObject(form) {
  const data = new FormData(form);
  const obj = {};
  for (const [k, v] of data.entries()) {
    if (v === "" || (v instanceof File)) continue;
    if (["proposed_value", "amount", "weight", "volume", "value", "origin_lat", "origin_lng", "destination_lat", "destination_lng", "tonnage_capacity", "current_lat", "current_lng", "latitude", "longitude", "years_experience", "load_id", "vehicle_id", "driver_id", "proposal_id", "negotiation_id", "trip_id"].includes(k)) {
      obj[k] = Number(v);
    } else if (v === "true" || v === "false") {
      obj[k] = v === "true";
    } else {
      obj[k] = v;
    }
  }
  return obj;
}

async function api(path, options = {}) {
  const method = options.method || "GET";
  const headers = options.headers || {};
  setStatus("Enviando " + method + " " + path);
  if (options.auth !== false && getToken()) headers.Authorization = "Bearer " + getToken();
  if (options.json) headers["Content-Type"] = "application/json";

  const res = await fetch(path, {
    method,
    headers,
    body: options.json ? JSON.stringify(options.json) : options.body,
  });
  const ct = res.headers.get("content-type") || "";
  const body = ct.includes("application/json") ? await res.json() : await res.text();
  write({ status: res.status, ok: res.ok, body });
  if (!res.ok) {
    const detail = body?.detail || "HTTP " + res.status;
    setStatus("Erro: " + detail);
  } else {
    setStatus("OK: " + method + " " + path);
  }
  return body;
}

async function registerUser(e) {
  e.preventDefault();
  await safeRun(async () => {
    const body = formObject(e.target);
    const data = await api("/auth/register", { method: "POST", json: body, auth: false });
    if (data.access_token) {
      setToken(data.access_token);
      document.getElementById("registerDialog").close();
    }
  });
}

async function loginUser(e) {
  e.preventDefault();
  await safeRun(async () => {
    const data = await api("/auth/login", { method: "POST", json: formObject(e.target), auth: false });
    if (data.access_token) {
      setToken(data.access_token);
      await refreshProposalFleetOptions();
      document.getElementById("loginDialog").close();
    }
  });
}

async function authMe() { await api("/auth/me"); }

async function updateUser(e) {
  e.preventDefault();
  const body = formObject(e.target);
  await safeRun(() => api("/users/me", { method: "PATCH", json: body }));
}

async function changePassword(e) {
  e.preventDefault();
  const body = formObject(e.target);
  await safeRun(() => api("/auth/password", { method: "PATCH", json: body }));
}

async function createVehicle(e) {
  e.preventDefault();
  await safeRun(async () => {
    const form = new FormData(e.target);
    for (const [k, v] of [...form.entries()]) {
      if (v === "" || (v instanceof File && !v.name)) form.delete(k);
    }
    await api("/vehicles", { method: "POST", body: form });
  });
}

async function updateVehicle(e) {
  e.preventDefault();
  const body = formObject(e.target);
  const vid = body.vehicle_id;
  delete body.vehicle_id;
  await safeRun(() => api("/vehicles/" + vid, { method: "PATCH", json: body }));
}

async function updateVehicleLocation(e) {
  e.preventDefault();
  const body = formObject(e.target);
  const vid = body.vehicle_id;
  delete body.vehicle_id;
  await safeRun(() => api("/vehicles/" + vid + "/location", { method: "PATCH", json: body }));
}

async function attachCompanyDriver(e) {
  e.preventDefault();
  await safeRun(async () => {
    const body = formObject(e.target);
    await api("/companies/me/drivers", { method: "POST", json: body });
    document.getElementById("companyAttachDriverDialog").close();
  });
}

async function detachCompanyDriver() {
  const email = prompt("Email do motorista a remover da empresa:");
  if (!email) return;
  if (!confirm("Remover motorista da empresa? Camioes atribuidos ficam sem motorista.")) return;
  await api("/companies/me/drivers?email=" + encodeURIComponent(email.trim()), { method: "DELETE" });
  write({ message: "Motorista removido da empresa" });
}

async function assignVehicleDriver(e) {
  e.preventDefault();
  await safeRun(async () => {
    const body = formObject(e.target);
    const vid = body.vehicle_id;
    await api("/vehicles/" + vid, { method: "PATCH", json: { driver_email: body.driver_email } });
    document.getElementById("vehicleAssignDriverDialog").close();
  });
}

async function createLoad(e) {
  e.preventDefault();
  const form = new FormData(e.target);
  for (const [k, v] of [...form.entries()]) {
    if (v === "" || (v instanceof File && !v.name)) form.delete(k);
  }
  await safeRun(() => api("/loads", { method: "POST", body: form }));
}

async function updateLoad(e) {
  e.preventDefault();
  const body = formObject(e.target);
  const lid = body.load_id;
  delete body.load_id;
  await safeRun(() => api("/loads/" + lid, { method: "PATCH", json: body }));
}

async function createProposal(e) {
  e.preventDefault();
  const body = formObject(e.target);
  const lid = body.load_id;
  delete body.load_id;
  await safeRun(() => api("/proposals/loads/" + lid, { method: "POST", json: body }));
}

async function createNegotiation(e) {
  e.preventDefault();
  const body = formObject(e.target);
  const pid = body.proposal_id;
  delete body.proposal_id;
  await safeRun(() => api("/proposals/" + pid + "/negotiations", { method: "POST", json: body }));
}

async function proposalAction(action) {
  const pid = prompt("Proposal ID:");
  if (!pid) return;
  const map = {
    accept: ["POST", "/proposals/" + pid + "/accept"],
    reject: ["POST", "/proposals/" + pid + "/reject"],
  };
  const [method, path] = map[action];
  await safeRun(() => api(path, { method }));
}

async function startTrip(e) {
  e.preventDefault();
  const body = formObject(e.target);
  const tid = body.trip_id;
  delete body.trip_id;
  await safeRun(() => api("/trips/" + tid + "/start", { method: "PATCH", json: body }));
}

async function updateDriver(e) {
  e.preventDefault();
  const body = formObject(e.target);
  await safeRun(() => api("/drivers/me", { method: "PATCH", json: body }));
}

async function updateDriverLocation(e) {
  e.preventDefault();
  const body = formObject(e.target);
  await safeRun(() => api("/drivers/me/location", { method: "PATCH", json: body }));
}

async function updateDriverAvailability(e) {
  e.preventDefault();
  const body = formObject(e.target);
  await safeRun(() => api("/drivers/me/availability", { method: "PATCH", json: { available: body.available } }));
}

// ============= WebSocket Functions =============
let websocket = null;
let wsConnectionStart = null;
const gpsLocationLogs = [];

function getWSUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const token = getToken();
  if (!token) {
    setStatus("Erro: Token não disponível");
    return null;
  }
  return protocol + "://" + window.location.host + "/ws?token=" + encodeURIComponent(token);
}

function addChatMessage(type, text) {
  const container = document.getElementById("wsChatMessages");
  const msg = document.createElement("div");
  msg.className = "ws-message " + type;
  const time = new Date().toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  msg.innerHTML = `<span class="ws-message-time">[${time}]</span> ${escapeHtml(text)}`;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

function addGPSLog(lat, lng, tripId, timestamp = new Date()) {
  const log = {
    timestamp: timestamp.toISOString(),
    latitude: lat,
    longitude: lng,
    trip_id: tripId || null,
    driver_position: { lat, lng },
    vehicle_position: { lat, lng }
  };
  gpsLocationLogs.push(log);
  
  const logsContainer = document.getElementById("gpsLogs");
  if (logsContainer.children.length === 1 && logsContainer.children[0].textContent.includes("Logs de GPS")) {
    logsContainer.innerHTML = "";
  }
  
  const entry = document.createElement("div");
  entry.className = "gps-log-entry";
  entry.textContent = JSON.stringify(log, null, 2);
  logsContainer.appendChild(entry);
  logsContainer.scrollTop = logsContainer.scrollHeight;
  
  addChatMessage("location", `📍 GPS: ${lat.toFixed(4)}, ${lng.toFixed(4)}`);
}

function clearGPSLogs() {
  gpsLocationLogs.length = 0;
  document.getElementById("gpsLogs").innerHTML = '<div style="color: var(--muted); text-align: center; padding: 20px;">Logs de GPS aparecem aqui...</div>';
  addChatMessage("success", "Logs GPS limpos");
}

function updateWSStatus(connected) {
  const badge = document.getElementById("wsStatus");
  if (connected) {
    badge.classList.add("connected");
    badge.title = "Conectado";
  } else {
    badge.classList.remove("connected");
    badge.title = "Desconectado";
  }
}

function formatWSConnectionTime() {
  if (!wsConnectionStart) return "-";
  const seconds = Math.floor((Date.now() - wsConnectionStart) / 1000);
  return `${seconds}s`;
}

function connectWebSocket() {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    addChatMessage("error", "Já conectado");
    return;
  }
  
  const url = getWSUrl();
  if (!url) return;
  
  setStatus("Conectando ao WebSocket...");
  websocket = new WebSocket(url);
  
  websocket.onopen = (event) => {
    wsConnectionStart = Date.now();
    updateWSStatus(true);
    setStatus("WebSocket conectado");
    addChatMessage("success", "🔌 Conectado ao WebSocket");
    
    // Auto-subscribe a trips ativas
    const tripId = document.getElementById("tripIdWS").value;
    if (tripId) {
      subscribeTrip();
    }
  };
  
  websocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleWSMessage(data);
  };
  
  websocket.onerror = (error) => {
    setStatus("Erro no WebSocket");
    addChatMessage("error", "❌ Erro: " + (error.message || "Desconexão"));
  };
  
  websocket.onclose = () => {
    updateWSStatus(false);
    wsConnectionStart = null;
    setStatus("WebSocket desconectado");
    addChatMessage("error", "❌ Desconectado do WebSocket");
  };
  
  // Atualizar status a cada segundo
  const statusInterval = setInterval(() => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      clearInterval(statusInterval);
      return;
    }
    document.getElementById("wsConnectionTime").textContent = formatWSConnectionTime();
  }, 1000);
}

function disconnectWebSocket() {
  if (websocket) {
    websocket.close();
    websocket = null;
    updateWSStatus(false);
    setStatus("WebSocket desconectado manualmente");
  }
}

function handleWSMessage(data) {
  console.log("WS Message:", data);
  
  switch (data.type) {
    case "driver_location":
      addChatMessage("location", `📍 Motorista em: ${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)} (Trip ${data.trip_id})`);
      addGPSLog(data.latitude, data.longitude, data.trip_id);
      break;
      
    case "message_send":
      addChatMessage("chat", `💬 ${data.body}`);
      break;
      
    case "subscribe_trip":
      addChatMessage("success", `✅ Inscrito na viagem ${data.trip_id}`);
      break;
      
    case "unsubscribe_trip":
      addChatMessage("success", `🔕 Desinscrição da viagem ${data.trip_id}`);
      break;
      
    case "error":
      addChatMessage("error", `❌ Erro: ${data.message}`);
      break;
      
    default:
      addChatMessage("success", `📩 ${JSON.stringify(data)}`);
  }
}

function subscribeTrip() {
  if (!websocket || websocket.readyState !== WebSocket.OPEN) {
    addChatMessage("error", "WebSocket não conectado");
    return;
  }
  
  const tripId = parseInt(document.getElementById("tripIdWS").value);
  if (!tripId) {
    addChatMessage("error", "Trip ID inválido");
    return;
  }
  
  websocket.send(JSON.stringify({
    type: "subscribe_trip",
    trip_id: tripId
  }));
}

function unsubscribeTrip() {
  if (!websocket || websocket.readyState !== WebSocket.OPEN) {
    addChatMessage("error", "WebSocket não conectado");
    return;
  }
  
  const tripId = parseInt(document.getElementById("tripIdWS").value);
  if (!tripId) {
    addChatMessage("error", "Trip ID inválido");
    return;
  }
  
  websocket.send(JSON.stringify({
    type: "unsubscribe_trip",
    trip_id: tripId
  }));
}

function sendDriverLocation() {
  if (!websocket || websocket.readyState !== WebSocket.OPEN) {
    addChatMessage("error", "WebSocket não conectado");
    return;
  }
  
  const tripId = parseInt(document.getElementById("tripIdWS").value);
  const lat = parseFloat(document.getElementById("driverLat").value);
  const lng = parseFloat(document.getElementById("driverLng").value);
  
  if (!tripId || isNaN(lat) || isNaN(lng)) {
    addChatMessage("error", "Trip ID ou coordenadas inválidas");
    return;
  }
  
  websocket.send(JSON.stringify({
    type: "driver_location",
    trip_id: tripId,
    latitude: lat,
    longitude: lng
  }));
  
  addGPSLog(lat, lng, tripId);
}

function sendWSMessage() {
  if (!websocket || websocket.readyState !== WebSocket.OPEN) {
    addChatMessage("error", "WebSocket não conectado");
    return;
  }
  
  const input = document.getElementById("wsChatInput");
  const message = input.value.trim();
  
  if (!message) return;
  
  // Simular envio de mensagem (descomentar conforme API)
  // const tripId = parseInt(document.getElementById("tripIdWS").value);
  // websocket.send(JSON.stringify({
  //   type: "message_send",
  //   load_id: 1,
  //   receiver_id: 2,
  //   body: message
  // }));
  
  addChatMessage("chat", "👤 Você: " + message);
  input.value = "";
}

async function requestById(path, idLabel, suffix = "") {
  const id = prompt(idLabel + ":");
  if (!id) return;
  return api(path + id + suffix);
}

async function deleteById(path, idLabel) {
  const id = prompt(idLabel + ":");
  if (!id || !confirm("Tem certeza?")) return;
  return api(path + id, { method: "DELETE" });
}

async function manualRequest(e) {
  e.preventDefault();
  const f = e.target;
  const method = f.elements.method.value;
  const path = f.elements.path.value;
  let body;
  if (method !== "GET" && method !== "DELETE") {
    body = JSON.parse(f.elements.body.value || "{}");
  }
  await safeRun(() => api(path, { method, json: body }));
}

// Função para calcular distância entre dois pontos (Haversine formula)
function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // Raio da Terra em km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c * 10) / 10; // Retorna com 1 casa decimal
}

// Obter localização atual do usuário
function getCurrentLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Geolocalização não suportada"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      (err) => reject(new Error("Permissão de localização negada"))
    );
  });
}

// Armazenar localização customizada
const userLocationKey = "cargolink_user_location";

function getUserLocation() {
  const saved = localStorage.getItem(userLocationKey);
  if (saved) {
    return JSON.parse(saved);
  }
  return null;
}

function saveUserLocation(lat, lng) {
  localStorage.setItem(userLocationKey, JSON.stringify({ lat, lng }));
  setStatus("Localização salva: " + lat.toFixed(4) + ", " + lng.toFixed(4));
}

async function useCurrentLocation() {
  try {
    setStatus("Obtendo localização...");
    const loc = await getCurrentLocation();
    document.getElementById("customLat").value = loc.lat.toFixed(6);
    document.getElementById("customLng").value = loc.lng.toFixed(6);
    saveUserLocation(loc.lat, loc.lng);
  } catch (err) {
    setStatus("Erro: " + err.message);
  }
}

function setCustomLocation(e) {
  e.preventDefault();
  const lat = parseFloat(document.getElementById("customLat").value);
  const lng = parseFloat(document.getElementById("customLng").value);
  if (isNaN(lat) || isNaN(lng)) {
    setStatus("Coordenadas inválidas");
    return;
  }
  saveUserLocation(lat, lng);
  document.getElementById("locationDialog").close();
}

// Listar cargas com distâncias
async function listLoadsWithDistance() {
  try {
    let userLoc = getUserLocation();
    
    if (!userLoc) {
      setStatus("Obtendo localização...");
      userLoc = await getCurrentLocation();
      saveUserLocation(userLoc.lat, userLoc.lng);
    }
    
    setStatus("Carregando cargas...");
    const response = await fetch("/loads", {
      headers: getToken() ? { Authorization: "Bearer " + getToken() } : {},
    });
    const loads = await response.json();
    
    if (!Array.isArray(loads)) {
      write({ status: response.status, ok: response.ok, body: loads });
      return;
    }
    
    // Adicionar distâncias aos dados
    const loadsWithDistance = loads.map(load => {
      const distFromUser = calculateDistance(
        userLoc.lat, userLoc.lng,
        load.origin_lat, load.origin_lng
      );
      const distRoute = calculateDistance(
        load.origin_lat, load.origin_lng,
        load.destination_lat, load.destination_lng
      );
      return {
        ...load,
        "📍 km (você até origem)": distFromUser,
        "🛣️ km (rota)": distRoute
      };
    });
    
    write({
      sua_localizacao: { lat: userLoc.lat.toFixed(4), lng: userLoc.lng.toFixed(4) },
      total_cargas: loadsWithDistance.length,
      cargas: loadsWithDistance
    });
    setStatus("OK: " + loadsWithDistance.length + " cargas com distâncias");
  } catch (err) {
    setStatus("Erro: " + err.message);
    write({ error: err.message });
  }
}

function applyMethodButtonClasses() {
  document.querySelectorAll("button").forEach((btn) => {
    const fromData = btn.dataset.method;
    if (fromData) {
      btn.classList.add("method-" + fromData.toLowerCase());
      return;
    }
    const text = btn.textContent.trim().toUpperCase();
    const match = text.match(/^(GET|POST|PATCH|PUT|DELETE)\\b/);
    if (!match) return;
    btn.classList.add("method-" + match[1].toLowerCase());
  });
}

function syncManualMethodSelect() {
  const select = document.querySelector('form[onsubmit="manualRequest(event)"] select[name="method"]');
  if (!select) return;
  const paint = () => {
    select.classList.remove("method-get", "method-post", "method-patch", "method-put", "method-delete");
    select.classList.add("method-" + select.value.toLowerCase());
  };
  select.addEventListener("change", paint);
  paint();
}

// ========================================================================================
// FUNÇÕES DE NEGOCIAÇÃO E VIAGEM
// ========================================================================================

const negotiationState = {
  clientId: null,
  clientToken: null,
  companyToken: null,
  driverToken: null,
  driverId: null,
  vehicleId: null,
  loadId: null,
  proposalId: null,
  tripId: null,
};

const proposalFleetState = {
  drivers: [],
  vehicles: [],
};

function updateProposalFleetHint(message, isError = false) {
  const hint = document.getElementById("proposalFleetHint");
  if (!hint) return;
  hint.textContent = message;
  hint.style.color = isError ? "var(--err)" : "var(--muted)";
}

function escapeOptionLabel(value) {
  return String(value || "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function renderDriverOptions(selectedDriverId = null) {
  const select = document.getElementById("proposalDriverId");
  if (!select) return;
  const selected = selectedDriverId ?? (Number(select.value || 0) || null);
  const options = ['<option value="">Selecione motorista</option>'];
  for (const driver of proposalFleetState.drivers) {
    const id = Number(driver.id);
    const name = driver.user?.name || driver.name || `Motorista ${id}`;
    const selectedAttr = selected === id ? " selected" : "";
    options.push(`<option value="${id}"${selectedAttr}>${id} - ${escapeOptionLabel(name)}</option>`);
  }
  select.innerHTML = options.join("");
}

function renderVehicleOptions(selectedVehicleId = null) {
  const select = document.getElementById("proposalVehicleId");
  if (!select) return;
  const selectedDriverId = Number(document.getElementById("proposalDriverId")?.value || 0) || null;
  const selected = selectedVehicleId ?? (Number(select.value || 0) || null);
  const options = ['<option value="">Selecione veículo</option>'];
  const vehicles = proposalFleetState.vehicles.filter((vehicle) => {
    if (!selectedDriverId) return true;
    return vehicle.driver_id === null || vehicle.driver_id === undefined || Number(vehicle.driver_id) === selectedDriverId;
  });
  for (const vehicle of vehicles) {
    const id = Number(vehicle.id);
    const plate = vehicle.plate || vehicle.license_plate || `Veículo ${id}`;
    const selectedAttr = selected === id ? " selected" : "";
    options.push(`<option value="${id}"${selectedAttr}>${id} - ${escapeOptionLabel(plate)}</option>`);
  }
  select.innerHTML = options.join("");
}

function syncFleetSelectionState() {
  const driverId = Number(document.getElementById("proposalDriverId")?.value || 0) || null;
  const vehicleId = Number(document.getElementById("proposalVehicleId")?.value || 0) || null;
  negotiationState.driverId = driverId;
  negotiationState.vehicleId = vehicleId;
}

async function refreshProposalFleetOptions() {
  if (!getToken()) {
    updateProposalFleetHint("Faça login como empresa para carregar motoristas e veículos.", true);
    return;
  }

  const [driversRes, vehiclesRes] = await Promise.all([
    rawApi("/companies/me/drivers"),
    rawApi("/vehicles/me"),
  ]);

  if (!driversRes.ok || !vehiclesRes.ok) {
    const errorDetail = (driversRes.body && driversRes.body.detail) || (vehiclesRes.body && vehiclesRes.body.detail);
    updateProposalFleetHint(`Não foi possível carregar frota: ${errorDetail || "verifique permissão da conta empresa."}`, true);
    return;
  }

  const drivers = Array.isArray(driversRes.body) ? driversRes.body : [];
  const vehicles = Array.isArray(vehiclesRes.body) ? vehiclesRes.body : [];
  proposalFleetState.drivers = drivers;
  proposalFleetState.vehicles = vehicles;

  renderDriverOptions();
  renderVehicleOptions();

  const driverSelect = document.getElementById("proposalDriverId");
  const vehicleSelect = document.getElementById("proposalVehicleId");

  if (!driverSelect.value && drivers.length > 0) {
    driverSelect.value = String(drivers[0].id);
  }
  renderVehicleOptions();
  if (!vehicleSelect.value) {
    const selectedDriverId = Number(driverSelect.value || 0) || null;
    const candidateVehicle = vehicles.find((vehicle) => {
      if (!selectedDriverId) return true;
      return Number(vehicle.driver_id) === selectedDriverId || vehicle.driver_id === null || vehicle.driver_id === undefined;
    });
    if (candidateVehicle) {
      vehicleSelect.value = String(candidateVehicle.id);
    }
  }

  syncFleetSelectionState();
  updateProposalFleetHint(`Frota carregada: ${drivers.length} motoristas, ${vehicles.length} veículos.`);
}

function updateNegotiationState(data) {
  const stateEl = document.getElementById("negotiationState");
  if (stateEl) {
    stateEl.textContent = JSON.stringify({...negotiationState, ...data}, null, 2);
  }
}

function addNegotiationLog(msg, type = "info") {
  const stateEl = document.getElementById("negotiationState");
  if (stateEl) {
    stateEl.textContent = `[${new Date().toLocaleTimeString()}] ${msg}\n\n` + stateEl.textContent;
  }
}

// 1. CLIENTE PUBLICA CARGA
async function stepPublishLoad(e) {
  e.preventDefault();
  setStatus("Publicando carga...");
  try {
    const formData = formObject(e.target);
    const res = await api('/loads', { method: 'POST', json: formData });
    
    negotiationState.loadId = res.id;
    updateNegotiationState({ loadId: res.id });
    addNegotiationLog(`✅ Carga publicada! ID=${res.id}, Código=${res.code}`);
    
    document.getElementById("proposalLoadId").value = res.id;
    document.getElementById("acceptLoadId").value = res.id;
    
    write(res);
  } catch (error) {
    addNegotiationLog(`❌ Erro: ${error.message}`);
    setStatus("Erro ao publicar carga");
  }
}

// 2. LISTAR CARGAS DISPONÍVEIS
async function stepListLoads() {
  setStatus("Buscando cargas disponíveis...");
  try {
    const loads = await api('/loads', { auth: false });
    const listDiv = document.getElementById("loadsListDiv");
    const loadsList = document.getElementById("loadsList");
    
    if (Array.isArray(loads) && loads.length > 0) {
      loadsList.innerHTML = loads.map(l => `
        <div style="padding: 4px 0; border-bottom: 1px solid var(--line); cursor: pointer;" onclick="selectLoad(${l.id})">
          <strong>ID ${l.id}</strong> - ${l.load_name} (${l.origin} → ${l.destination})
          <br><span style="color: var(--muted);">MT ${l.value} | ${l.weight} ton | Negociável: ${l.negotiable}</span>
        </div>
      `).join("");
      listDiv.style.display = "block";
      addNegotiationLog(`✅ ${loads.length} cargas disponíveis`);
    } else {
      loadsList.innerHTML = '<p style="color: var(--muted);">Nenhuma carga disponível</p>';
      listDiv.style.display = "block";
    }
    write({ cargas: loads.length, loads: loads.slice(0, 3) });
  } catch (error) {
    addNegotiationLog(`❌ Erro: ${error.message}`);
  }
}

function selectLoad(loadId) {
  document.getElementById("proposalLoadId").value = loadId;
  negotiationState.loadId = loadId;
  addNegotiationLog(`📍 Carga selecionada: ID=${loadId}`);
}

// LISTAR DETALHES DE CARGA
async function stepListLoadDetails() {
  setStatus("Buscando detalhes...");
  try {
    const loadId = document.getElementById("proposalLoadId").value;
    if (!loadId) {
      alert("Selecione uma carga antes");
      return;
    }
    const load = await api(`/loads/${loadId}`, { auth: false });
    write(load);
    addNegotiationLog(`📄 Detalhes da carga ${loadId} carregados`);
  } catch (error) {
    addNegotiationLog(`❌ Erro: ${error.message}`);
  }
}

// 3. EMPRESA ENVIA PROPOSTA
async function stepSendProposal(e) {
  e.preventDefault();
  setStatus("Enviando proposta...");
  try {
    const formData = formObject(e.target);
    const loadId = formData.load_id;
    
    if (!loadId) {
      alert("Selecione uma carga");
      return;
    }

    if (!formData.driver_id || !formData.vehicle_id) {
      alert("Selecione motorista e veículo válidos na frota da empresa.");
      return;
    }
    
    const res = await api(`/loads/${loadId}/proposals`, { 
      method: 'POST', 
      json: {
        proposed_value: formData.proposed_value,
        driver_id: formData.driver_id,
        vehicle_id: formData.vehicle_id,
        message: "Proposta da nossa empresa"
      }
    });
    
    negotiationState.proposalId = res.id;
    negotiationState.driverId = formData.driver_id;
    negotiationState.vehicleId = formData.vehicle_id;
    updateNegotiationState(negotiationState);
    
    document.getElementById("acceptProposalId").value = res.id;
    addNegotiationLog(`✅ Proposta enviada! ID=${res.id}, Valor=MT ${res.proposed_value}`);
    write(res);
  } catch (error) {
    addNegotiationLog(`❌ Erro: ${error.message}`);
    setStatus("Erro ao enviar proposta");
  }
}

// 4. CLIENTE VÊ PROPOSTAS
async function stepListProposals() {
  setStatus("Buscando propostas...");
  try {
    const proposals = await api('/proposals/received');
    const listDiv = document.getElementById("proposalsListDiv");
    const proposalsList = document.getElementById("proposalsList");
    
    if (Array.isArray(proposals) && proposals.length > 0) {
      proposalsList.innerHTML = proposals.map(p => `
        <div style="padding: 6px 0; border-bottom: 1px solid var(--line); cursor: pointer;" onclick="selectProposal(${p.load_id}, ${p.id})">
          <strong>Proposta ID ${p.id}</strong> - Load ${p.load_id}
          <br><span style="color: #6ee7b7;">MT ${p.proposed_value} | Status: ${p.status}</span>
          <br><span style="color: var(--muted);">${p.company?.company_name || "Empresa"} | Driver: ${p.driver?.name || "N/A"}</span>
        </div>
      `).join("");
      listDiv.style.display = "block";
      addNegotiationLog(`✅ ${proposals.length} propostas encontradas`);
    } else {
      proposalsList.innerHTML = '<p style="color: var(--muted);">Nenhuma proposta recebida</p>';
      listDiv.style.display = "block";
    }
    write({ proposals: proposals.length, data: proposals.slice(0, 2) });
  } catch (error) {
    addNegotiationLog(`❌ Erro: ${error.message}`);
  }
}

function selectProposal(loadId, proposalId) {
  document.getElementById("acceptLoadId").value = loadId;
  document.getElementById("acceptProposalId").value = proposalId;
  negotiationState.loadId = loadId;
  negotiationState.proposalId = proposalId;
  addNegotiationLog(`💰 Proposta selecionada: Load=${loadId}, Proposta=${proposalId}`);
}

// 5. CLIENTE ACEITA PROPOSTA (cria Trip)
async function stepAcceptProposal(e) {
  e.preventDefault();
  setStatus("Aceitando proposta...");
  try {
    const formData = formObject(e.target);
    const loadId = formData.load_id;
    const proposalId = formData.proposal_id;
    
    if (!loadId || !proposalId) {
      alert("Selecione load e proposta");
      return;
    }
    
    const trip = await api(`/loads/${loadId}/proposals/${proposalId}/accept`, { 
      method: 'POST'
    });
    
    negotiationState.tripId = trip.id;
    updateNegotiationState(negotiationState);
    
    document.getElementById("startTripId").value = trip.id;
    addNegotiationLog(`✅ Proposta aceita! Trip criada: ID=${trip.id}, Status=${trip.status}`);
    write(trip);
  } catch (error) {
    addNegotiationLog(`❌ Erro: ${error.message}`);
    setStatus("Erro ao aceitar proposta");
  }
}

// 6. MOTORISTA VÊ VIAGENS
async function stepListTrips() {
  setStatus("Buscando viagens...");
  try {
    const trips = await api('/trips/me');
    const listDiv = document.getElementById("tripsListDiv");
    const tripsList = document.getElementById("tripsList");
    
    if (Array.isArray(trips) && trips.length > 0) {
      tripsList.innerHTML = trips.map(t => `
        <div style="padding: 6px 0; border-bottom: 1px solid var(--line); cursor: pointer;" onclick="selectTrip(${t.id})">
          <strong>Trip ID ${t.id}</strong> - Load ${t.load_id}
          <br><span style="color: #38bdf8;">Status: ${t.status}</span>
        </div>
      `).join("");
      listDiv.style.display = "block";
      addNegotiationLog(`✅ ${trips.length} viagens do motorista`);
    } else {
      tripsList.innerHTML = '<p style="color: var(--muted);">Nenhuma viagem</p>';
      listDiv.style.display = "block";
    }
    write({ trips: trips.length, data: trips.slice(0, 2) });
  } catch (error) {
    addNegotiationLog(`❌ Erro: ${error.message}`);
  }
}

function selectTrip(tripId) {
  document.getElementById("startTripId").value = tripId;
  negotiationState.tripId = tripId;
  addNegotiationLog(`🚗 Viagem selecionada: ID=${tripId}`);
}

// 7. MOTORISTA INICIA VIAGEM
async function stepStartTrip(e) {
  e.preventDefault();
  setStatus("Iniciando viagem...");
  try {
    const formData = formObject(e.target);
    const tripId = formData.trip_id;
    
    if (!tripId) {
      alert("Selecione uma viagem");
      return;
    }
    
    const payload = {};
    if (negotiationState.vehicleId) {
      payload.vehicle_id = negotiationState.vehicleId;
    }
    const trip = await api(`/trips/${tripId}/start`, {
      method: 'PATCH',
      json: payload
    });
    
    addNegotiationLog(`✅ Viagem iniciada! Status=${trip.status}`);
    write(trip);
  } catch (error) {
    addNegotiationLog(`❌ Erro: ${error.message}`);
    setStatus("Erro ao iniciar viagem");
  }
}

// DEMO COMPLETO
async function negotiationDemo() {
  setStatus("Iniciando demo do fluxo completo...");
  addNegotiationLog("🎬 Demo iniciada");
  
  try {
    syncFleetSelectionState();
    if (!negotiationState.driverId || !negotiationState.vehicleId) {
      await refreshProposalFleetOptions();
      syncFleetSelectionState();
    }
    if (!negotiationState.driverId || !negotiationState.vehicleId) {
      throw new Error("Selecione motorista e veículo antes de rodar o demo.");
    }

    // 1. Cliente publica carga
    addNegotiationLog("1️⃣ Cliente publicando carga...");
    const loadRes = await api('/loads', { 
      method: 'POST', 
      json: {
        load_type: "eletronica",
        load_name: "Demo - Componentes Eletrônicos",
        weight: 50,
        value: 50000,
        negotiable: true,
        origin: "Maputo",
        destination: "Beira",
        origin_lat: -25.9692,
        origin_lng: 32.5732,
        destination_lat: -19.8437,
        destination_lng: 34.8488,
        departure_date: new Date().toISOString().split('T')[0]
      }
    });
    negotiationState.loadId = loadRes.id;
    document.getElementById("proposalLoadId").value = loadRes.id;
    addNegotiationLog(`✅ Carga criada: ID=${loadRes.id}`);
    
    await new Promise(r => setTimeout(r, 1000));
    
    // 2. Empresa envia proposta
    addNegotiationLog("2️⃣ Empresa enviando proposta...");
    const proposalRes = await api(`/loads/${loadRes.id}/proposals`, { 
      method: 'POST',
      json: {
        proposed_value: 45000,
        driver_id: negotiationState.driverId,
        vehicle_id: negotiationState.vehicleId,
        message: "Proposta demo"
      }
    });
    negotiationState.proposalId = proposalRes.id;
    document.getElementById("acceptProposalId").value = proposalRes.id;
    addNegotiationLog(`✅ Proposta enviada: ID=${proposalRes.id}`);
    
    await new Promise(r => setTimeout(r, 1000));
    
    // 3. Cliente aceita proposta
    addNegotiationLog("3️⃣ Cliente aceitando proposta (Trip será criada)...");
    const tripRes = await api(`/loads/${loadRes.id}/proposals/${proposalRes.id}/accept`, { 
      method: 'POST'
    });
    negotiationState.tripId = tripRes.id;
    document.getElementById("startTripId").value = tripRes.id;
    addNegotiationLog(`✅ Trip criada: ID=${tripRes.id}, Status=${tripRes.status}`);
    
    await new Promise(r => setTimeout(r, 1000));
    
    // 4. Motorista inicia viagem
    addNegotiationLog("4️⃣ Motorista iniciando viagem...");
    const startPayload = {};
    if (negotiationState.vehicleId) {
      startPayload.vehicle_id = negotiationState.vehicleId;
    }
    const startRes = await api(`/trips/${tripRes.id}/start`, {
      method: 'PATCH',
      json: startPayload
    });
    addNegotiationLog(`✅ Viagem iniciada! Status=${startRes.status}`);
    
    updateNegotiationState(negotiationState);
    addNegotiationLog("🎉 Demo completo finalizado com sucesso!");
    write(negotiationState);
    
  } catch (error) {
    addNegotiationLog(`❌ Erro na demo: ${error.message}`);
    write({ error: error.message });
  }
}

applyMethodButtonClasses();
syncManualMethodSelect();
updateTokenState();
document.getElementById("proposalDriverId")?.addEventListener("change", () => {
  renderVehicleOptions();
  syncFleetSelectionState();
});
document.getElementById("proposalVehicleId")?.addEventListener("change", syncFleetSelectionState);
if (getToken()) {
  safeRun(refreshProposalFleetOptions);
}

// Simulador de GPS para testes
let gpsSimulator = null;

function startGPSSimulator() {
  if (gpsSimulator) {
    addChatMessage("error", "Simulador já está em execução");
    return;
  }
  
  if (!websocket || websocket.readyState !== WebSocket.OPEN) {
    addChatMessage("error", "WebSocket não conectado");
    return;
  }
  
  let lat = parseFloat(document.getElementById("driverLat").value) || -25.9692;
  let lng = parseFloat(document.getElementById("driverLng").value) || 32.5732;
  
  addChatMessage("success", "🚗 Simulador de GPS iniciado - atualiza a cada 3 segundos");
  
  gpsSimulator = setInterval(() => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      clearInterval(gpsSimulator);
      gpsSimulator = null;
      addChatMessage("error", "WebSocket desconectado - Simulador parado");
      return;
    }
    
    // Variar coordenadas ligeiramente (simular movimento)
    lat += (Math.random() - 0.5) * 0.001;
    lng += (Math.random() - 0.5) * 0.001;
    
    document.getElementById("driverLat").value = lat.toFixed(6);
    document.getElementById("driverLng").value = lng.toFixed(6);
    
    sendDriverLocation();
  }, 3000);
}

function stopGPSSimulator() {
  if (gpsSimulator) {
    clearInterval(gpsSimulator);
    gpsSimulator = null;
    addChatMessage("success", "Simulador de GPS parado");
  }
}

// Adicionar botão de simulador no HTML dinamicamente
document.addEventListener("DOMContentLoaded", () => {
  // Encontrar seção WebSocket e adicionar botões de simulador
  const tripIdWS = document.getElementById("tripIdWS");
  if (tripIdWS) {
    const container = tripIdWS.parentElement.parentElement;
    const simButtonsDiv = document.createElement("div");
    simButtonsDiv.className = "row-compact";
    simButtonsDiv.style.marginTop = "8px";
    simButtonsDiv.innerHTML = `
      <button onclick="startGPSSimulator()" class="method-post" style="background: rgba(251, 191, 36, 0.12); border-color: rgba(251, 191, 36, 0.45);">▶️ Simular GPS</button>
      <button onclick="stopGPSSimulator()" class="method-delete" style="background: rgba(248, 113, 113, 0.12); border-color: rgba(248, 113, 113, 0.45);">⏹️ Parar Simulador</button>
    `;
    container.insertBefore(simButtonsDiv, tripIdWS.parentElement.nextSibling);
  }
});
</script>
</body>
</html>"""
    )
