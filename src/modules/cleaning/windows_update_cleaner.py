"""
Módulo de Limpeza Controlada do Cache de Downloads do Windows Update.
Diretório afetado: C:\\Windows\\SoftwareDistribution\\Download
NUNCA remove DataStore, catroot2 ou componentes vitais do sistema.
Garante controle de serviços, verificação de integridade e restauração no bloco finally.
"""
import os
import time
import winreg
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import psutil

from src.utils.logger import app_logger
from src.utils.command_runner import run_command
from src.core.safety_manager import safety_manager, RiskLevel

UPDATE_PROCESS_NAMES = {
    "tiworker.exe",
    "trustedinstaller.exe",
    "wuauclt.exe",
    "mousocoreworker.exe",
    "usoclient.exe"
}

def is_reboot_pending() -> bool:
    """Verifica se há reinicialização pendente por atualizações do Windows."""
    paths_to_check = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired")
    ]
    for hkey, subkey in paths_to_check:
        try:
            key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ)
            winreg.CloseKey(key)
            return True
        except (FileNotFoundError, OSError):
            continue
    return False

def is_update_in_progress() -> Tuple_Result:
    """
    Verifica se o Windows Update ou instaladores de componentes estão em execução ativa.
    Analisa processos em execução e estado do serviço wuauserv.
    """
    # 1. Verifica processos ativos de instalação
    for proc in psutil.process_iter(['name']):
        try:
            pname = (proc.info.get('name') or '').lower()
            if pname in UPDATE_PROCESS_NAMES:
                return True, f"Processo crítico de atualização detectado em execução: {pname}"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # 2. Verifica estado do serviço wuauserv
    try:
        service = psutil.win_service_get("wuauserv")
        status = service.status()
        if status in ("start_pending", "continue_pending"):
            return True, "Serviço do Windows Update está em transição de inicialização."
    except Exception:
        pass

    return False, ""

Tuple_Result = tuple[bool, str]

def analyze_update_cache() -> Dict[str, Any]:
    """Calcula o tamanho e contagem dos arquivos na pasta SoftwareDistribution\\Download."""
    win_dir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    download_dir = win_dir / "SoftwareDistribution" / "Download"

    total_bytes = 0
    file_count = 0
    dir_count = 0

    if download_dir.exists() and download_dir.is_dir():
        for root, dirs, files in os.walk(download_dir):
            for d in dirs:
                dir_count += 1
            for f in files:
                try:
                    fp = Path(root) / f
                    total_bytes += fp.stat().st_size
                    file_count += 1
                except (OSError, PermissionError):
                    continue

    active_update, reason = is_update_in_progress()
    reboot = is_reboot_pending()

    return {
        "path": str(download_dir),
        "file_count": file_count,
        "dir_count": dir_count,
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 ** 2), 2),
        "reboot_pending": reboot,
        "update_in_progress": active_update,
        "update_block_reason": reason,
        "is_safe_to_clean": not reboot and not active_update
    }

def _wait_for_service_status(service_name: str, target_status: str, timeout_sec: int = 15) -> bool:
    """Aguarda ativamente até que um serviço do Windows alcance o status desejado."""
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        try:
            srv = psutil.win_service_get(service_name)
            if srv.status() == target_status:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def clean_update_cache(
    user_confirmed: bool = False,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Executa a limpeza controlada de C:\\Windows\\SoftwareDistribution\\Download.
    Interrompe wuauserv e bits, aguarda a finalização de processos, remove itens e restaura os serviços.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="WINDOWS_UPDATE_CLEANUP",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    # 1. Verificações de segurança obrigatórias
    if is_reboot_pending():
        return {
            "success": False,
            "message": "Existe uma reinicialização pendente do Windows. Reinicie o sistema antes de limpar o cache."
        }

    active, active_reason = is_update_in_progress()
    if active:
        return {
            "success": False,
            "message": f"Operação abortada por segurança: {active_reason}"
        }

    win_dir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    download_dir = win_dir / "SoftwareDistribution" / "Download"

    if dry_run:
        stat = analyze_update_cache()
        return {
            "success": True,
            "dry_run": True,
            "freed_mb": stat["total_mb"],
            "file_count": stat["file_count"],
            "message": f"Simulação concluída: {stat['file_count']} arquivos ({stat['total_mb']} MB) elegíveis para limpeza."
        }

    if not download_dir.exists():
        return {"success": True, "message": "O diretório de cache do Windows Update não existe ou já está limpo."}

    app_logger.info("Iniciando rotina profissional de limpeza do cache do Windows Update...")
    if progress_callback:
        progress_callback(10, "Verificando estado dos serviços do Windows Update...")

    services_to_manage = ["wuauserv", "bits"]
    previously_running = []

    # 2. Identifica quais serviços estavam em execução
    for s_name in services_to_manage:
        try:
            srv = psutil.win_service_get(s_name)
            if srv.status() == "running":
                previously_running.append(s_name)
        except Exception as e:
            app_logger.warning(f"Não foi possível consultar o serviço {s_name}: {e}")

    # 3. Interrupção controlada com validação
    stopped_services = []
    for s_name in previously_running:
        if progress_callback:
            progress_callback(20, f"Interrompendo serviço {s_name}...")
        app_logger.info(f"Interrompendo serviço {s_name}...")
        rc, out, err = run_command(["net", "stop", s_name], timeout=30)
        
        # Confirma se o serviço realmente parou
        if _wait_for_service_status(s_name, "stopped", timeout_sec=15):
            stopped_services.append(s_name)
            app_logger.info(f"Serviço {s_name} parado com sucesso.")
        else:
            app_logger.error(f"Falha ao parar o serviço {s_name}. Abortando limpeza por segurança.")
            # Restaura os serviços que já tinham sido parados
            for r_name in stopped_services:
                run_command(["net", "start", r_name], timeout=20)
            return {
                "success": False,
                "message": f"Não foi possível interromper o serviço '{s_name}' com segurança. Operação cancelada."
            }

    deleted_bytes = 0
    deleted_files = 0
    deleted_dirs = 0
    failed_items = []

    try:
        if progress_callback:
            progress_callback(40, "Coletando lista de arquivos para remoção...")

        # Coleta lista de itens
        items = list(download_dir.iterdir())
        total_items = len(items)

        for idx, item in enumerate(items):
            pct = 40 + int((idx / max(total_items, 1)) * 40)
            if progress_callback:
                progress_callback(pct, f"Removendo {item.name}...")

            try:
                if item.is_file():
                    sz = item.stat().st_size
                    item.unlink()
                    deleted_bytes += sz
                    deleted_files += 1
                elif item.is_dir():
                    # Calcula tamanho antes de remover
                    dir_sz = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                    # Remove recursivamente com captura de erro em cada arquivo
                    for subfile in sorted(item.rglob('*'), reverse=True):
                        try:
                            if subfile.is_file():
                                subfile.unlink()
                                deleted_files += 1
                            elif subfile.is_dir():
                                subfile.rmdir()
                                deleted_dirs += 1
                        except Exception as fe:
                            failed_items.append(f"{subfile.name}: {fe}")
                    # Tenta remover o diretório raiz
                    try:
                        item.rmdir()
                        deleted_dirs += 1
                        deleted_bytes += dir_sz
                    except Exception as de:
                        failed_items.append(f"{item.name}: {de}")
            except Exception as e:
                failed_items.append(f"{item.name}: {e}")
                app_logger.warning(f"Falha ao remover item do cache {item}: {e}")

    finally:
        # 4. Restauração incondicional dos serviços que estavam rodando originalmente
        if progress_callback:
            progress_callback(85, "Restaurando serviços de sistema...")
        services_restored = []
        services_failed_restore = []

        for s_name in previously_running:
            app_logger.info(f"Restaurando serviço {s_name}...")
            run_command(["net", "start", s_name], timeout=30)
            if _wait_for_service_status(s_name, "running", timeout_sec=15):
                services_restored.append(s_name)
            else:
                services_failed_restore.append(s_name)
                app_logger.critical(f"Aviso crítico: Falha ao confirmar restauração do serviço {s_name}!")

    freed_mb = round(deleted_bytes / (1024 ** 2), 2)
    has_failures = len(failed_items) > 0
    restore_failures = len(services_failed_restore) > 0

    if progress_callback:
        progress_callback(100, "Concluído.")

    if restore_failures:
        return {
            "success": False,
            "deleted_files": deleted_files,
            "deleted_dirs": deleted_dirs,
            "freed_mb": freed_mb,
            "failed_count": len(failed_items),
            "service_failures": services_failed_restore,
            "message": f"Limpeza parcial realizada ({freed_mb} MB), mas houve falha ao reativar os serviços: {', '.join(services_failed_restore)}."
        }

    if has_failures:
        app_logger.warning(f"Limpeza de Windows Update concluída com {len(failed_items)} falhas pontuais.")
        return {
            "success": True,
            "partial": True,
            "deleted_files": deleted_files,
            "deleted_dirs": deleted_dirs,
            "freed_mb": freed_mb,
            "failed_count": len(failed_items),
            "message": f"Limpeza concluída com sucesso parcial: {deleted_files} arquivos removidos ({freed_mb} MB liberados). {len(failed_items)} arquivos em uso foram preservados."
        }

    app_logger.info(f"Limpeza de Windows Update concluída com sucesso total: {deleted_files} arquivos, {freed_mb} MB liberados.")
    return {
        "success": True,
        "partial": False,
        "deleted_files": deleted_files,
        "deleted_dirs": deleted_dirs,
        "freed_mb": freed_mb,
        "failed_count": 0,
        "message": f"Cache do Windows Update limpo com sucesso total: {deleted_files} arquivos ({freed_mb} MB liberados)."
    }
