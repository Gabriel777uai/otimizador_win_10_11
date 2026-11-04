"""
Gerenciador do Windows Recall - ALTUS PC OPTIMIZER.
Verifica compatibilidade estrita de hardware (Copilot+ PC), NPU e versão do SO.
Permite desativação controlada com confirmação especial de segurança e rollback.
"""
import winreg
from typing import Dict, Any
from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager
from src.core.recovery_manager import register_recovery_operation
from .feature_detector import detect_os_details, detect_recall_status

def get_recall_status() -> Dict[str, Any]:
    """Retorna diagnóstico de compatibilidade e estado do Windows Recall."""
    os_info = detect_os_details()
    st = detect_recall_status(os_info)
    return {
        "hardware_compatible": st["hardware_compatible"],
        "available": st["available"],
        "disabled": st["disabled"],
        "notes": st["notes"],
        "can_disable": st["available"] and not st["disabled"],
        "can_enable": st["available"] and st["disabled"],
        "description": "Recurso de IA do Windows 11 24H2 que tira instantâneos fotográficos periódicos da tela para busca semântica."
    }

def configure_recall(disable: bool, user_confirmed: bool = False) -> Dict[str, Any]:
    """
    Configura a política de desativação ou reativação do Windows Recall
    com exigência de confirmação explícita devido ao impacto em instantâneos salvos.
    """
    status = get_recall_status()
    if not status["hardware_compatible"]:
        return {
            "success": False,
            "message": f"Operação não permitida: {status['notes']}"
        }

    auth = safety_manager.validate_and_authorize(
        op_id="TOGGLE_RECALL",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    sub_key = r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI"
    orig_val = None
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key, 0, winreg.KEY_READ)
        orig_val, _ = winreg.QueryValueEx(k, "DisableAIDataAnalysis")
        winreg.CloseKey(k)
    except Exception:
        pass

    record_id = register_recovery_operation(
        op_id="TOGGLE_RECALL",
        category="RECALL",
        original_state={
            "root": "HKLM",
            "sub_key": sub_key,
            "value_name": "DisableAIDataAnalysis",
            "value_data": orig_val,
            "value_type": "REG_DWORD"
        },
        applied_state={"disabled": disable},
        restore_strategy="RESTORE_REGISTRY_VALUE",
        status="IN_PROGRESS"
    )

    try:
        new_val = 1 if disable else 0
        k = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, sub_key)
        winreg.SetValueEx(k, "DisableAIDataAnalysis", 0, winreg.REG_DWORD, new_val)
        winreg.CloseKey(k)

        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "APPLIED")

        action_msg = "desativado com sucesso (captura de instantâneos suspensa)" if disable else "reativado"
        app_logger.info(f"Windows Recall {action_msg}. Registro: {record_id}")
        return {
            "success": True,
            "message": f"Windows Recall foi {action_msg}.",
            "record_id": record_id
        }
    except Exception as e:
        app_logger.error(f"Erro ao configurar Windows Recall: {e}")
        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "FAILED", str(e))
        return {"success": False, "message": f"Falha ao configurar Windows Recall: {e}"}
