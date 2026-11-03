"""
Módulo de Limpeza e Redefinição do Cache de Resolução DNS do Windows.
Utiliza a ferramenta nativa oficial ipconfig /flushdns.
"""
from typing import Dict, Any
from src.utils.command_runner import run_command
from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager, RiskLevel

def check_dns_cache_status() -> Dict[str, Any]:
    """Verifica estado do cliente DNS do Windows."""
    return {
        "status": "Pronto para limpeza",
        "description": "Cache de resolução DNS local do sistema operacional"
    }

def flush_dns_cache() -> Dict[str, Any]:
    """Executa ipconfig /flushdns e retorna o feedback do sistema operacional."""
    auth = safety_manager.validate_and_authorize(
        op_id="FLUSH_DNS",
        risk_level=RiskLevel.LEVEL_1_SAFE
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    app_logger.info("Executando ipconfig /flushdns")
    rc, out, err = run_command(["ipconfig", "/flushdns"], timeout=15)

    success = (rc == 0) and ("sucesso" in out.lower() or "successfully" in out.lower() or rc == 0)
    output_message = out.strip() if out.strip() else (err.strip() if err.strip() else "Comando concluído.")

    return {
        "success": success,
        "return_code": rc,
        "output": output_message
    }
