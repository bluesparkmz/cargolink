from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# ---------------------------------------------------------------------------
# 1. Utilizadores
# ---------------------------------------------------------------------------


class User(Base):
    """Tabela users — conta principal (cliente, motorista, admin)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column("nome", String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(150), unique=True)
    phone: Mapped[str] = mapped_column("telefone", String(30), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column("senha_hash", Text, nullable=False)
    user_type: Mapped[str] = mapped_column("tipo", String(30), nullable=False)
    profile_photo: Mapped[str | None] = mapped_column("foto_perfil", Text)
    status: Mapped[str] = mapped_column(String(30), default="ativo")
    verified: Mapped[bool] = mapped_column("verificado", Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped[Client | None] = relationship(back_populates="user", uselist=False)
    driver: Mapped[Driver | None] = relationship(back_populates="user", uselist=False)
    documents: Mapped[list[Document]] = relationship(back_populates="user")
    notifications: Mapped[list[Notification]] = relationship(back_populates="user")


# ---------------------------------------------------------------------------
# 2. Cliente
# ---------------------------------------------------------------------------


class Client(Base):
    """Tabela clients — perfil do utilizador tipo cliente."""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    client_type: Mapped[str] = mapped_column("tipo_cliente", String(30), default="individual")
    company_name: Mapped[str | None] = mapped_column("nome_empresa", String(150))
    tax_id: Mapped[str | None] = mapped_column("nuit", String(50))
    address: Mapped[str | None] = mapped_column("endereco", Text)
    city: Mapped[str | None] = mapped_column("cidade", String(100))
    state: Mapped[str | None] = mapped_column("provincia", String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="client")
    loads: Mapped[list[Load]] = relationship(back_populates="client")


# ---------------------------------------------------------------------------
# 3. Motorista e veículos
# ---------------------------------------------------------------------------


class Driver(Base):
    """Tabela drivers — perfil do motorista."""

    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    license_number: Mapped[str | None] = mapped_column("numero_carta", String(100))
    license_expiry: Mapped[date | None] = mapped_column("validade_carta", Date)
    years_experience: Mapped[int] = mapped_column("experiencia_anos", Integer, default=0)
    average_rating: Mapped[Decimal] = mapped_column("avaliacao_media", Numeric(3, 2), default=0)
    total_trips: Mapped[int] = mapped_column("total_viagens", Integer, default=0)
    available: Mapped[bool] = mapped_column("disponivel", Boolean, default=True)
    current_lat: Mapped[Decimal | None] = mapped_column("latitude_atual", Numeric(10, 7))
    current_lng: Mapped[Decimal | None] = mapped_column("longitude_atual", Numeric(10, 7))
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="driver")
    vehicles: Mapped[list[Vehicle]] = relationship(back_populates="driver")
    proposals: Mapped[list[LoadProposal]] = relationship(back_populates="driver")
    trips: Mapped[list[Trip]] = relationship(back_populates="driver")


class Vehicle(Base):
    """Tabela vehicles — veículos do motorista."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id", ondelete="CASCADE"))
    plate: Mapped[str] = mapped_column("matricula", String(50), unique=True, nullable=False)
    brand: Mapped[str | None] = mapped_column("marca", String(100))
    model_name: Mapped[str | None] = mapped_column("modelo", String(100))
    vehicle_type: Mapped[str | None] = mapped_column("tipo", String(100))
    tonnage_capacity: Mapped[Decimal | None] = mapped_column("capacidade_toneladas", Numeric(10, 2))
    volume_capacity: Mapped[Decimal | None] = mapped_column("capacidade_volume", Numeric(10, 2))
    photo: Mapped[str | None] = mapped_column("foto", Text)
    status: Mapped[str] = mapped_column(String(30), default="disponivel")
    current_lat: Mapped[Decimal | None] = mapped_column("latitude_atual", Numeric(10, 7))
    current_lng: Mapped[Decimal | None] = mapped_column("longitude_atual", Numeric(10, 7))
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    driver: Mapped[Driver] = relationship(back_populates="vehicles")
    trips: Mapped[list[Trip]] = relationship(back_populates="vehicle")


# ---------------------------------------------------------------------------
# 4. Documentos
# ---------------------------------------------------------------------------


class Document(Base):
    """Tabela documents — BI, carta, licenças."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    document_type: Mapped[str] = mapped_column("tipo", String(50), nullable=False)
    file_url: Mapped[str] = mapped_column("arquivo_url", Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pendente")
    notes: Mapped[str | None] = mapped_column("observacao", Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="documents")


# ---------------------------------------------------------------------------
# 5–8. Cargas, imagens e propostas
# ---------------------------------------------------------------------------


class Load(Base):
    """Tabela loads — cargas publicadas pelo cliente."""

    __tablename__ = "loads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column("codigo", String(30), unique=True, nullable=False)
    load_type: Mapped[str] = mapped_column("tipo_carga", String(100), nullable=False)
    load_name: Mapped[str | None] = mapped_column("nome_carga", String(150))
    description: Mapped[str | None] = mapped_column("descricao", Text)
    weight: Mapped[Decimal | None] = mapped_column("peso", Numeric(10, 2))
    weight_unit: Mapped[str | None] = mapped_column("peso_unidade", String(20), default="ton")
    volume: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    value: Mapped[Decimal | None] = mapped_column("valor", Numeric(12, 2))
    negotiable: Mapped[bool] = mapped_column("negociavel", Boolean, default=True)
    origin: Mapped[str] = mapped_column("origem", String(150), nullable=False)
    destination: Mapped[str] = mapped_column("destino", String(150), nullable=False)
    origin_lat: Mapped[Decimal | None] = mapped_column("origem_lat", Numeric(10, 7))
    origin_lng: Mapped[Decimal | None] = mapped_column("origem_lng", Numeric(10, 7))
    destination_lat: Mapped[Decimal | None] = mapped_column("destino_lat", Numeric(10, 7))
    destination_lng: Mapped[Decimal | None] = mapped_column("destino_lng", Numeric(10, 7))
    departure_date: Mapped[date | None] = mapped_column("data_saida", Date)
    load_fill: Mapped[str | None] = mapped_column("tipo_carga_volume", String(30))
    suggested_vehicle_type: Mapped[str | None] = mapped_column("tipo_veiculo_sugerido", String(150))
    instructions: Mapped[str | None] = mapped_column("instrucoes", Text)
    status: Mapped[str] = mapped_column(String(40), default="disponivel")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped[Client] = relationship(back_populates="loads")
    images: Mapped[list[LoadImage]] = relationship(back_populates="load")
    proposals: Mapped[list[LoadProposal]] = relationship(back_populates="load")
    trip: Mapped[Trip | None] = relationship(back_populates="load", uselist=False)
    messages: Mapped[list[Message]] = relationship(back_populates="load")
    payments: Mapped[list[Payment]] = relationship(back_populates="load")


class LoadImage(Base):
    """Tabela load_images — fotos da carga."""

    __tablename__ = "load_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    load_id: Mapped[int] = mapped_column(ForeignKey("loads.id", ondelete="CASCADE"))
    image_url: Mapped[str] = mapped_column("imagem_url", Text, nullable=False)
    is_primary: Mapped[bool] = mapped_column("principal", Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    load: Mapped[Load] = relationship(back_populates="images")


class LoadProposal(Base):
    """Tabela load_proposals — propostas do motorista."""

    __tablename__ = "load_proposals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    load_id: Mapped[int] = mapped_column(ForeignKey("loads.id", ondelete="CASCADE"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id", ondelete="CASCADE"))
    proposed_value: Mapped[Decimal | None] = mapped_column("valor_proposto", Numeric(12, 2))
    message: Mapped[str | None] = mapped_column("mensagem", Text)
    status: Mapped[str] = mapped_column(String(30), default="pendente")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    load: Mapped[Load] = relationship(back_populates="proposals")
    driver: Mapped[Driver] = relationship(back_populates="proposals")


# ---------------------------------------------------------------------------
# 9–10. Viagens e localização
# ---------------------------------------------------------------------------


class Trip(Base):
    """Tabela trips — viagem após aceite de proposta."""

    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    load_id: Mapped[int] = mapped_column(ForeignKey("loads.id", ondelete="CASCADE"), unique=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id"))
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"))
    status: Mapped[str] = mapped_column(String(40), default="aguardando_inicio")
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime)
    client_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    total_distance_km: Mapped[Decimal | None] = mapped_column("distancia_total_km", Numeric(10, 2))
    traveled_distance_km: Mapped[Decimal | None] = mapped_column(
        "distancia_percorrida_km", Numeric(10, 2)
    )
    estimated_time: Mapped[str | None] = mapped_column("tempo_estimado", Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    load: Mapped[Load] = relationship(back_populates="trip")
    driver: Mapped[Driver | None] = relationship(back_populates="trips")
    vehicle: Mapped[Vehicle | None] = relationship(back_populates="trips")
    locations: Mapped[list[TripLocation]] = relationship(back_populates="trip")
    stops: Mapped[list["TripStop"]] = relationship(back_populates="trip")
    ratings: Mapped[list[Rating]] = relationship(back_populates="trip")
    fuel_requests: Mapped[list[FuelRequest]] = relationship(back_populates="trip")


class TripLocation(Base):
    """Tabela trip_locations — GPS em tempo real."""

    __tablename__ = "trip_locations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    speed: Mapped[Decimal | None] = mapped_column("velocidade", Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    trip: Mapped[Trip] = relationship(back_populates="locations")


class TripStop(Base):
    """Tabela trip_stops — paragens durante a viagem (abastecimento, descanso, etc.)."""

    __tablename__ = "trip_stops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    stop_type: Mapped[str] = mapped_column("tipo", String(50), nullable=False)
    location_name: Mapped[str | None] = mapped_column("nome_local", String(150))
    address: Mapped[str | None] = mapped_column("endereco", Text)
    notes: Mapped[str | None] = mapped_column("observacao", Text)
    stopped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    trip: Mapped[Trip] = relationship(back_populates="stops")


# ---------------------------------------------------------------------------
# 11–12. Carteira (só modelo; sem rotas)
# ---------------------------------------------------------------------------


class Wallet(Base):
    """Tabela wallets — saldos (lógica futura)."""

    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    available_balance: Mapped[Decimal] = mapped_column("saldo_disponivel", Numeric(12, 2), default=0)
    pending_balance: Mapped[Decimal] = mapped_column("saldo_pendente", Numeric(12, 2), default=0)
    blocked_balance: Mapped[Decimal] = mapped_column("saldo_bloqueado", Numeric(12, 2), default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    transactions: Mapped[list[Transaction]] = relationship(back_populates="wallet")
    withdrawals: Mapped[list[Withdrawal]] = relationship(back_populates="wallet")


class Transaction(Base):
    """Tabela transactions — movimentos na carteira."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id", ondelete="CASCADE"))
    transaction_type: Mapped[str] = mapped_column("tipo", String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column("valor", Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pendente")
    reference: Mapped[str | None] = mapped_column("referencia", String(100))
    description: Mapped[str | None] = mapped_column("descricao", Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    wallet: Mapped[Wallet] = relationship(back_populates="transactions")


# ---------------------------------------------------------------------------
# 13. Pagamentos
# ---------------------------------------------------------------------------


class Payment(Base):
    """Tabela payments — M-Pesa e outros."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    load_id: Mapped[int | None] = mapped_column(ForeignKey("loads.id"))
    method: Mapped[str | None] = mapped_column("metodo", String(50))
    phone: Mapped[str | None] = mapped_column("telefone", String(30))
    amount: Mapped[Decimal] = mapped_column("valor", Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pendente")
    external_reference: Mapped[str | None] = mapped_column("referencia_externa", String(100))
    gateway_response: Mapped[dict | None] = mapped_column("resposta_gateway", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    load: Mapped[Load | None] = relationship(back_populates="payments")


# ---------------------------------------------------------------------------
# 14–15. Combustível
# ---------------------------------------------------------------------------


class FuelRequest(Base):
    """Tabela fuel_requests — pedido de combustível na viagem."""

    __tablename__ = "fuel_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id"))
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("trips.id"))
    liters: Mapped[Decimal] = mapped_column("litros", Numeric(10, 2), nullable=False)
    price_per_liter: Mapped[Decimal] = mapped_column("preco_litro", Numeric(10, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column("valor_total", Numeric(12, 2), nullable=False)
    gas_station: Mapped[str | None] = mapped_column("posto", String(150))
    status: Mapped[str] = mapped_column(String(30), default="pendente")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    trip: Mapped[Trip | None] = relationship(back_populates="fuel_requests")


class FuelPrice(Base):
    """Tabela fuel_prices — preço por tipo de combustível."""

    __tablename__ = "fuel_prices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fuel_type: Mapped[str] = mapped_column("tipo_combustivel", String(50), nullable=False)
    price_per_liter: Mapped[Decimal] = mapped_column("preco_litro", Numeric(10, 2), nullable=False)
    active: Mapped[bool] = mapped_column("ativo", Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# 16–17. Mensagens e notificações
# ---------------------------------------------------------------------------


class Message(Base):
    """Tabela messages — chat sobre uma carga."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    load_id: Mapped[int] = mapped_column(ForeignKey("loads.id", ondelete="CASCADE"))
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    receiver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column("mensagem", Text, nullable=False)
    attachment: Mapped[str | None] = mapped_column("anexo", Text)
    read: Mapped[bool] = mapped_column("lida", Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    load: Mapped[Load] = relationship(back_populates="messages")


class Notification(Base):
    """Tabela notifications — alertas in-app."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column("titulo", String(150), nullable=False)
    body: Mapped[str] = mapped_column("mensagem", Text, nullable=False)
    notification_type: Mapped[str | None] = mapped_column("tipo", String(50))
    read: Mapped[bool] = mapped_column("lida", Boolean, default=False)
    payload: Mapped[dict | None] = mapped_column("data", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="notifications")


# ---------------------------------------------------------------------------
# 18. Avaliações
# ---------------------------------------------------------------------------


class Rating(Base):
    """Tabela ratings — nota 1 a 5 após viagem."""

    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    rater_id: Mapped[int | None] = mapped_column("avaliador_id", ForeignKey("users.id"))
    rated_user_id: Mapped[int | None] = mapped_column("avaliado_id", ForeignKey("users.id"))
    score: Mapped[int | None] = mapped_column("nota", Integer)
    comment: Mapped[str | None] = mapped_column("comentario", Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    trip: Mapped[Trip] = relationship(back_populates="ratings")


# ---------------------------------------------------------------------------
# 19. Saques
# ---------------------------------------------------------------------------


class Withdrawal(Base):
    """Tabela withdrawals — levantamento (lógica futura)."""

    __tablename__ = "withdrawals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    wallet_id: Mapped[int | None] = mapped_column(ForeignKey("wallets.id"))
    method: Mapped[str] = mapped_column("metodo", String(50), default="mpesa")
    phone: Mapped[str | None] = mapped_column("telefone", String(30))
    amount: Mapped[Decimal] = mapped_column("valor", Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pendente")
    external_reference: Mapped[str | None] = mapped_column("referencia_externa", String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    wallet: Mapped[Wallet | None] = relationship(back_populates="withdrawals")


# ---------------------------------------------------------------------------
# 20. Configurações do sistema
# ---------------------------------------------------------------------------


class SystemSetting(Base):
    """Tabela system_settings — chave/valor editável pelo admin."""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column("chave", String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column("valor", Text, nullable=False)
    description: Mapped[str | None] = mapped_column("descricao", Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
