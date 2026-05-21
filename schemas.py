"""
Schemas Pydantic CargoLink — validação de entrada e saída da API.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from constants import VEHICLE_STATUS_AVAILABLE


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Dados para criar nova conta."""

    name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=8, max_length=30)
    password: str = Field(..., min_length=6, max_length=128)
    user_type: Literal["cliente", "motorista"] = "cliente"
    email: EmailStr | None = None
    client_type: str | None = "individual"
    company_name: str | None = None
    city: str | None = None
    state: str | None = None


class LoginRequest(BaseModel):
    """Credenciais de login (telefone + senha)."""

    phone: str
    password: str


class PasswordChangeRequest(BaseModel):
    """Alterar senha (ecrã Segurança do perfil)."""

    current_password: str = Field(..., min_length=6, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    """Resposta com JWT após login ou registo."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Dados públicos do utilizador autenticado."""

    id: int
    name: str
    email: str | None
    phone: str
    user_type: str
    status: str
    verified: bool
    profile_photo: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Utilizadores
# ---------------------------------------------------------------------------


class UserUpdateRequest(BaseModel):
    """Atualização dos dados base do utilizador."""

    name: str | None = Field(None, min_length=2, max_length=150)
    email: EmailStr | None = None
    profile_photo: str | None = None


class ClientProfileResponse(BaseModel):
    """Perfil cliente ligado ao utilizador."""

    id: int
    client_type: str
    company_name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None

    model_config = {"from_attributes": True}


class DriverProfileResponse(BaseModel):
    """Perfil motorista ligado ao utilizador."""

    id: int
    license_number: str | None = None
    license_expiry: date | None = None
    years_experience: int
    average_rating: float
    total_trips: int
    available: bool
    current_lat: float | None = None
    current_lng: float | None = None
    location_updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserProfileResponse(UserResponse):
    """Utilizador com perfil cliente ou motorista."""

    client: ClientProfileResponse | None = None
    driver: DriverProfileResponse | None = None


class ClientProfileUpdateRequest(BaseModel):
    """Atualização do perfil cliente."""

    client_type: str | None = None
    company_name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None


class DriverProfileUpdateRequest(BaseModel):
    """Atualização do perfil motorista."""

    license_number: str | None = None
    license_expiry: date | None = None
    years_experience: int | None = None
    available: bool | None = None


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------


class ClientUserSummary(BaseModel):
    """Dados públicos do utilizador ligado ao cliente."""

    id: int
    name: str
    phone: str
    email: str | None = None
    profile_photo: str | None = None
    verified: bool

    model_config = {"from_attributes": True}


class ClientDetailResponse(ClientProfileResponse):
    """Cliente com dados do utilizador."""

    user: ClientUserSummary


class ClientListItem(BaseModel):
    """Item resumido na listagem de clientes."""

    id: int
    user_id: int
    name: str
    client_type: str
    city: str | None = None
    company_name: str | None = None
    verified: bool

    model_config = {"from_attributes": True}


class ClientStatsResponse(BaseModel):
    """Cards Minhas atividades no perfil do cliente."""

    published_count: int
    in_progress_count: int
    completed_count: int
    average_rating: float | None = None
    rating_count: int = 0


class AvailabilityUpdateRequest(BaseModel):
    """Alterar disponibilidade do motorista."""

    available: bool


class LocationUpdateRequest(BaseModel):
    """Atualizar posição GPS no mapa."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    sync_vehicles: bool = Field(
        True,
        description="Ao atualizar motorista, replica coords nos camiões disponíveis",
    )


# ---------------------------------------------------------------------------
# Motoristas
# ---------------------------------------------------------------------------


class DriverUserSummary(BaseModel):
    """Dados públicos do utilizador ligado ao motorista."""

    id: int
    name: str
    phone: str
    email: str | None = None
    profile_photo: str | None = None
    verified: bool

    model_config = {"from_attributes": True}


class DriverDetailResponse(DriverProfileResponse):
    """Motorista com dados do utilizador."""

    user: DriverUserSummary


class DriverListItem(BaseModel):
    """Item resumido na listagem de motoristas."""

    id: int
    user_id: int
    name: str
    average_rating: float
    total_trips: int
    available: bool
    profile_photo: str | None = None
    verified: bool
    current_lat: float | None = None
    current_lng: float | None = None
    location_updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Cargas
# ---------------------------------------------------------------------------


class LoadImageResponse(BaseModel):
    """Imagem associada à carga."""

    id: int
    image_url: str
    is_primary: bool

    model_config = {"from_attributes": True}


class LoadImageCreateRequest(BaseModel):
    """Adicionar imagem à carga."""

    image_url: str
    is_primary: bool = False


class LoadTypeItem(BaseModel):
    """Tipo de carga para o selector do app."""

    id: str
    label: str


class LoadFillTypeItem(BaseModel):
    """Carga completa / meia carga."""

    id: str
    label: str


class LoadCreateRequest(BaseModel):
    """Publicar nova carga (passos 1–3 do app num único pedido)."""

    load_type: str = Field(..., min_length=2, max_length=100)
    load_name: str | None = None
    description: str | None = None
    weight: float | None = None
    weight_unit: str | None = "ton"
    volume: float | None = None
    value: float | None = None
    negotiable: bool = True
    origin: str = Field(..., min_length=2, max_length=150)
    destination: str = Field(..., min_length=2, max_length=150)
    origin_lat: float | None = None
    origin_lng: float | None = None
    destination_lat: float | None = None
    destination_lng: float | None = None
    departure_date: date | None = None
    load_fill: str | None = None
    suggested_vehicle_type: str | None = Field(None, max_length=150)
    instructions: str | None = None
    images: list[LoadImageCreateRequest] | None = None


class LoadUpdateRequest(BaseModel):
    """Atualizar carga existente."""

    load_type: str | None = None
    load_name: str | None = None
    description: str | None = None
    weight: float | None = None
    weight_unit: str | None = None
    volume: float | None = None
    value: float | None = None
    negotiable: bool | None = None
    origin: str | None = None
    destination: str | None = None
    origin_lat: float | None = None
    origin_lng: float | None = None
    destination_lat: float | None = None
    destination_lng: float | None = None
    departure_date: date | None = None
    load_fill: str | None = None
    suggested_vehicle_type: str | None = Field(None, max_length=150)
    instructions: str | None = None
    status: str | None = None


class LoadResponse(BaseModel):
    """Resposta padrão de uma carga."""

    id: int
    client_id: int
    code: str
    load_type: str
    load_name: str | None = None
    description: str | None = None
    weight: float | None = None
    weight_unit: str | None = None
    volume: float | None = None
    value: float | None = None
    negotiable: bool
    origin: str
    destination: str
    origin_lat: float | None = None
    origin_lng: float | None = None
    destination_lat: float | None = None
    destination_lng: float | None = None
    departure_date: date | None = None
    load_fill: str | None = None
    suggested_vehicle_type: str | None = None
    instructions: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LoadSenderSummary(BaseModel):
    """Remetente (cliente) no detalhe da carga."""

    client_id: int
    user_id: int
    name: str
    phone: str
    email: str | None = None
    profile_photo: str | None = None
    verified: bool
    average_rating: float | None = None
    rating_count: int = 0


class LoadRouteEstimate(BaseModel):
    """Distância e tempo estimados (mapa da secção Rota)."""

    distance_km: float | None = None
    estimated_time_min: int | None = None
    estimated_time_label: str | None = None


class LoadDetailResponse(LoadResponse):
    """Detalhe completo para o ecrã Detalhes da Carga."""

    images: list[LoadImageResponse] = []
    load_type_label: str | None = None
    load_fill_label: str | None = None
    sender: LoadSenderSummary
    route: LoadRouteEstimate | None = None
    proposals_count: int = 0


class LoadListItem(BaseModel):
    """Item resumido na listagem de cargas."""

    id: int
    code: str
    load_type: str
    load_name: str | None = None
    origin: str
    destination: str
    origin_lat: float | None = None
    origin_lng: float | None = None
    destination_lat: float | None = None
    destination_lng: float | None = None
    weight: float | None = None
    weight_unit: str | None = None
    value: float | None = None
    negotiable: bool
    status: str
    departure_date: date | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LoadProposalCreateRequest(BaseModel):
    """Proposta do motorista para uma carga."""

    proposed_value: float | None = None
    message: str | None = None


class LoadProposalResponse(BaseModel):
    """Proposta registada."""

    id: int
    load_id: int
    driver_id: int
    proposed_value: float | None = None
    message: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Viagens
# ---------------------------------------------------------------------------


class TripResponse(BaseModel):
    """Viagem após aceite de proposta."""

    id: int
    load_id: int
    driver_id: int | None
    vehicle_id: int | None
    status: str
    started_at: datetime | None = None
    arrived_at: datetime | None = None
    client_confirmed_at: datetime | None = None
    completed_at: datetime | None = None
    total_distance_km: float | None = None
    traveled_distance_km: float | None = None
    estimated_time: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TripStartRequest(BaseModel):
    """Iniciar viagem (opcional: veículo e distância estimada)."""

    vehicle_id: int | None = None
    total_distance_km: float | None = None
    estimated_time: str | None = None


class TripLocationCreateRequest(BaseModel):
    """Ponto GPS durante a viagem."""

    latitude: float
    longitude: float
    speed: float | None = None
    traveled_distance_km: float | None = None


class TripLocationResponse(BaseModel):
    """Localização registada."""

    id: int
    trip_id: int
    latitude: float
    longitude: float
    speed: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# App motorista — viagens e paragens
# ---------------------------------------------------------------------------


class StopTypeItem(BaseModel):
    """Tipo de paragem para o selector do app."""

    id: str
    label: str


class TripStopCreateRequest(BaseModel):
    """Registar paragem na viagem."""

    stop_type: str
    location_name: str | None = None
    address: str | None = None
    notes: str | None = None
    stopped_at: datetime | None = None


class TripStopResponse(BaseModel):
    """Paragem registada."""

    id: int
    trip_id: int
    stop_type: str
    location_name: str | None = None
    address: str | None = None
    notes: str | None = None
    stopped_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class TripDriverListItem(BaseModel):
    """Item da lista Minhas Viagens (motorista)."""

    id: int
    load_code: str
    origin: str
    destination: str
    client_name: str
    status: str
    started_at: datetime | None = None
    estimated_time: str | None = None
    departure_date: date | None = None
    created_at: datetime


class TripDriverDetailResponse(TripResponse):
    """Detalhe da viagem para o motorista."""

    load_code: str
    load_type: str
    origin: str
    destination: str
    client_name: str
    client_phone: str | None = None
    progress_percent: float | None = None
    stops: list[TripStopResponse] = []


# ---------------------------------------------------------------------------
# Documentos
# ---------------------------------------------------------------------------


class DocumentTypeItem(BaseModel):
    """Tipo de documento para upload."""

    id: str
    label: str


class DocumentCreateRequest(BaseModel):
    """Registar documento (URL do ficheiro já enviado ao storage)."""

    document_type: str = Field(..., min_length=2, max_length=50)
    file_url: str = Field(..., min_length=10)
    notes: str | None = None


class DocumentResponse(BaseModel):
    """Documento do utilizador."""

    id: int
    user_id: int
    document_type: str
    file_url: str
    status: str
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Dashboard / estatísticas
# ---------------------------------------------------------------------------


class DashboardStatsResponse(BaseModel):
    """Contagens para os cards do ecrã inicial."""

    available_loads: int
    active_loads: int
    completed_this_month: int
    available_vehicles: int


# ---------------------------------------------------------------------------
# Veículos (camiões)
# ---------------------------------------------------------------------------


class VehicleListItem(BaseModel):
    """Camião disponível na listagem horizontal."""

    id: int
    driver_id: int
    plate: str
    brand: str | None = None
    model_name: str | None = None
    vehicle_type: str | None = None
    tonnage_capacity: float | None = None
    photo: str | None = None
    status: str
    current_lat: float | None = None
    current_lng: float | None = None
    location_updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class VehicleDetailResponse(VehicleListItem):
    """Detalhe do veículo com dados do motorista."""

    driver_name: str
    driver_rating: float


class VehicleCreateRequest(BaseModel):
    """Motorista regista novo camião."""

    plate: str = Field(..., min_length=3, max_length=50)
    brand: str | None = Field(None, max_length=100)
    model_name: str | None = Field(None, max_length=100)
    vehicle_type: str | None = Field(None, max_length=100)
    tonnage_capacity: float | None = Field(None, gt=0)
    photo: str | None = None
    status: str = VEHICLE_STATUS_AVAILABLE
    current_lat: float | None = Field(None, ge=-90, le=90)
    current_lng: float | None = Field(None, ge=-180, le=180)


class VehicleUpdateRequest(BaseModel):
    """Atualização parcial do veículo."""

    plate: str | None = Field(None, min_length=3, max_length=50)
    brand: str | None = None
    model_name: str | None = None
    vehicle_type: str | None = None
    tonnage_capacity: float | None = Field(None, gt=0)
    photo: str | None = None
    status: str | None = None
    current_lat: float | None = Field(None, ge=-90, le=90)
    current_lng: float | None = Field(None, ge=-180, le=180)


# ---------------------------------------------------------------------------
# Carteira
# ---------------------------------------------------------------------------


class WalletBalanceResponse(BaseModel):
    """Saldo da carteira do utilizador."""

    available_balance: float
    pending_balance: float
    blocked_balance: float
    currency: str = "MT"


class WalletTransactionResponse(BaseModel):
    """Movimento no extrato."""

    id: int
    transaction_type: str
    amount: float
    status: str
    reference: str | None = None
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WalletDepositRequest(BaseModel):
    """Pedido de depósito via M-Pesa (+ no app)."""

    amount: float = Field(..., gt=0, le=5_000_000)
    phone: str | None = Field(None, min_length=8, max_length=30)
    method: Literal["mpesa"] = "mpesa"


class WalletDepositResponse(BaseModel):
    """Resposta após iniciar depósito."""

    payment_id: int
    transaction_id: int
    amount: float
    status: str
    external_reference: str
    phone: str
    message: str


# ---------------------------------------------------------------------------
# Notificações
# ---------------------------------------------------------------------------


class NotificationResponse(BaseModel):
    """Alerta in-app."""

    id: int
    title: str
    body: str
    notification_type: str | None = None
    read: bool
    payload: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    """Contagem de não lidas (sino do app)."""

    count: int


# ---------------------------------------------------------------------------
# Mensagens
# ---------------------------------------------------------------------------


class MessageCreateRequest(BaseModel):
    """Enviar mensagem numa conversa da carga."""

    receiver_id: int = Field(..., gt=0)
    body: str = Field(..., min_length=1, max_length=5000)
    attachment: str | None = None


class MessageResponse(BaseModel):
    """Mensagem no chat."""

    id: int
    load_id: int
    sender_id: int | None
    receiver_id: int | None
    body: str
    attachment: str | None = None
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    """Resumo para lista de conversas."""

    load_id: int
    load_code: str
    other_user_id: int
    other_user_name: str
    last_message: str | None = None
    last_message_at: datetime | None = None
    unread_count: int


class MessagesSummaryResponse(BaseModel):
    """Badge total de mensagens não lidas."""

    unread_count: int


# ---------------------------------------------------------------------------
# Atividades recentes (cliente)
# ---------------------------------------------------------------------------


class ActivityItem(BaseModel):
    """Item do feed Atividades recentes."""

    load_id: int
    code: str
    origin: str
    destination: str
    load_type: str
    weight: float | None = None
    weight_unit: str | None = None
    display_status: str
    activity_at: datetime
    trip_id: int | None = None


# ---------------------------------------------------------------------------
# Rastreio de carga
# ---------------------------------------------------------------------------


class LoadTrackingResponse(BaseModel):
    """Rastreio por carga — viagem e GPS."""

    load_id: int
    load_code: str
    load_status: str
    trip_id: int | None = None
    trip_status: str | None = None
    trackable: bool
    locations: list[TripLocationResponse] = []
    last_location: TripLocationResponse | None = None
