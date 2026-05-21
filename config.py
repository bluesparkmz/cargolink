"""
Configurações da aplicação CargoLink.
Lê variáveis de ambiente com os.getenv (sem ficheiro .env automático).
"""

import os


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


class Settings:
    """Parâmetros globais da API."""

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    AUTO_CONFIRM_MPESA_DEPOSITS: bool


settings = Settings()
settings.DATABASE_URL = os.getenv("DATABASE_URL")
settings.SECRET_KEY = os.getenv("SECRET_KEY", "altere-esta-chave-em-producao")
settings.ALGORITHM = os.getenv("ALGORITHM", "HS256")
settings.ACCESS_TOKEN_EXPIRE_MINUTES = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24)
settings.AUTO_CONFIRM_MPESA_DEPOSITS = _env_bool("AUTO_CONFIRM_MPESA_DEPOSITS", True)
