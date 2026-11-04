"""
Módulo de Recuperação do Windows Background Control - ALTUS PC OPTIMIZER.
Integra com o Auto Recovery Center para listar, auditar e reverter modificações
de registro, políticas, serviços e perfis de segundo plano.
"""
from typing import Dict, Any, List
from src.utils.logger import app_logger
from src.core.recovery_manager import load_ledger, rollback_operation

BACKGROUND_CATEGORIES = {
    "COPILOT", "RECALL", "EDGE", "TELEMETRY", "WIDGETS",
    "GAMING_DVR", "SEARCH_INDEX", "DELIVERY_OPTIMIZATION",
    "BACKGROUND_APPS", "SERVICE", "PROFILE"
}

def get_background_recovery_history() -> List[Dict[str, Any]]:
    """Retorna apenas as operações de recuperação vinculadas ao Windows Background Control."""
    ledger = load_ledger()
    return [r for r in ledger if r.get("category") in BACKGROUND_CATEGORIES]

def restore_background_operation(record_id: str) -> Dict[str, Any]:
    """Reverte individualmente uma operação registrada."""
    return rollback_operation(record_id)

def restore_all_background_optimizations() -> Dict[str, Any]:
    """
    Restaura em sequência todas as modificações ativas do Windows Background Control,
    recuperando o estado original registrado no ledger.
    """
    history = get_background_recovery_history()
    active_records = [r for r in history if r.get("status") in ("APPLIED", "IN_PROGRESS")]

    reverted = 0
    errors = []

    for r in active_records:
        rec_id = r["record_id"]
        res = rollback_operation(rec_id)
        if res.get("success"):
            reverted += 1
        else:
            errors.append(f"{rec_id}: {res.get('message')}")

    if not active_records:
        return {"success": True, "message": "Nenhuma alteração pendente de reversão no momento."}

    app_logger.info(f"Restauração global concluída: {reverted}/{len(active_records)} revertidas.")
    return {
        "success": len(errors) == 0 or reverted > 0,
        "message": f"{reverted} alterações foram restauradas com sucesso." + (f" ({len(errors)} erros)" if errors else ""),
        "reverted_count": reverted,
        "errors": errors
    }
