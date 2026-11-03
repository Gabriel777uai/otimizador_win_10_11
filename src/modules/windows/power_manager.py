"""
Módulo de Gerenciamento de Energia do Windows.
Lista e aplica esquemas oficiais de energia via powercfg sem hacks obscuros.
"""
from typing import List, Dict, Any
from src.utils.logger import app_logger
from src.utils.command_runner import run_command
from src.core.safety_manager import safety_manager, RiskLevel

def list_power_schemes() -> List[Dict[str, Any]]:
    """Lista todos os esquemas de energia instalados no Windows."""
    schemes = []
    rc, out, _ = run_command(["powercfg", "/list"], timeout=10)
    if rc != 0:
        return schemes

    for line in out.splitlines():
        line = line.strip()
        if "GUID do Esquema de Energia:" in line or "Power Scheme GUID:" in line:
            is_active = "*" in line
            parts = line.split(":")
            if len(parts) > 1:
                sub = parts[1].strip()
                guid = sub.split("(")[0].strip()
                name = sub.split("(")[1].replace(")", "").replace("*", "").strip() if "(" in sub else "Plano de Energia"
                schemes.append({
                    "guid": guid,
                    "name": name,
                    "is_active": is_active
                })
    return schemes

def set_active_power_scheme(guid: str, user_confirmed: bool = False) -> Dict[str, Any]:
    """Define o plano de energia ativo."""
    auth = safety_manager.validate_and_authorize(
        op_id="SET_POWER_SCHEME",
        risk_level=RiskLevel.LEVEL_2_CONTROLLED,
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    app_logger.info(f"Alterando esquema de energia para {guid}...")
    rc, out, err = run_command(["powercfg", "/setactive", guid], timeout=10)
    if rc == 0:
        return {"success": True, "message": "Esquema de energia alterado com sucesso."}
    return {"success": False, "message": f"Falha ao definir esquema: {err or out}"}
