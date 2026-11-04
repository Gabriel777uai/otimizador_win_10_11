"""
Gerenciador de Widgets, Notícias e Sugestões do Windows - ALTUS PC OPTIMIZER.
Permite ocultar o painel de Widgets da barra de tarefas e desativar propagandas/dicas
nativas do sistema, preservando componentes essenciais do Windows Shell e Store.
"""
import winreg
from typing import Dict, Any
from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager
from src.core.recovery_manager import register_recovery_operation
from .feature_detector import detect_widgets_and_suggestions

def get_widget_status() -> Dict[str, Any]:
    """Retorna estado dos widgets e sugestões do Windows."""
    st = detect_widgets_and_suggestions()
    return {
        "widgets_visible": st["widgets_visible"],
        "suggestions_disabled": st["suggestions_disabled"],
        "can_optimize": st["widgets_visible"] or not st["suggestions_disabled"],
        "description": "Painel de notícias/clima e sugestões automáticas de aplicativos no Menu Iniciar e Notificações."
    }

def configure_widgets(
    hide_widgets: bool = True,
    disable_suggestions: bool = True,
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    Configura visibilidade de widgets e desativação de sugestões promocionais.
    Registra no Auto Recovery Center para rollback imediato.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="CONFIGURE_WIDGETS",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    sub_adv = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    sub_cdm = r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"

    orig_widget = None
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_adv, 0, winreg.KEY_READ)
        orig_widget, _ = winreg.QueryValueEx(k, "TaskbarDa")
        winreg.CloseKey(k)
    except Exception: pass

    record_id = register_recovery_operation(
        op_id="CONFIGURE_WIDGETS",
        category="WIDGETS",
        original_state={
            "root": "HKCU",
            "sub_key": sub_adv,
            "value_name": "TaskbarDa",
            "value_data": orig_widget,
            "value_type": "REG_DWORD"
        },
        applied_state={
            "hide_widgets": hide_widgets,
            "disable_suggestions": disable_suggestions
        },
        restore_strategy="RESTORE_REGISTRY_VALUE",
        status="IN_PROGRESS"
    )

    try:
        # 1. Oculta ou exibe o botão de Widgets na Barra de Tarefas (0 = Oculto, 1 = Visível)
        if hide_widgets:
            k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_adv)
            winreg.SetValueEx(k, "TaskbarDa", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(k)

        # 2. Desativa dicas promocionais e sugestões no Iniciar
        if disable_suggestions:
            k_cdm = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_cdm)
            cdm_keys = [
                "SubscribedContent-338388Enabled",
                "SubscribedContent-338389Enabled",
                "SubscribedContent-353696Enabled",
                "SubscribedContent-353698Enabled",
                "SystemPaneSuggestionsEnabled"
            ]
            for key_name in cdm_keys:
                winreg.SetValueEx(k_cdm, key_name, 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(k_cdm)

        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "APPLIED")

        app_logger.info(f"Widgets e sugestões configurados com sucesso. Registro: {record_id}")
        return {
            "success": True,
            "message": "Painel de Widgets e sugestões do Windows configurados com sucesso.",
            "record_id": record_id
        }
    except Exception as e:
        app_logger.error(f"Erro ao configurar widgets: {e}")
        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "FAILED", str(e))
        return {"success": False, "message": f"Falha ao configurar widgets: {e}"}
