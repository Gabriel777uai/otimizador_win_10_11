"""
Gerenciamento de permissões do Windows e controle UAC.
Permite executar a aplicação em privilégio normal de usuário
e elevar apenas comandos específicos quando estritamente necessário.
"""
import sys
import ctypes
from typing import Optional
from src.utils.logger import app_logger

def is_admin() -> bool:
    """Verifica se o processo atual possui privilégios de administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def request_uac_elevation(script_or_exe: str, args: str = "") -> bool:
    """
    Solicita elevação de privilégios para executar um comando via prompt UAC (User Account Control).
    """
    if sys.platform != "win32":
        return False

    app_logger.info(f"Solicitando elevação UAC (User Account Control) para: {script_or_exe} {args}")
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            script_or_exe,
            args,
            None,
            1  # SW_SHOWNORMAL
        )
        return ret > 32
    except Exception as e:
        app_logger.error(f"Erro ao solicitar elevação UAC (User Account Control): {e}")
        return False
