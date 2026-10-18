"""IBM z/OS Connect configuration. Never put credentials in source control."""
import os
from dataclasses import dataclass
from aegis_backend.config import settings


def _env(name: str, fallback: str = "") -> str:
    value = os.getenv(name)
    return value if value is not None else fallback


@dataclass
class IBMZSettings:
    ENABLED: bool = True
    MOCK_MODE: bool = True
    ZOS_CONNECT_URL: str = ""
    CICS_TRAN_ID: str = "AEG1"
    SYSPLEX_NODE: str = "PLEX1.ZOS25.CICS55"
    TIMEOUT_SECONDS: float = 5.0
    API_KEY: str = ""
    AUTH_MODE: str = "bearer"
    USERNAME: str = ""
    PASSWORD: str = ""
    TOKEN: str = ""
    API_KEY_HEADER: str = "X-IBM-Client-Id"
    EVALUATE_PATH: str = "/EvaluateEmergencyDecision"
    CAPACITY_PATH: str = "/SyncEmergencyCapacity"
    STATUS_PATH: str = "/"

    def __init__(self):
        self.ENABLED = _env("AEGIS_IBM_Z_ENABLED", str(getattr(settings, "IBM_Z_ENABLED", True))).lower() in ("1", "true", "yes", "on")
        self.MOCK_MODE = _env("AEGIS_IBM_Z_MOCK_MODE", str(getattr(settings, "IBM_Z_MOCK_MODE", True))).lower() in ("1", "true", "yes", "on")
        self.ZOS_CONNECT_URL = _env("AEGIS_IBM_Z_CONNECT_URL", getattr(settings, "IBM_Z_CONNECT_URL", "") or "").strip().rstrip("/")
        self.CICS_TRAN_ID = _env("AEGIS_IBM_Z_CICS_TRAN_ID", getattr(settings, "IBM_Z_CICS_TRAN_ID", "AEG1"))
        self.SYSPLEX_NODE = _env("AEGIS_IBM_Z_SYSPLEX_NODE", "PLEX1.ZOS25.CICS55")
        self.TIMEOUT_SECONDS = float(_env("AEGIS_IBM_Z_TIMEOUT_SECONDS", str(getattr(settings, "IBM_Z_TIMEOUT_SECONDS", 5.0))))
        self.API_KEY = _env("AEGIS_IBM_Z_API_KEY", getattr(settings, "IBM_Z_API_KEY", "") or "")
        self.AUTH_MODE = _env("AEGIS_IBM_Z_AUTH_MODE", "bearer").lower().strip()
        self.USERNAME = _env("AEGIS_IBM_Z_USERNAME")
        self.PASSWORD = _env("AEGIS_IBM_Z_PASSWORD")
        self.TOKEN = _env("AEGIS_IBM_Z_TOKEN")
        self.API_KEY_HEADER = _env("AEGIS_IBM_Z_API_KEY_HEADER", "X-IBM-Client-Id")
        self.EVALUATE_PATH = _env("AEGIS_IBM_Z_EVALUATE_PATH", "/EvaluateEmergencyDecision")
        self.CAPACITY_PATH = _env("AEGIS_IBM_Z_CAPACITY_PATH", "/SyncEmergencyCapacity")
        self.STATUS_PATH = _env("AEGIS_IBM_Z_STATUS_PATH", "/")


ibm_z_settings = IBMZSettings()
