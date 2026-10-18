"""Configurable IBM z/OS Connect HTTP adapter.

Live mode never silently falls back to mock. Configure the deployed API's
actual URL, paths, authentication, and JSON contract with your IBM admin.
"""
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx

from aegis_backend.ibm_z.config import ibm_z_settings

logger = logging.getLogger(__name__)


class IBMZConnectClient:
    def __init__(self):
        self.refresh_config()

    def refresh_config(self):
        cfg = ibm_z_settings
        self.base_url = cfg.ZOS_CONNECT_URL
        self.mock_mode = cfg.MOCK_MODE
        self.timeout = cfg.TIMEOUT_SECONDS
        self.sysplex_node = "UNVERIFIED"
        self.cics_tran_id = cfg.CICS_TRAN_ID

    def _path_for(self, service_name: str) -> str:
        cfg = ibm_z_settings
        paths = {
            "EvaluateEmergencyDecision": cfg.EVALUATE_PATH,
            "SyncEmergencyCapacity": cfg.CAPACITY_PATH,
        }
        # Use explicit configured path; unknown services use their name.
        return paths.get(service_name, "/" + service_name)

    def _auth(self):
        cfg = ibm_z_settings
        mode = cfg.AUTH_MODE
        if mode == "bearer":
            token = cfg.TOKEN or cfg.API_KEY
            if not token:
                raise RuntimeError("Live mode requires AEGIS_IBM_Z_TOKEN (Bearer token).")
            return {"Authorization": f"Bearer {token}"}, None
        if mode in ("api_key", "apikey"):
            if not cfg.API_KEY:
                raise RuntimeError("Live mode requires AEGIS_IBM_Z_API_KEY.")
            return {cfg.API_KEY_HEADER: cfg.API_KEY}, None
        if mode == "basic":
            if not cfg.USERNAME or not cfg.PASSWORD:
                raise RuntimeError("Basic auth requires AEGIS_IBM_Z_USERNAME and AEGIS_IBM_Z_PASSWORD.")
            return {}, (cfg.USERNAME, cfg.PASSWORD)
        if mode in ("none", "no_auth"):
            return {}, None
        raise RuntimeError("Unsupported AEGIS_IBM_Z_AUTH_MODE. Use bearer, api_key, basic, or none.")

    async def execute_cics_transaction(
        self,
        service_name: str,
        payload: Dict[str, Any],
        transaction_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cfg = ibm_z_settings
        tran_id = transaction_id or cfg.CICS_TRAN_ID
        started = time.perf_counter()

        if not cfg.ENABLED:
            return {"success": False, "mode": "DISABLED", "error": "IBM Z integration is disabled."}

        if cfg.MOCK_MODE:
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            logger.warning("IBM Z MOCK request: service=%s; no live IBM call was made", service_name)
            return {
                "success": True,
                "service": service_name,
                "payload": payload,
                "zos_header": {
                    "sysplex_id": "MOCK_ONLY",
                    "cics_tran_id": tran_id,
                    "return_code": 0,
                    "reason_code": 0,
                    "execution_time_ms": elapsed,
                    "mode": "MOCK_SANDBOX",
                },
            }

        if not cfg.ZOS_CONNECT_URL:
            return {
                "success": False,
                "mode": "LIVE_CONFIGURATION_ERROR",
                "error": "AEGIS_IBM_Z_CONNECT_URL is missing; no request was sent.",
            }

        try:
            auth_headers, basic_auth = self._auth()
        except RuntimeError as exc:
            return {"success": False, "mode": "LIVE_CONFIGURATION_ERROR", "error": str(exc)}

        path = self._path_for(service_name)
        url = cfg.ZOS_CONNECT_URL.rstrip("/") + "/" + path.lstrip("/")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-IBM-Z-CICS-TRANID": tran_id,
            **auth_headers,
        }

        try:
            async with httpx.AsyncClient(timeout=cfg.TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload, headers=headers, auth=basic_auth)
            elapsed = round((time.perf_counter() - started) * 1000, 2)

            if not 200 <= response.status_code < 300:
                logger.warning("IBM z/OS Connect HTTP status=%s service=%s", response.status_code, service_name)
                return {
                    "success": False,
                    "mode": "LIVE_ZOS_CONNECT_ERROR",
                    "status_code": response.status_code,
                    "service": service_name,
                    "latency_ms": elapsed,
                    "error": response.text[:1000],
                }

            try:
                data = response.json()
            except ValueError:
                data = {"raw_response": response.text[:1000]}

            if not isinstance(data, dict):
                data = {"response": data}

            # A successful HTTP response does not prove the business transaction
            # succeeded; preserve the response's own business status if present.
            data["zos_header"] = {
                "cics_tran_id": tran_id,
                "status_code": response.status_code,
                "execution_time_ms": elapsed,
                "mode": "LIVE_ZOS_CONNECT",
                "endpoint": url,
            }
            data.setdefault("success", True)
            return data

        except httpx.TimeoutException:
            logger.exception("IBM z/OS Connect request timed out")
            return {"success": False, "mode": "LIVE_ZOS_CONNECT_ERROR", "error": "IBM endpoint request timed out."}
        except httpx.RequestError as exc:
            logger.warning("IBM z/OS Connect connection failed: %s", type(exc).__name__)
            return {
                "success": False,
                "mode": "LIVE_ZOS_CONNECT_ERROR",
                "error": f"Could not connect to configured IBM endpoint ({type(exc).__name__}). Check host, network, TLS, and credentials.",
            }


ibm_z_client = IBMZConnectClient()
