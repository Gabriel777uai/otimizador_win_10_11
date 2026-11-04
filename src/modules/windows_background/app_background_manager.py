"""
Gerenciador de Aplicativos em Segundo Plano - ALTUS PC OPTIMIZER.
Identifica permissões de execução em segundo plano para aplicativos instalados,
sugere encerramento manual de softwares não essenciais antes de jogos e
permite controle individualizado com reversão no Auto Recovery Center.
"""
import winreg
from typing import Dict, Any, List
import psutil

from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager
from src.core.recovery_manager import register_recovery_operation

# Softwares comuns não essenciais que frequentemente consomem CPU/RAM em segundo plano
COMMON_GAMING_BACKGROUND_APPS = {
    "discord.exe": "Discord (Comunicação)",
    "spotify.exe": "Spotify (Streaming de Áudio)",
    "steam.exe": "Steam (Plataforma de Jogos)",
    "epicgameslauncher.exe": "Epic Games Launcher",
    "origin.exe": "EA Origin / EA App",
    "eadesktop.exe": "EA App",
    "chrome.exe": "Google Chrome (Navegador)",
    "firefox.exe": "Mozilla Firefox",
    "brave.exe": "Brave Browser",
    "telegram.exe": "Telegram Desktop",
    "whatsapp.exe": "WhatsApp Desktop",
    "utorrent.exe": "uTorrent Client",
    "bittorrent.exe": "BitTorrent Client",
    "qbittorrent.exe": "qBittorrent"
}

def get_background_apps_status() -> Dict[str, Any]:
    """Verifica a política global de aplicativos em segundo plano do Windows."""
    sub_key = r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications"
    disabled = False
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(k, "GlobalUserDisabled")
        disabled = (val == 1)
        winreg.CloseKey(k)
    except Exception:
        pass

    return {
        "global_user_disabled": disabled,
        "description": "Controla se aplicativos universais e da Microsoft Store podem executar tarefas quando não estão abertos na tela."
    }

def get_active_heavy_background_apps() -> List[Dict[str, Any]]:
    """
    Identifica processos comuns de terceiros em execução em segundo plano
    que podem ser fechados manualmente antes de iniciar uma partida de jogo.
    Nunca encerra nada automaticamente.
    """
    found = []
    seen = set()

    for p in psutil.process_iter(['name', 'pid', 'memory_info', 'cpu_percent']):
        try:
            name = (p.info.get('name') or '').lower()
            if name in COMMON_GAMING_BACKGROUND_APPS and name not in seen:
                seen.add(name)
                mem_mb = round(p.info['memory_info'].rss / (1024 ** 2), 1)
                cpu = p.info.get('cpu_percent') or 0.0

                found.append({
                    "name": name,
                    "description": COMMON_GAMING_BACKGROUND_APPS[name],
                    "pid": p.info['pid'],
                    "memory_mb": mem_mb,
                    "cpu_percent": round(cpu, 1),
                    "can_close_manually": True
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    found.sort(key=lambda x: x["memory_mb"], reverse=True)
    return found

def configure_background_apps(
    disable_global: bool = True,
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    Configura a chave GlobalUserDisabled para aplicativos em segundo plano.
    Salva o valor anterior no Auto Recovery Center para reversão rápida.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="CONFIGURE_BACKGROUND_APPS",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    sub_key = r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications"
    orig_val = None
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key, 0, winreg.KEY_READ)
        orig_val, _ = winreg.QueryValueEx(k, "GlobalUserDisabled")
        winreg.CloseKey(k)
    except Exception:
        pass

    record_id = register_recovery_operation(
        op_id="CONFIGURE_BACKGROUND_APPS",
        category="BACKGROUND_APPS",
        original_state={
            "root": "HKCU",
            "sub_key": sub_key,
            "value_name": "GlobalUserDisabled",
            "value_data": orig_val,
            "value_type": "REG_DWORD"
        },
        applied_state={"disable_global": disable_global},
        restore_strategy="RESTORE_REGISTRY_VALUE",
        status="IN_PROGRESS"
    )

    try:
        new_val = 1 if disable_global else 0
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_key)
        winreg.SetValueEx(k, "GlobalUserDisabled", 0, winreg.REG_DWORD, new_val)
        winreg.CloseKey(k)

        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "APPLIED")

        status_msg = "limitados com sucesso" if disable_global else "restaurados para execução padrão"
        app_logger.info(f"Permissões de aplicativos em segundo plano {status_msg}. Registro: {record_id}")
        return {
            "success": True,
            "message": f"Aplicativos em segundo plano foram {status_msg}.",
            "record_id": record_id
        }
    except Exception as e:
        app_logger.error(f"Erro ao configurar aplicativos em segundo plano: {e}")
        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "FAILED", str(e))
        return {"success": False, "message": f"Falha ao configurar aplicativos em segundo plano: {e}"}
