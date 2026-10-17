"""AEGIS API Routers Package."""

from aegis_backend.routers import (
    hospitals,
    ambulances,
    emergencies,
    recommendations,
    simulation_api,
    ibm_z_api,
    analytics,
)

__all__ = [
    "hospitals",
    "ambulances",
    "emergencies",
    "recommendations",
    "simulation_api",
    "ibm_z_api",
    "analytics",
]
