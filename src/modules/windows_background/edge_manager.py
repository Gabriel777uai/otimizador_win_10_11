"""
Gerenciador de Recursos em Segundo Plano do Microsoft Edge - ALTUS PC OPTIMIZER.
Controla Startup Boost e execução de extensões em segundo plano com backup oficial
no Registro do Windows, preservando senhas, perfis, WebView2 e atualizações.
"""
import winreg
from typing import Dict, Any, List
import psutil

from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager
from src.core.recovery_manager import register_recovery_operation
from .feature_detector import detect_edge_status

def get_edge_status() -> Dict[str, Any]:
    """Retorna estado do Microsoft Edge e métricas de processos em segundo plano."""
    st = detect_edge_status()
    
    # Coleta processos msedge.exe em execução
    edge_procs = 0
    edge_mem_mb = 0.0
    for p in psutil.process_iter(['name', 'memory_info']):
        try:
            n = (p.info.get('name') or '').lower()
            if n == "msedge.exe":
                edge_procs += 1
                edge_mem_mb += p.info['memory_info'].rss / (1024 ** 2)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {
        "installed": st["installed"],
        "startup_boost_disabled": st["startup_boost_disabled"],
        "background_mode_disabled": st["background_mode_disabled"],
        "active_processes_count": edge_procs,
        "total_memory_mb": round(edge_mem_mb, 1),
        "can_optimize": st["installed"] and (not st["startup_boost_disabled"] or not st["background_mode_disabled"]),
        "description": "Configurações que mantêm o Edge pré-carregado no boot e extensões ativas após fechar a janela."
    }

def configure_edge_background(
    disable_startup_boost: bool = True,
    disable_background_mode: bool = True,
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    Configura políticas oficiais do Edge no Registro (HKLM/HKCU Policies).
    Registra os valores originais no Auto Recovery Center para rollback imediato.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="CONFIGURE_EDGE_BACKGROUND",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    sub_key = r"SOFTWARE\Policies\Microsoft\Edge"
    
    # Lê valores originais
    orig_boost = None
    orig_bg = None
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key, 0, winreg.KEY_READ)
        try: orig_boost, _ = winreg.QueryValueEx(k, "StartupBoostEnabled")
        except Exception: pass
        try: orig_bg, _ = winreg.QueryValueEx(k, "BackgroundModeEnabled")
        except Exception: pass
        winreg.CloseKey(k)
    except Exception:
        pass

    record_id = register_recovery_operation(
        op_id="CONFIGURE_EDGE_BACKGROUND",
        category="EDGE",
        original_state={
            "root": "HKLM",
            "sub_key": sub_key,
            "value_name": "StartupBoostEnabled",
            "value_data": orig_boost,
            "value_type": "REG_DWORD",
            "secondary_value_name": "BackgroundModeEnabled",
            "secondary_value_data": orig_bg
        },
        applied_state={
            "disable_startup_boost": disable_startup_boost,
            "disable_background_mode": disable_background_mode
        },
        restore_strategy="RESTORE_REGISTRY_VALUE",
        status="IN_PROGRESS"
    )

    try:
        k = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, sub_key)
        
        # 0 = Desativado, 1 = Ativado
        val_boost = 0 if disable_startup_boost else 1
        winreg.SetValueEx(k, "StartupBoostEnabled", 0, winreg.REG_DWORD, val_boost)

        val_bg = 0 if disable_background_mode else 1
        winreg.SetValueEx(k, "BackgroundModeEnabled", 0, winreg.REG_DWORD, val_bg)
        
        winreg.CloseKey(k)

        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "APPLIED")

        app_logger.info(f"Políticas de segundo plano do Edge atualizadas (Boost={val_boost}, Bg={val_bg}). Registro: {record_id}")
        return {
            "success": True,
            "message": "Recursos em segundo plano do Microsoft Edge foram otimizados com sucesso.",
            "record_id": record_id
        }
    except Exception as e:
        app_logger.error(f"Erro ao configurar políticas do Edge: {e}")
        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "FAILED", str(e))
        return {"success": False, "message": f"Falha ao configurar Edge: {e}"}
