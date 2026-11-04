"""
Gerenciador Inteligente de Indexação do Windows Search - ALTUS PC OPTIMIZER.
Identifica consumo do serviço WSearch e SearchIndexer.exe e sugere exclusão de
pastas volumosas de desenvolvimento (node_modules, .git, venv, vendor) sem apagar nenhum arquivo.
"""
import os
import psutil
from typing import Dict, Any, List
from pathlib import Path

from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager
from src.core.recovery_manager import register_recovery_operation
from src.core.config_manager import load_app_config, save_app_config

COMMON_DEV_FOLDER_NAMES = {
    "node_modules", "vendor", ".git", ".venv", "venv", "__pycache__",
    "dist", "build", ".cache", "coverage", ".next", ".nuxt", "target"
}

def get_search_index_status() -> Dict[str, Any]:
    """Retorna estado do serviço de indexação e consumo de memória do SearchIndexer."""
    service_running = False
    proc_cpu = 0.0
    proc_mem_mb = 0.0

    try:
        svc = psutil.win_service_get("WSearch")
        service_running = (svc.status() == "running")
    except Exception:
        pass

    for p in psutil.process_iter(['name', 'cpu_percent', 'memory_info']):
        try:
            if (p.info.get('name') or '').lower() == "searchindexer.exe":
                proc_cpu = p.info.get('cpu_percent') or 0.0
                proc_mem_mb = round((p.info['memory_info'].rss) / (1024 ** 2), 1)
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    config = load_app_config()
    current_exclusions = config.get("search_excluded_paths", [])

    return {
        "service_running": service_running,
        "indexer_cpu_percent": proc_cpu,
        "indexer_memory_mb": proc_mem_mb,
        "excluded_paths": current_exclusions,
        "excluded_count": len(current_exclusions),
        "description": "O SearchIndexer indexa continuamente arquivos de código e bibliotecas, aumentando o uso de disco e CPU."
    }

def scan_common_dev_folders(search_roots: Optional[List[str]] = None, max_results: int = 25) -> List[Dict[str, Any]]:
    """
    Localiza diretórios volumosos de desenvolvimento em locais comuns do usuário.
    Nunca lê o conteúdo nem remove nada. Apenas mapeia caminhos para sugestão.
    """
    if not search_roots:
        search_roots = []
        user_home = Path.home()
        for candidate in [
            user_home / "Projects",
            user_home / "source",
            user_home / "workspace",
            user_home / "Desktop",
            user_home / "Documents",
            Path("C:/wamp64/www"),
            Path("C:/laragon/www"),
            Path("C:/dev"),
            Path("D:/Projects")
        ]:
            if candidate.exists() and candidate.is_dir():
                search_roots.append(str(candidate))

    found_dirs: List[Dict[str, Any]] = []
    seen = set()

    for root_dir in search_roots:
        if len(found_dirs) >= max_results:
            break
        try:
            # Varredura rasa (máximo 3 níveis de profundidade para rapidez)
            for current_root, dirs, _ in os.walk(root_dir):
                # Limita profundidade
                depth = current_root[len(root_dir):].count(os.sep)
                if depth > 3:
                    dirs.clear()
                    continue

                for d in list(dirs):
                    if d.lower() in COMMON_DEV_FOLDER_NAMES:
                        full_path = os.path.abspath(os.path.join(current_root, d))
                        if full_path not in seen and os.path.exists(full_path):
                            seen.add(full_path)
                            found_dirs.append({
                                "path": full_path,
                                "name": d,
                                "parent": current_root,
                                "exists": True,
                                "suggested": True
                            })
                            dirs.remove(d) # Não aprofunda dentro de node_modules/.git
                            if len(found_dirs) >= max_results:
                                break
        except (PermissionError, OSError):
            continue

    return found_dirs

def configure_index_exclusions(
    paths_to_exclude: List[str],
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    Registra diretórios para exclusão da indexação sem remover arquivos.
    Salva backup das exclusões no Auto Recovery Center.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="CONFIGURE_SEARCH_INDEXING",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    valid_paths = [p for p in paths_to_exclude if os.path.exists(p) and os.path.isdir(p)]
    if not valid_paths and paths_to_exclude:
        return {"success": False, "message": "Nenhum diretório válido localizado para exclusão da indexação."}

    config = load_app_config()
    orig_exclusions = config.get("search_excluded_paths", [])

    record_id = register_recovery_operation(
        op_id="CONFIGURE_SEARCH_INDEXING",
        category="SEARCH_INDEX",
        original_state={"excluded_paths": orig_exclusions},
        applied_state={"excluded_paths": valid_paths},
        restore_strategy="RESTORE_SEARCH_INDEX",
        status="IN_PROGRESS"
    )

    try:
        # Atualiza configurações persistentes do ALTUS
        config["search_excluded_paths"] = valid_paths
        save_app_config(config)

        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "APPLIED")

        app_logger.info(f"{len(valid_paths)} pastas excluídas da indexação. Registro: {record_id}")
        return {
            "success": True,
            "message": f"{len(valid_paths)} pastas de desenvolvimento configuradas para exclusão da pesquisa com sucesso.",
            "record_id": record_id
        }
    except Exception as e:
        app_logger.error(f"Erro ao salvar exclusões de indexação: {e}")
        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "FAILED", str(e))
        return {"success": False, "message": f"Falha ao configurar exclusões: {e}"}
