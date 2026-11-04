"""
Gerenciador do Microsoft Copilot - ALTUS PC OPTIMIZER.
Verifica instalação, consumo, visibilidade do botão na barra de tarefas,
políticas administrativas e desativação segura com rollback no Auto Recovery Center.
"""
import winreg
from typing import Dict, Any, Optional
from src.utils.logger import app_logger
from src.utils.command_runner import run_command
from src.core.safety_manager import safety_manager
from src.core.recovery_manager import register_recovery_operation
from .feature_detector import detect_copilot_status

def get_copilot_status() -> Dict[str, Any]:
    """Retorna estado completo e detalhado do Microsoft Copilot."""
    status = detect_copilot_status()
    return {
        "installed": status["installed"],
        "taskbar_visible": status["taskbar_visible"],
        "policy_disabled": status["policy_disabled"],
        "active_processes": status["active_processes"],
        "can_disable": status["installed"] or status["taskbar_visible"],
        "description": "Assistente de IA integrado ao Windows 11 e Edge que executa telemetria e processos em segundo plano."
    }

def configure_copilot(disable: bool, user_confirmed: bool = False) -> Dict[str, Any]:
    """
    Configura o Microsoft Copilot (desativação ou ativação)
    ajustando o botão da barra de tarefas e as políticas de grupo com rollback.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="TOGGLE_COPILOT",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    sub_key_adv = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    sub_key_pol = r"Software\Policies\Microsoft\Windows\WindowsCopilot"

    # 1. Lê estado original do botão da barra de tarefas
    orig_button_val = None
    orig_button_type = "REG_DWORD"
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key_adv, 0, winreg.KEY_READ)
        orig_button_val, _ = winreg.QueryValueEx(k, "ShowCopilotButton")
        winreg.CloseKey(k)
    except Exception:
        pass

    # 2. Lê estado original da política
    orig_pol_val = None
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key_pol, 0, winreg.KEY_READ)
        orig_pol_val, _ = winreg.QueryValueEx(k, "TurnOffWindowsCopilot")
        winreg.CloseKey(k)
    except Exception:
        pass

    # Registra no Auto Recovery Center
    record_id = register_recovery_operation(
        op_id="TOGGLE_COPILOT",
        category="COPILOT",
        original_state={
            "root": "HKCU",
            "sub_key": sub_key_adv,
            "value_name": "ShowCopilotButton",
            "value_data": orig_button_val,
            "value_type": orig_button_type
        },
        applied_state={"disabled": disable},
        restore_strategy="RESTORE_REGISTRY_VALUE",
        status="IN_PROGRESS"
    )

    try:
        # Aplica visibilidade do botão na barra de tarefas
        new_button_val = 0 if disable else 1
        k_adv = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_key_adv)
        winreg.SetValueEx(k_adv, "ShowCopilotButton", 0, winreg.REG_DWORD, new_button_val)
        winreg.CloseKey(k_adv)

        # Aplica política de desligamento do Copilot
        new_pol_val = 1 if disable else 0
        k_pol = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_key_pol)
        winreg.SetValueEx(k_pol, "TurnOffWindowsCopilot", 0, winreg.REG_DWORD, new_pol_val)
        winreg.CloseKey(k_pol)

        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "APPLIED")

        action_msg = "desativado com sucesso (botão oculto e política aplicada)" if disable else "reativado com sucesso"
        app_logger.info(f"Copilot {action_msg}. Registro: {record_id}")
        return {
            "success": True,
            "message": f"Microsoft Copilot foi {action_msg}.",
            "record_id": record_id
        }
    except Exception as e:
        app_logger.error(f"Erro ao configurar Copilot: {e}")
        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "FAILED", str(e))
        return {"success": False, "message": f"Falha ao configurar Copilot: {e}"}
