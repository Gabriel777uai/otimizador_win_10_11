"""
Módulo de execução segura de comandos de sistema para Windows.
Trata codificação, timeouts e isolamento de processos.
"""
import subprocess
import sys
import ctypes
from typing import Tuple, List, Optional
from src.utils.logger import app_logger

def run_command(
    cmd: List[str] | str,
    timeout: Optional[int] = 60,
    shell: bool = False
) -> Tuple[int, str, str]:
    """
    Executa um comando de forma síncrona com captura de saída e timeout seguro.
    Retorna (returncode, stdout, stderr).
    """
    app_logger.info(f"Executando comando: {cmd}")
    try:
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell,
            startupinfo=startupinfo,
            text=False
        )

        stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)

        # Decodificação tolerante para saída de console Windows (OEM / UTF-8)
        stdout = _decode_output(stdout_bytes)
        stderr = _decode_output(stderr_bytes)

        return process.returncode, stdout, stderr

    except subprocess.TimeoutExpired:
        process.kill()
        app_logger.warning(f"Comando atingiu timeout de {timeout}s: {cmd}")
        return -1, "", f"Operação interrompida: tempo limite excedido ({timeout}s)"
    except Exception as e:
        app_logger.error(f"Erro ao executar comando {cmd}: {e}")
        return -1, "", str(e)

def run_as_admin(executable: str, params: str = "", timeout: int = 120) -> bool:
    """
    Executa um processo com privilégios administrativos via ShellExecuteW (UAC Prompt).
    """
    if sys.platform != "win32":
        return False

    app_logger.info(f"Solicitando execução administrativa (UAC): {executable} {params}")
    try:
        # Usa ShellExecuteW com o verbo 'runas'
        rc = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            executable,
            params,
            None,
            1  # SW_SHOWNORMAL
        )
        return rc > 32
    except Exception as e:
        app_logger.error(f"Falha ao solicitar elevação administrativa: {e}")
        return False

def _decode_output(data: bytes) -> str:
    """Decodifica bytes retornados por ferramentas do Windows em encodings comuns."""
    if not data:
        return ""
    for enc in ["utf-8", "cp850", "cp1252", "latin-1"]:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
