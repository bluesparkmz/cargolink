"""
Configurações da aplicação CargoLink.
Carrega variáveis de ambiente para base de dados e JWT.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parâmetros globais lidos do ficheiro .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Base de dados PostgreSQL
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/cargolink"

    # JWT
    SECRET_KEY: str = "altere-esta-chave-em-producao"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas

    # Em dev confirma depósitos M-Pesa automaticamente; em produção usar webhook/callback
    AUTO_CONFIRM_MPESA_DEPOSITS: bool = True


settings = Settings()
