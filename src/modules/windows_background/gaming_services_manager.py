"""
Gerenciador de Serviços em Segundo Plano para Jogos - ALTUS PC OPTIMIZER.
Controla a captura contínua e gravação automática em segundo plano do Game DVR,
reduzindo a gravação constante em disco sem afetar o Game Mode, serviços Xbox ou anticheats.
"""
import winreg
from typing import Dict, Any
from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager
from src.core.recovery_manager import register_recovery_operation
from .feature_detector import detect_gaming_dvr_status

def get_gaming_dvr_status() -> Dict[str, Any]:
    """Retorna estado da captura contínua de jogos e Game DVR."""
    st = detect_gaming_dvr_status()
    return {
        "game_dvr_enabled": st["game_dvr_enabled"],
        "background_recording_active": st["background_recording_active"],
        "can_optimize": st["background_recording_active"],
        "description": "A gravação contínua em segundo plano consome I/O de disco e ciclos de CPU para armazenar os últimos minutos de gameplay."
    }

def configure_gaming_dvr(
    disable_background_recording: bool = True,
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    Desativa ou ativa a gravação automática em segundo plano (HistoricalCaptureEnabled / AppCaptureEnabled)
    mantendo integralmente ativo o Modo de Jogo nativo do Windows e os serviços da Xbox Network.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="CONFIGURE_GAME_DVR",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    sub_gamedvr = r"Software\Microsoft\Windows\CurrentVersion\GameDVR"
    sub_config = r"System\GameConfigStore"

    orig_hist = None
    orig_app = None
    orig_dvr = None

    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_gamedvr, 0, winreg.KEY_READ)
        try: orig_hist, _ = winreg.QueryValueEx(k, "HistoricalCaptureEnabled")
        except Exception: pass
        try: orig_app, _ = winreg.QueryValueEx(k, "AppCaptureEnabled")
        except Exception: pass
        winreg.CloseKey(k)
    except Exception: pass

    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_config, 0, winreg.KEY_READ)
        orig_dvr, _ = winreg.QueryValueEx(k, "GameDVR_Enabled")
        winreg.CloseKey(k)
    except Exception: pass

    record_id = register_recovery_operation(
        op_id="CONFIGURE_GAME_DVR",
        category="GAMING_DVR",
        original_state={
            "root": "HKCU",
            "sub_key": sub_gamedvr,
            "value_name": "HistoricalCaptureEnabled",
            "value_data": orig_hist,
            "value_type": "REG_DWORD"
        },
        applied_state={"disable_background_recording": disable_background_recording},
        restore_strategy="RESTORE_REGISTRY_VALUE",
        status="IN_PROGRESS"
    )

    try:
        # Se desativar a gravação de fundo, seta para 0
        new_val = 0 if disable_background_recording else 1

        k1 = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_gamedvr)
        winreg.SetValueEx(k1, "HistoricalCaptureEnabled", 0, winreg.REG_DWORD, new_val)
        winreg.SetValueEx(k1, "AppCaptureEnabled", 0, winreg.REG_DWORD, new_val)
        winreg.CloseKey(k1)

        k2 = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_config)
        winreg.SetValueEx(k2, "GameDVR_Enabled", 0, winreg.REG_DWORD, new_val)
        winreg.CloseKey(k2)

        # Garante que o Windows Game Mode continua ATIVO para melhor priorização de threads
        k_game = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar")
        winreg.SetValueEx(k_game, "AllowAutoGameMode", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(k_game)

        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "APPLIED")

        status_txt = "desativada com sucesso (Game Mode preservado)" if disable_background_recording else "reativada"
        app_logger.info(f"Gravação em segundo plano do Game DVR {status_txt}. Registro: {record_id}")
        return {
            "success": True,
            "message": f"Captura contínua em segundo plano do Game DVR foi {status_txt}.",
            "record_id": record_id
        }
    except Exception as e:
        app_logger.error(f"Erro ao configurar Game DVR: {e}")
        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "FAILED", str(e))
        return {"success": False, "message": f"Falha ao configurar Game DVR: {e}"}
