from pathlib import Path
from urllib.parse import urlparse
import os

from dotenv import load_dotenv

from src.shared.exceptions import SettingsException


class Settings:
    BASE_DIR = Path(__file__).resolve().parents[3]

    LOCAL_DOWNLOAD_DIR = BASE_DIR / "data" / "downloads"
    LOCAL_PROCESSED_DIR = BASE_DIR / "data" / "processed"
    LOCAL_SERVIDOR: Path | None = None
    SERVIDOR_SIRIUS_PATH: Path | None = None
    CARGA_SIRIUS_PATH: Path | None = None

    SFTP_HOST_SIRIUS: str | None = None
    SFTP_USER_SIRIUS: str | None = None
    SFTP_PASSWORD_SIRIUS: str | None = None
    SFTP_PORT_SIRIUS: int = 22
    SFTP_REMOTE_DIR_SIRIUS: str | None = None
    SFTP_ENVIO_HOST_SIRIUS: str | None = None
    SFTP_ENVIO_USER_SIRIUS: str | None = None
    SFTP_ENVIO_PASSWORD_SIRIUS: str | None = None
    SFTP_ENVIO_PORT_SIRIUS: int = 22
    SFTP_ENVIO_REMOTE_DIR_SIRIUS: str | None = None
    SFTP_ENVIO_SUBPASTA_SIRIUS: str | None = None

    SIRIUS_URL: str | None = None
    SIRIUS_USER: str | None = None
    SIRIUS_PASSWORD: str | None = None
    SIRIUS_TIMEOUT: int = 60000

    GPG_EXE: str = "gpg"
    GPG_RECIPIENT: str | None = None
    GPG_PUBLIC_KEY_PATH: str | None = None
    GPG_HOME: str | None = None

    UI_CONFIDENCE: float = 0.85
    TELEGRAM_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    @classmethod
    def _int_env(cls, name: str, default: int) -> int:
        value = os.getenv(name)
        if not value:
            return default
        return int(value)

    @classmethod
    def _float_env(cls, name: str, default: float) -> float:
        value = os.getenv(name)
        if not value:
            return default
        return float(value)

    @classmethod
    def _sanitize_host(cls, host: str) -> str:
        host = host.strip()
        if "://" in host:
            parsed = urlparse(host)
            if parsed.hostname:
                return parsed.hostname
        return host

    @classmethod
    def _path_env(cls, name: str) -> Path | None:
        value = os.getenv(name)
        if not value:
            return None
        normalized = value.strip().strip('"').strip("'")
        if not normalized:
            return None
        if normalized.startswith("\\") and not normalized.startswith("\\\\"):
            normalized = f"\\{normalized}"
        return Path(normalized)

    @classmethod
    def _refresh_env(cls) -> None:
        host_sirius = os.getenv("SFTP_HOST_SIRIUS")
        cls.SFTP_HOST_SIRIUS = cls._sanitize_host(host_sirius) if host_sirius else None
        cls.SFTP_USER_SIRIUS = os.getenv("SFTP_USER_SIRIUS")
        cls.SFTP_PASSWORD_SIRIUS = os.getenv("SFTP_PASSWORD_SIRIUS")
        cls.SFTP_PORT_SIRIUS = cls._int_env("SFTP_PORT_SIRIUS", 22)
        cls.SFTP_REMOTE_DIR_SIRIUS = os.getenv("SFTP_REMOTE_DIR_SIRIUS")
        host_envio_sirius = os.getenv("SFTP_ENVIO_HOST_SIRIUS")
        cls.SFTP_ENVIO_HOST_SIRIUS = (
            cls._sanitize_host(host_envio_sirius) if host_envio_sirius else cls.SFTP_HOST_SIRIUS
        )
        cls.SFTP_ENVIO_USER_SIRIUS = os.getenv("SFTP_ENVIO_USER_SIRIUS") or cls.SFTP_USER_SIRIUS
        cls.SFTP_ENVIO_PASSWORD_SIRIUS = (
            os.getenv("SFTP_ENVIO_PASSWORD_SIRIUS") or cls.SFTP_PASSWORD_SIRIUS
        )
        cls.SFTP_ENVIO_PORT_SIRIUS = cls._int_env("SFTP_ENVIO_PORT_SIRIUS", cls.SFTP_PORT_SIRIUS)
        cls.SFTP_ENVIO_REMOTE_DIR_SIRIUS = (
            os.getenv("SFTP_ENVIO_REMOTE_DIR_SIRIUS") or "/Importacao"
        )
        cls.SFTP_ENVIO_SUBPASTA_SIRIUS = (
            os.getenv("SFTP_ENVIO_SUBPASTA_SIRIUS") or "Sirius"
        )

        cls.LOCAL_SERVIDOR = cls._path_env("LOCAL_SERVIDOR")
        cls.SERVIDOR_SIRIUS_PATH = cls._path_env("SERVIDOR_SIRIUS")
        cls.CARGA_SIRIUS_PATH = cls._path_env("CARGA_SIRIUS")

        cls.SIRIUS_URL = os.getenv("SIRIUS_URL")
        cls.SIRIUS_USER = os.getenv("SIRIUS_USER")
        cls.SIRIUS_PASSWORD = os.getenv("SIRIUS_PASSWORD")
        cls.SIRIUS_TIMEOUT = cls._int_env("SIRIUS_TIMEOUT", 60000)

        cls.GPG_EXE = os.getenv("GPG_EXE", "gpg")
        cls.GPG_RECIPIENT = os.getenv("GPG_RECIPIENT")
        cls.GPG_PUBLIC_KEY_PATH = os.getenv("GPG_PUBLIC_KEY_PATH")
        cls.GPG_HOME = os.getenv("GPG_HOME")

        cls.UI_CONFIDENCE = cls._float_env("UI_CONFIDENCE", 0.85)
        cls.TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN")
        cls.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("ID_CHAT")

    @classmethod
    def load_env(cls) -> None:
        env_path = cls.BASE_DIR / ".env"
        if not env_path.exists():
            raise SettingsException(f"Arquivo .env nao encontrado em: {env_path}")

        load_dotenv(env_path)
        cls._refresh_env()

    @classmethod
    def validate(cls) -> None:
        cls.load_env()

        obrigatorias = {
            "SFTP_HOST_SIRIUS": cls.SFTP_HOST_SIRIUS,
            "SFTP_USER_SIRIUS": cls.SFTP_USER_SIRIUS,
            "SFTP_PASSWORD_SIRIUS": cls.SFTP_PASSWORD_SIRIUS,
            "SFTP_REMOTE_DIR_SIRIUS": cls.SFTP_REMOTE_DIR_SIRIUS,
            "SIRIUS_URL": cls.SIRIUS_URL,
            "SIRIUS_USER": cls.SIRIUS_USER,
            "SIRIUS_PASSWORD": cls.SIRIUS_PASSWORD,
            "GPG_RECIPIENT": cls.GPG_RECIPIENT,
            "GPG_PUBLIC_KEY_PATH": cls.GPG_PUBLIC_KEY_PATH,
            "LOCAL_SERVIDOR_OU_SERVIDOR_SIRIUS_OU_CARGA_SIRIUS": (
                cls.LOCAL_SERVIDOR or cls.SERVIDOR_SIRIUS_PATH or cls.CARGA_SIRIUS_PATH
            ),
            "SERVER_71": os.getenv("SERVER_71"),
            "SERVER_USER": os.getenv("SERVER_USER"),
            "SERVER_SENHA": os.getenv("SERVER_SENHA"),
        }

        faltando = [k for k, v in obrigatorias.items() if not v]
        if faltando:
            raise SettingsException(
                f"Variaveis obrigatorias ausentes no .env: {', '.join(faltando)}"
            )

        cls.LOCAL_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOCAL_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def conexao_71() -> dict:
    return {
        "ipServidor": os.getenv("SERVER_71"),
        "usuario": os.getenv("SERVER_USER"),
        "senha": os.getenv("SERVER_SENHA"),
    }


def conexao_66(banco: str = "DB_NAME") -> dict:
    return {
        "ipServidor": os.getenv("DB_66"),
        "banco": banco,
        "usuario": os.getenv("DB_USER"),
        "senha": os.getenv("DB_SENHA"),
    }
