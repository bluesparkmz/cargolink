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
    STORAGE_DIR: str
    GOOGLE_CLIENT_IDS: list[str]
    MPESA_HOST: str
    MPESA_BEARER_TOKEN: str
    MPESA_SERVICE_PROVIDER_CODE: str


settings = Settings()
settings.DATABASE_URL = os.getenv("DATABASE_URL")
settings.SECRET_KEY = os.getenv("SECRET_KEY", "altere-esta-chave-em-producao")
settings.ALGORITHM = os.getenv("ALGORITHM", "HS256")
settings.ACCESS_TOKEN_EXPIRE_MINUTES = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24)
settings.AUTO_CONFIRM_MPESA_DEPOSITS = _env_bool("AUTO_CONFIRM_MPESA_DEPOSITS", True)
settings.STORAGE_DIR = os.getenv("STORAGE_DIR", "/storage")
settings.GOOGLE_CLIENT_IDS = [
    client_id.strip()
    for client_id in os.getenv(
        "GOOGLE_CLIENT_IDS",
        "750540528154-m9c1ee1gd8mfia95egfv2atlpbqhhki4.apps.googleusercontent.com",
    ).split(",")
    if client_id.strip()
]

# M-Pesa Sandbox Configuration
settings.MPESA_HOST = os.getenv("MPESA_HOST", "https://api.sandbox.vm.co.mz")
settings.MPESA_BEARER_TOKEN = os.getenv(
    "MPESA_BEARER_TOKEN",
    "UELjHuIUTK0VelJ68L4gx95py5nLmoMhCL0R2iL/Q7N0IOzqmDS/MD6vvfeb6koVeKlmZoY/ritM44pY7g4TQKhKNm/CI7UwWgwkENIAUlV0m6mhU8KaSVILG8mmJsk21wJEJxLjNJQnLDyn+hQfMh/DxEOv4ZCid0crCRFtC/H6FWR9aQHnfbTMsnZVreKWDWFGbElQzVFAFfLHocC5Z+vv1ehY5uF92nUFuI7jnCHEsTsXWTpaa8BgXA93Qv/dVpyoCBM3fonCJ1OioIV04A3lkseuWX+6CpOnQVoHl/bKYlNwjd7yArRI7xlwWtbxt7Wz+RNJZDd1gzP2LnyXY++8z/naZ/sPTx56wHweYHJoeiveeKwWMUZ9k6pgF8Ka+ejRjl9U04AZQ4MFmabXKvf6sP+/ZHtcoGrQK7e9H9L5rzGtfp2fdCVRt/KpxHqfYGJWhpstmvAEQfsV+hPbVER4GSO3Rf+a+ECbaWbp7dBbOCkYXbb9dpvcAeZd6ACF4y8o9ClUPm1o3gOq1h9dB7jKbL4TAyBC1pTmtAefnTHv3gj2z0iRDquuDI7cMrcoL/3IEesYBouuR849/QA91Vo+M7YRdHjOnDys/5oYyVlMXPpm3bMxprS+hwiyfHlRNiA6rIGyJZNpuFummIgjmSb90bczaWmAz7WsOSYqZ4g=",
)
settings.MPESA_SERVICE_PROVIDER_CODE = os.getenv("MPESA_SERVICE_PROVIDER_CODE", "171717")
