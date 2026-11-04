"""
Gerenciador de Otimização de Entrega (Delivery Optimization) - ALTUS PC OPTIMIZER.
Permite desativar o compartilhamento P2P de atualizações pela internet/rede local (DODownloadMode=0),
garantindo download 100% oficial e direto dos servidores da Microsoft sem consumir upload do usuário.
Preserva integralmente o serviço Windows Update e BITS.
"""
import winreg
from typing import Dict, Any
from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager
from src.core.recovery_manager import register_recovery_operation
from .feature_detector import detect_delivery_optimization

def get_delivery_optimization_status() -> Dict[str, Any]:
    """Retorna estado do modo de entrega do Windows Update e P2P."""
    st = detect_delivery_optimization()
    mode_names = {
        0: "HTTP Apenas (Direto da Microsoft - Sem P2P / Recomendado)",
        1: "P2P em Rede Local (LAN apenas)",
        2: "P2P em Grupo / Domínio",
        3: "P2P na Internet (Envia partes de atualizações para a web)",
        99: "Modo Bypass"
    }
    return {
        "mode": st["mode"],
        "mode_description": mode_names.get(st["mode"], "Padrão do Sistema"),
        "is_p2p_disabled": st["is_p2p_disabled"],
        "can_optimize": not st["is_p2p_disabled"],
        "description": "Por padrão, o Windows pode usar sua conexão e upload para enviar atualizações para outros computadores."
    }

def configure_delivery_optimization(
    disable_p2p_sharing: bool = True,
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    Define DODownloadMode para 0 (HTTP Direto da Microsoft) sem desativar o serviço DoSvc nem o Windows Update.
    Registra no Auto Recovery Center para rollback imediato.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="CONFIGURE_DELIVERY_OPTIMIZATION",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    sub_key = r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization"
    orig_mode = None
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key, 0, winreg.KEY_READ)
        orig_mode, _ = winreg.QueryValueEx(k, "DODownloadMode")
        winreg.CloseKey(k)
    except Exception:
        pass

    record_id = register_recovery_operation(
        op_id="CONFIGURE_DELIVERY_OPTIMIZATION",
        category="DELIVERY_OPTIMIZATION",
        original_state={
            "root": "HKLM",
            "sub_key": sub_key,
            "value_name": "DODownloadMode",
            "value_data": orig_mode,
            "value_type": "REG_DWORD"
        },
        applied_state={"disable_p2p_sharing": disable_p2p_sharing},
        restore_strategy="RESTORE_REGISTRY_VALUE",
        status="IN_PROGRESS"
    )

    try:
        new_mode = 0 if disable_p2p_sharing else 1
        k = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, sub_key)
        winreg.SetValueEx(k, "DODownloadMode", 0, winreg.REG_DWORD, new_mode)
        winreg.CloseKey(k)

        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "APPLIED")

        mode_txt = "P2P desativado (Download direto da Microsoft)" if disable_p2p_sharing else "P2P habilitado"
        app_logger.info(f"Otimização de Entrega configurada: {mode_txt}. Registro: {record_id}")
        return {
            "success": True,
            "message": f"Otimização de Entrega atualizada com sucesso: {mode_txt}.",
            "record_id": record_id
        }
    except Exception as e:
        app_logger.error(f"Erro ao configurar Delivery Optimization: {e}")
        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "FAILED", str(e))
        return {"success": False, "message": f"Falha ao configurar Delivery Optimization: {e}"}
