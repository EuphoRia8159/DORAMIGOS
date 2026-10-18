"""AEGIS Backend Configuration Module.

Loads configuration with 'AEGIS_' environment variable prefix.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for AEGIS Emergency Care Orchestration Platform."""
    
    # Application Info
    APP_NAME: str = "AEGIS — Emergency Care Orchestration API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server Binding
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Database
    DATABASE_URL: str = "sqlite:///./aegis.db"
    
    # Recommendation Engine Weights
    WEIGHT_CAPABILITY: float = 0.35
    WEIGHT_TRAVEL_TIME: float = 0.25
    WEIGHT_BED_AVAILABILITY: float = 0.20
    WEIGHT_ER_CONGESTION: float = 0.15
    WEIGHT_IBM_Z_VERIFIED: float = 0.05
    
    # Ambulance Speed & Traffic Configuration
    AVERAGE_AMBULANCE_SPEED_KMH: float = 45.0
    RUSH_HOUR_TRAFFIC_MULTIPLIER: float = 1.35
    
    # Simulation Defaults
    SIMULATION_INTERVAL_SECONDS: float = 3.0
    AUTO_SIMULATION_ENABLED: bool = True
    
    # IBM Z Integration Layer
    IBM_Z_ENABLED: bool = True
    IBM_Z_MOCK_MODE: bool = True
    IBM_Z_CONNECT_URL: str = "https://zosconnect.enterprise.internal:9443/zosConnect/services"
    IBM_Z_CICS_TRAN_ID: str = "AEG1"
    IBM_Z_TIMEOUT_SECONDS: float = 3.5
    IBM_Z_API_KEY: str = ""
    
    model_config = SettingsConfigDict(
        env_prefix="AEGIS_",
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
