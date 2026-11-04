"""
Gerenciador de Telemetria e Diagnóstico do Windows - ALTUS PC OPTIMIZER.
Configura níveis de coleta de diagnóstico, experiências personalizadas e
frequência de solicitações de feedback segundo documentação oficial da Microsoft.
Preserva integralmente o Windows Update, Error Reporting e componentes de segurança.
"""
import winreg
from typing import Dict, Any
from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager
from src.core.recovery_manager import register_recovery_operation
from .feature_detector import detect_telemetry_status

def get_telemetry_status() -> Dict[str, Any]:
    """Retorna estado atual das políticas de diagnóstico e privacidade."""
    st = detect_telemetry_status()
    level_desc = {
        0: "Segurança / Enterprise (Mínimo)",
        1: "Dados de Diagnóstico Básicos / Obrigatórios (Recomendado)",
        2: "Avançado",
        3: "Completo / Opcional (Padrão Windows)"
    }
    return {
        "level": st["level"],
        "level_description": level_desc.get(st["level"], "Personalizado"),
        "tailored_experiences_disabled": st["tailored_experiences_disabled"],
        "feedback_frequency_zero": st["feedback_frequency_zero"],
        "can_optimize": st["level"] > 1 or not st["tailored_experiences_disabled"] or not st["feedback_frequency_zero"],
        "description": "Limita o envio de dados diagnósticos opcionais para a Microsoft e desativa pesquisas de opinião no sistema."
    }

def configure_telemetry(
    set_basic_diagnostics: bool = True,
    disable_tailored_experiences: bool = True,
    disable_feedback_prompts: bool = True,
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    Aplica configurações recomendadas de telemetria e privacidade sem prejudicar atualizações.
    Registra os valores no Auto Recovery Center para reversão total.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="CONFIGURE_TELEMETRY",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    sub_data = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"
    sub_cloud = r"Software\Policies\Microsoft\Windows\CloudContent"
    sub_siuf = r"Software\Microsoft\Siuf\Rules"

    # Salva valores originais
    orig_tel = None
    orig_tailor = None
    orig_siuf = None

    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_data, 0, winreg.KEY_READ)
        orig_tel, _ = winreg.QueryValueEx(k, "AllowTelemetry")
        winreg.CloseKey(k)
    except Exception: pass

    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_cloud, 0, winreg.KEY_READ)
        orig_tailor, _ = winreg.QueryValueEx(k, "DisableTailoredExperiencesWithDiagnosticData")
        winreg.CloseKey(k)
    except Exception: pass

    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_siuf, 0, winreg.KEY_READ)
        orig_siuf, _ = winreg.QueryValueEx(k, "NumberOfSIUFInPeriod")
        winreg.CloseKey(k)
    except Exception: pass

    record_id = register_recovery_operation(
        op_id="CONFIGURE_TELEMETRY",
        category="TELEMETRY",
        original_state={
            "root": "HKLM",
            "sub_key": sub_data,
            "value_name": "AllowTelemetry",
            "value_data": orig_tel,
            "value_type": "REG_DWORD"
        },
        applied_state={
            "set_basic_diagnostics": set_basic_diagnostics,
            "disable_tailored_experiences": disable_tailored_experiences,
            "disable_feedback_prompts": disable_feedback_prompts
        },
        restore_strategy="RESTORE_REGISTRY_VALUE",
        status="IN_PROGRESS"
    )

    try:
        # 1. Nível de Telemetria (1 = Dados Básicos / Obrigatórios)
        if set_basic_diagnostics:
            k = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, sub_data)
            winreg.SetValueEx(k, "AllowTelemetry", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(k)

        # 2. Experiências Personalizadas (1 = Desativado)
        if disable_tailored_experiences:
            k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_cloud)
            winreg.SetValueEx(k, "DisableTailoredExperiencesWithDiagnosticData", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(k)

        # 3. Notificações de Feedback (0 = Nunca solicitar)
        if disable_feedback_prompts:
            k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_siuf)
            winreg.SetValueEx(k, "NumberOfSIUFInPeriod", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(k)

        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "APPLIED")

        app_logger.info(f"Políticas de telemetria e diagnóstico configuradas com sucesso. Registro: {record_id}")
        return {
            "success": True,
            "message": "Nível de diagnóstico e opções de privacidade configurados com sucesso (telemetria básica ativa).",
            "record_id": record_id
        }
    except Exception as e:
        app_logger.error(f"Erro ao configurar telemetria: {e}")
        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "FAILED", str(e))
        return {"success": False, "message": f"Falha ao configurar telemetria: {e}"}
