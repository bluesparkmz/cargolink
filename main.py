"""
Ponto de entrada da API CargoLink.
Inicializa FastAPI, rotas e tabelas na base de dados.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routers.auth import router as auth_router
from routers.clients import router as clients_router
from routers.documents import router as documents_router
from routers.drivers import router as drivers_router
from routers.loads import router as loads_router
from routers.driver_trips import router as driver_trips_router
from routers.messages import router as messages_router
from routers.notifications import router as notifications_router
from routers.stats import router as stats_router
from routers.trips import router as trips_router
from routers.users import router as users_router
from routers.vehicles import router as vehicles_router
from routers.wallet import router as wallet_router

# Importa modelos para o SQLAlchemy registar todas as tabelas
import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cria tabelas ao arrancar (em dev; em produção usar migrações Alembic)."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="CargoLink API",
    description="API base — modelos completos e autenticação JWT",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cada router é registado aqui, um ficheiro por domínio
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(users_router, prefix="/users", tags=["Users"])
app.include_router(clients_router, prefix="/clients", tags=["Clients"])
app.include_router(documents_router, prefix="/documents", tags=["Documents"])
app.include_router(drivers_router, prefix="/drivers", tags=["Drivers"])
app.include_router(loads_router, prefix="/loads", tags=["Loads"])
app.include_router(trips_router, prefix="/trips", tags=["Trips"])
app.include_router(driver_trips_router, prefix="/driver/trips", tags=["Driver"])
app.include_router(stats_router, prefix="/stats", tags=["Stats"])
app.include_router(vehicles_router, prefix="/vehicles", tags=["Vehicles"])
app.include_router(wallet_router, prefix="/wallet", tags=["Wallet"])
app.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
app.include_router(messages_router, prefix="/messages", tags=["Messages"])


@app.get("/")
def root():
    """Health check simples."""
    return {"app": "CargoLink", "status": "ok"}
