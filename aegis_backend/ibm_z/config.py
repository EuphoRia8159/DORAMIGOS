"""IBM Z Enterprise Integration Configuration."""

from aegis_backend.config import settings


class IBMZSettings:
    """Settings specific to IBM Z z/OS Connect and CICS transactions."""

    ENABLED: bool = settings.IBM_Z_ENABLED
    MOCK_MODE: bool = settings.IBM_Z_MOCK_MODE
    ZOS_CONNECT_URL: str = settings.IBM_Z_CONNECT_URL
    CICS_TRAN_ID: str = settings.IBM_Z_CICS_TRAN_ID
    TIMEOUT_SECONDS: float = settings.IBM_Z_TIMEOUT_SECONDS
    API_KEY: str = settings.IBM_Z_API_KEY
    SYSPLEX_NODE: str = "PLEX1.ZOS25.CICS55"

    # COBOL Copybook definitions for documentation & schema verification
    PATIENT_COPYBOOK_NAME: str = "CPYEMERG"
    CAPACITY_COPYBOOK_NAME: str = "CPYCAPAC"


ibm_z_settings = IBMZSettings()
