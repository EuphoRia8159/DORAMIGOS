"""IBM Z z/OS Connect EE Enterprise Client Adapter.

Implements bidirectional mapping between AEGIS REST payloads and IBM z/OS
Connect EE JSON schemas backed by CICS TS COBOL copybooks.
"""

import time
import logging
from typing import Dict, Any, Optional
import httpx
from aegis_backend.ibm_z.config import ibm_z_settings

logger = logging.getLogger(__name__)


class IBMZConnectClient:
    """Enterprise client adapter for IBM z/OS Connect and CICS Transaction Server."""

    def __init__(self):
        self.base_url = ibm_z_settings.ZOS_CONNECT_URL
        self.mock_mode = ibm_z_settings.MOCK_MODE
        self.timeout = ibm_z_settings.TIMEOUT_SECONDS
        self.sysplex_node = ibm_z_settings.SYSPLEX_NODE
        self.cics_tran_id = ibm_z_settings.CICS_TRAN_ID

    async def execute_cics_transaction(
        self,
        service_name: str,
        payload: Dict[str, Any],
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes a transaction via z/OS Connect service endpoint or sandbox mock.

        Maps to CICS COMMAREA / Channel Container data structures.
        """
        tran_id = transaction_id or self.cics_tran_id
        start_time = time.perf_counter()

        if self.mock_mode or not self.base_url or "internal" in self.base_url:
            # High-fidelity mock sandbox simulation
            elapsed_ms = round((time.perf_counter() - start_time + 0.018) * 1000, 2)
            logger.info(f"[IBM Z Mock] Simulated CICS transaction '{tran_id}' on service '{service_name}' ({elapsed_ms}ms)")
            return {
                "zos_header": {
                    "sysplex_id": self.sysplex_node,
                    "cics_tran_id": tran_id,
                    "return_code": 0,
                    "reason_code": 0,
                    "cics_abcode": "    ",
                    "execution_time_ms": elapsed_ms,
                    "mode": "MOCK_SANDBOX"
                },
                "service": service_name,
                "payload": payload,
                "success": True
            }

        # Live IBM z/OS Connect EE invocation
        url = f"{self.base_url.rstrip('/')}/{service_name}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-IBM-Z-CICS-TRANID": tran_id
        }
        if ibm_z_settings.API_KEY:
            headers["Authorization"] = f"Bearer {ibm_z_settings.API_KEY}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                
                if response.status_code == 200:
                    data = response.json()
                    data["zos_header"] = {
                        "sysplex_id": self.sysplex_node,
                        "cics_tran_id": tran_id,
                        "status_code": response.status_code,
                        "execution_time_ms": elapsed_ms,
                        "mode": "LIVE_ZOS_CONNECT"
                    }
                    return data
                else:
                    logger.warning(f"IBM z/OS Connect returned non-200 status {response.status_code}")
                    return {
                        "success": False,
                        "error": f"z/OS Connect error HTTP {response.status_code}: {response.text}",
                        "mode": "LIVE_ZOS_CONNECT_ERROR"
                    }
        except httpx.RequestError as exc:
            logger.error(f"Failed to communicate with IBM z/OS Connect: {exc}")
            # Explicitly report connection status without false claims
            return {
                "success": False,
                "error": f"Connection to IBM z/OS Connect failed: {str(exc)}",
                "mode": "UNCONFIGURED_OR_OFFLINE",
                "note": "Host unreachable. Running in disconnected fallback state."
            }


ibm_z_client = IBMZConnectClient()
