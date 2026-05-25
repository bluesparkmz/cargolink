"""
Constantes da aplicação CargoLink.
"""

# Tipos de carga (ecrã "Cadastrar nova carga")
LOAD_TYPES = [
    {"id": "areia", "label": "Areia"},
    {"id": "cimento", "label": "Cimento"},
    {"id": "cascalho", "label": "Cascalho"},
    {"id": "combustivel", "label": "Combustível"},
    {"id": "ferro", "label": "Ferro"},
    {"id": "madeira", "label": "Madeira"},
    {"id": "graos", "label": "Grãos"},
    {"id": "mercadoria_geral", "label": "Mercadoria geral"},
    {"id": "outro", "label": "Outro"},
]

LOAD_TYPE_IDS = {item["id"] for item in LOAD_TYPES}

LOAD_TYPE_LABELS = {item["id"]: item["label"] for item in LOAD_TYPES}

# Carga completa / meia carga (badge no detalhe)
LOAD_FILL_TYPES = [
    {"id": "completa", "label": "Carga completa"},
    {"id": "meia_carga", "label": "Meia carga"},
]
LOAD_FILL_IDS = {item["id"] for item in LOAD_FILL_TYPES}
LOAD_FILL_LABELS = {item["id"]: item["label"] for item in LOAD_FILL_TYPES}

# Velocidade média para estimativa de tempo de rota (km/h)
ROUTE_AVG_SPEED_KMH_MIN = 50
ROUTE_AVG_SPEED_KMH_MAX = 60

MAX_LOAD_IMAGES = 5

# Unidades de peso aceites
WEIGHT_UNITS = ["ton", "kg"]

# Estados da viagem
TRIP_STATUS_WAITING = "aguardando_inicio"
TRIP_STATUS_STARTED = "viagem_iniciada"
TRIP_STATUS_WAITING_CLIENT = "aguardando_cliente"
TRIP_STATUS_COMPLETED = "concluida"

# GPS da viagem: controla quantos pontos entram no historico da rota.
TRIP_LOCATION_MIN_INTERVAL_SECONDS = 10
TRIP_LOCATION_MIN_DISTANCE_METERS = 50
TRIP_LOCATION_HEARTBEAT_SECONDS = 120

# Filtros do app motorista (Minhas Viagens)
TRIP_GROUP_IN_PROGRESS = "em_andamento"
TRIP_GROUP_COMPLETED = "concluidas"

TRIP_GROUP_STATUSES = {
    TRIP_GROUP_IN_PROGRESS: [
        TRIP_STATUS_WAITING,
        TRIP_STATUS_STARTED,
        TRIP_STATUS_WAITING_CLIENT,
    ],
    TRIP_GROUP_COMPLETED: [TRIP_STATUS_COMPLETED],
}

# Tipos de paragem durante a viagem
STOP_TYPES = [
    {"id": "abastecimento", "label": "Abastecimento"},
    {"id": "descanso", "label": "Descanso"},
    {"id": "mecanica", "label": "Mecânica"},
    {"id": "outros", "label": "Outros"},
]

STOP_TYPE_IDS = {item["id"] for item in STOP_TYPES}

# Status de carga
LOAD_STATUS_AVAILABLE = "disponivel"
LOAD_STATUS_ACCEPTED = "aceite"
LOAD_STATUS_IN_TRANSIT = "em_viagem"
LOAD_STATUS_COMPLETED = "concluida"
LOAD_STATUS_CANCELLED = "cancelada"

LOAD_ACTIVE_STATUSES = [LOAD_STATUS_ACCEPTED, LOAD_STATUS_IN_TRANSIT]

# Status exibidos no feed de atividades do cliente
ACTIVITY_IN_PROGRESS = "em_andamento"
ACTIVITY_NEGOTIATING = "em_negociacao"
ACTIVITY_COMPLETED = "concluida"

# Status de propostas e negociacoes
PROPOSAL_STATUS_PENDING = "pendente"
PROPOSAL_STATUS_NEGOTIATING = "em_negociacao"
PROPOSAL_STATUS_ACCEPTED = "aceite"
PROPOSAL_STATUS_REJECTED = "recusada"
PROPOSAL_OPEN_STATUSES = [PROPOSAL_STATUS_PENDING, PROPOSAL_STATUS_NEGOTIATING]

NEGOTIATION_STATUS_PENDING = "pendente"
NEGOTIATION_STATUS_ACCEPTED = "aceite"
NEGOTIATION_STATUS_REJECTED = "recusada"
NEGOTIATION_STATUS_REPLACED = "substituida"

# Veículos
VEHICLE_STATUS_AVAILABLE = "disponivel"
VEHICLE_STATUS_UNAVAILABLE = "indisponivel"
VEHICLE_STATUS_MAINTENANCE = "manutencao"
VEHICLE_STATUS_INACTIVE = "inativo"
VEHICLE_STATUSES = {
    VEHICLE_STATUS_AVAILABLE,
    VEHICLE_STATUS_UNAVAILABLE,
    VEHICLE_STATUS_MAINTENANCE,
    VEHICLE_STATUS_INACTIVE,
}

# Carteira e pagamentos
TRANSACTION_TYPE_DEPOSIT = "deposito"
TRANSACTION_TYPE_WITHDRAWAL = "levantamento"
PAYMENT_METHOD_MPESA = "mpesa"
PAYMENT_STATUS_PENDING = "pendente"
PAYMENT_STATUS_COMPLETED = "concluido"
PAYMENT_STATUS_FAILED = "falhou"
TRANSACTION_STATUS_PENDING = "pendente"
TRANSACTION_STATUS_COMPLETED = "concluido"

# Tipos de documento (perfil)
DOCUMENT_TYPES = [
    {"id": "bi", "label": "Bilhete de Identidade"},
    {"id": "carta", "label": "Carta de condução"},
    {"id": "licenca", "label": "Licença / Alvará"},
    {"id": "nuit", "label": "NUIT / Documento fiscal"},
    {"id": "outro", "label": "Outro"},
]
DOCUMENT_TYPE_IDS = {item["id"] for item in DOCUMENT_TYPES}

DOCUMENT_STATUS_PENDING = "pendente"
DOCUMENT_STATUS_APPROVED = "aprovado"
DOCUMENT_STATUS_REJECTED = "rejeitado"
