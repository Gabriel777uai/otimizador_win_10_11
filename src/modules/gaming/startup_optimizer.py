"""
Módulo de Otimização e Gerenciamento de Programas de Inicialização.
Audita chaves Run do Registro e pastas de inicialização do Windows.
Oferece desativação e reativação completas, preservando tipos de dados (REG_SZ, REG_EXPAND_SZ)
e arquivos na pasta Startup.
"""
import os
import shutil
import winreg
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager, RiskLevel

# 1. Aplicativos e componentes ESSENCIAIS (Nunca desativar)
ESSENTIAL_STARTUP_SIGNATURES = [
    "securityhealth", "defender", "antivirus", "msseces", "smartscreen",
    "realtek", "waves", "rtkhdaudio", "nvidia", "nvvsvc", "nvbackend",
    "amd", "radeon", "intel", "igfx", "synaptics", "elan", "alps",
    "ctfmon", "userinit"
]

# 2. Aplicativos comuns conhecidos e OPCIONAIS (Seguro desativar se o usuário desejar)
KNOWN_OPTIONAL_APPS = [
    "discord", "spotify", "steam", "epicgames", "ea desktop", "origin",
    "battle.net", "gog galaxy", "utorrent", "bittorrent", "qbittorrent",
    "skype", "teams", "telegram", "whatsapp", "slack", "zoom",
    "onedrive", "dropbox", "googledrive", "itunes", "ccleaner"
]

def classify_startup_entry(name: str, command: str) -> Dict[str, Any]:
    """
    Classifica a entrada com base em critérios técnicos:
    - Essencial (Hardware/Segurança): Proibido desativar.
    - Opcional Conhecido: Seguro desativar.
    - Desconhecido: Não classificado; não permite desativação automática cega.
    """
    text = f"{name} {command}".lower()

    for sig in ESSENTIAL_STARTUP_SIGNATURES:
        if sig in text:
            return {
                "classification": "Essencial (Sistema/Hardware)",
                "can_disable": False,
                "impact": "Crítico",
                "reason": "Componente essencial de segurança ou driver de hardware."
            }

    for app in KNOWN_OPTIONAL_APPS:
        if app in text:
            return {
                "classification": "Opcional (Aplicativo do Usuário)",
                "can_disable": True,
                "impact": "Médio",
                "reason": "Aplicativo de inicialização opcional; não interfere no sistema."
            }

    return {
        "classification": "Desconhecido (Não Identificado)",
        "can_disable": False,  # Proteção contra desativação automática de desconhecidos
        "impact": "Desconhecido",
        "reason": "Programa não catalogado. Recomenda-se manter para evitar instabilidade."
    }

def get_startup_dir() -> Path:
    """Retorna o diretório Startup do usuário atual."""
    app_data = os.environ.get("APPDATA", "")
    return Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

def get_startup_disabled_dir() -> Path:
    """Retorna o diretório de backup de atalhos desativados."""
    d = get_startup_dir() / "Altus_Disabled"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_startup_entries() -> List[Dict[str, Any]]:
    """Lê todas as entradas de inicialização ativas nos Registros e pastas."""
    entries = []

    # 1. Registro HKCU Run
    entries.extend(_read_registry_run(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"))

    # 2. Registro HKLM Run
    entries.extend(_read_registry_run(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM"))

    # 3. Pasta Startup
    startup_dir = get_startup_dir()
    if startup_dir.exists():
        for item in startup_dir.iterdir():
            if item.is_file() and item.name.lower() != "desktop.ini":
                cl = classify_startup_entry(item.stem, str(item))
                entries.append({
                    "name": item.stem,
                    "command": str(item),
                    "location": "Pasta Startup (Usuário)",
                    "type": "Shortcut/File",
                    "file_path": str(item),
                    "status": "Ativo",
                    **cl
                })

    return entries

def get_disabled_startup_entries() -> List[Dict[str, Any]]:
    """Lê todas as entradas desativadas pelo ALTUS que podem ser reativadas."""
    disabled = []

    # 1. Registro HKCU Altus_Disabled
    disabled.extend(_read_registry_run(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run\Altus_Disabled",
        "HKCU",
        is_disabled_pool=True
    ))

    # 2. Registro HKLM Altus_Disabled
    disabled.extend(_read_registry_run(
        winreg.HKEY_LOCAL_MACHINE,
        r"Software\Microsoft\Windows\CurrentVersion\Run\Altus_Disabled",
        "HKLM",
        is_disabled_pool=True
    ))

    # 3. Pasta Startup Altus_Disabled
    bk_dir = get_startup_disabled_dir()
    if bk_dir.exists():
        for item in bk_dir.iterdir():
            if item.is_file() and item.name.lower() != "desktop.ini":
                disabled.append({
                    "name": item.stem,
                    "command": str(item),
                    "location": "Pasta Startup (Desativado)",
                    "type": "Shortcut/File",
                    "file_path": str(item),
                    "status": "Desativado",
                    "can_enable": True
                })

    return disabled

def _read_registry_run(hkey, subkey_path: str, location_label: str, is_disabled_pool: bool = False) -> List[Dict[str, Any]]:
    results = []
    try:
        key = winreg.OpenKey(hkey, subkey_path, 0, winreg.KEY_READ)
        index = 0
        while True:
            try:
                name, val, val_type = winreg.EnumValue(key, index)
                cl = classify_startup_entry(name, str(val))
                results.append({
                    "name": name,
                    "command": str(val),
                    "reg_type": val_type,
                    "location": f"Registro {location_label}",
                    "registry_root": location_label,
                    "registry_path": subkey_path,
                    "type": "Registro",
                    "status": "Desativado" if is_disabled_pool else "Ativo",
                    "can_enable": is_disabled_pool,
                    **cl
                })
                index += 1
            except OSError:
                break
        winreg.CloseKey(key)
    except Exception:
        pass
    return results

def disable_startup_entry(entry: Dict[str, Any], user_confirmed: bool = False) -> Dict[str, Any]:
    """
    Desativa com segurança uma entrada de inicialização preservando seu tipo exato no Registro
    ou movendo o atalho para a subpasta de quarentena.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="DISABLE_STARTUP_ENTRY",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    if not entry.get("can_disable", False):
        return {
            "success": False,
            "message": f"'{entry.get('name')}' não pode ser desativado: {entry.get('reason', 'Classificado como Essencial ou Desconhecido')}."
        }

    entry_type = entry.get("type")
    val_name = entry["name"]

    # Caso 1: Entrada do Registro
    if entry_type == "Registro":
        root = winreg.HKEY_CURRENT_USER if entry["registry_root"] == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        orig_path = entry["registry_path"]
        backup_path = orig_path + r"\Altus_Disabled"
        val_data = entry["command"]
        reg_type = entry.get("reg_type", winreg.REG_SZ)

        try:
            # 1. Salva na subchave de backup preservando o tipo exato (REG_SZ / REG_EXPAND_SZ)
            bk_key = winreg.CreateKey(root, backup_path)
            winreg.SetValueEx(bk_key, val_name, 0, reg_type, val_data)
            winreg.CloseKey(bk_key)

            # 2. Remove da chave ativa
            orig_key = winreg.OpenKey(root, orig_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(orig_key, val_name)
            winreg.CloseKey(orig_key)

            app_logger.info(f"Entrada de inicialização desativada com preservação de tipo ({reg_type}): {val_name}")
            return {"success": True, "message": f"'{val_name}' desativado com sucesso (disponível para restauração)."}
        except Exception as e:
            app_logger.error(f"Erro ao desativar entrada {val_name}: {e}")
            return {"success": False, "message": f"Falha ao acessar Registro: {e}"}

    # Caso 2: Atalho da pasta Startup
    elif entry_type == "Shortcut/File":
        file_path = Path(entry.get("file_path", ""))
        if not file_path.exists():
            return {"success": False, "message": "Atalho de inicialização não encontrado no disco."}

        bk_dir = get_startup_disabled_dir()
        dest_path = bk_dir / file_path.name
        try:
            shutil.move(str(file_path), str(dest_path))
            app_logger.info(f"Atalho de inicialização movido para quarentena: {file_path.name}")
            return {"success": True, "message": f"Atalho '{file_path.name}' desativado com sucesso."}
        except Exception as e:
            return {"success": False, "message": f"Falha ao mover atalho de inicialização: {e}"}

    return {"success": False, "message": "Tipo de inicializador não reconhecido para desativação."}

def enable_startup_entry(entry: Dict[str, Any], user_confirmed: bool = False) -> Dict[str, Any]:
    """
    Restaura/reativa uma entrada de inicialização previamente desativada pelo ALTUS,
    retornando o valor exato com seu tipo original para a chave Run ou movendo o atalho de volta.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="ENABLE_STARTUP_ENTRY",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    entry_type = entry.get("type")
    val_name = entry["name"]

    # Caso 1: Entrada do Registro
    if entry_type == "Registro":
        root = winreg.HKEY_CURRENT_USER if entry["registry_root"] == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        current_path = entry["registry_path"]  # Ex: ...\Run\Altus_Disabled
        orig_run_path = current_path.replace(r"\Altus_Disabled", "")
        val_data = entry["command"]
        reg_type = entry.get("reg_type", winreg.REG_SZ)

        try:
            # 1. Restaura na chave Run ativa
            run_key = winreg.OpenKey(root, orig_run_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(run_key, val_name, 0, reg_type, val_data)
            winreg.CloseKey(run_key)

            # 2. Remove da chave Altus_Disabled
            bk_key = winreg.OpenKey(root, current_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(bk_key, val_name)
            winreg.CloseKey(bk_key)

            app_logger.info(f"Entrada de inicialização reativada com sucesso: {val_name}")
            return {"success": True, "message": f"'{val_name}' reativado com sucesso."}
        except Exception as e:
            app_logger.error(f"Erro ao reativar entrada {val_name}: {e}")
            return {"success": False, "message": f"Falha ao restaurar no Registro: {e}"}

    # Caso 2: Atalho da pasta Startup
    elif entry_type == "Shortcut/File":
        file_path = Path(entry.get("file_path", ""))
        if not file_path.exists():
            return {"success": False, "message": "Atalho desativado não encontrado na pasta de quarentena."}

        target_dir = get_startup_dir()
        dest_path = target_dir / file_path.name
        try:
            shutil.move(str(file_path), str(dest_path))
            app_logger.info(f"Atalho restaurado para a pasta Startup: {file_path.name}")
            return {"success": True, "message": f"Atalho '{file_path.name}' reativado na inicialização."}
        except Exception as e:
            return {"success": False, "message": f"Falha ao restaurar atalho: {e}"}

    return {"success": False, "message": "Tipo de inicializador não reconhecido para reativação."}
