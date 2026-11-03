"""
Operações de arquivo seguras para limpeza e auditoria de disco.
Garante proteção de dados pessoais, links simbólicos, controle de idade e proteção contra TOCTOU.
"""
import os
import time
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional, Callable
from src.utils.logger import app_logger
from src.utils.validators import validate_file_for_deletion

def is_reparse_point(path: Path) -> bool:
    """
    Verifica se o caminho é link simbólico, junção (junction) ou reparse point
    utilizando lstat sem seguir o destino.
    """
    try:
        if os.path.islink(path):
            return True
        lst = os.lstat(path)
        attrs = getattr(lst, "st_file_attributes", 0)
        # FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        return (attrs & 0x400) != 0
    except Exception:
        return False

def scan_directory(
    directory: Path,
    min_age_days: int = 7,
    max_depth: int = 8,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Analisa um diretório temporário respeitando o critério de idade mínima,
    profundidade máxima de varredura e proteção contra links simbólicos/junções.
    """
    now = time.time()
    min_age_seconds = min_age_days * 86400

    metrics = {
        "path": str(directory),
        "total_files": 0,
        "total_bytes": 0,
        "eligible_files": 0,
        "eligible_bytes": 0,
        "skipped_recent": 0,
        "skipped_symlinks": 0,
        "files_to_clean": []
    }

    if not directory.exists() or not directory.is_dir():
        return metrics

    try:
        for root, dirs, files in os.walk(directory, topdown=True, followlinks=False):
            root_path = Path(root)

            # 1. Limitação real de profundidade
            try:
                rel_parts = root_path.relative_to(directory).parts
                current_depth = len(rel_parts)
                if current_depth >= max_depth:
                    dirs.clear()  # Não desce mais fundo
            except Exception:
                pass

            # 2. Não seguir junções nem links simbólicos em pastas
            safe_dirs = []
            for d in dirs:
                sub_dir_path = root_path / d
                if is_reparse_point(sub_dir_path):
                    metrics["skipped_symlinks"] += 1
                else:
                    safe_dirs.append(d)
            dirs[:] = safe_dirs

            # 3. Analisa arquivos individuais
            for fname in files:
                file_path = root_path / fname
                metrics["total_files"] += 1

                try:
                    if is_reparse_point(file_path):
                        metrics["skipped_symlinks"] += 1
                        continue

                    # Usa lstat para não seguir atalhos
                    lst = os.lstat(file_path)
                    file_size = lst.st_size
                    metrics["total_bytes"] += file_size

                    file_age = now - lst.st_mtime
                    if file_age >= min_age_seconds:
                        metrics["eligible_files"] += 1
                        metrics["eligible_bytes"] += file_size
                        metrics["files_to_clean"].append({
                            "path": str(file_path),
                            "size": file_size,
                            "age_days": round(file_age / 86400, 1)
                        })
                    else:
                        metrics["skipped_recent"] += 1

                except (PermissionError, FileNotFoundError, OSError):
                    continue

    except Exception as e:
        app_logger.warning(f"Exceção durante varredura segura de {directory}: {e}")

    return metrics

def clean_files_safely(
    files: List[Dict[str, Any]],
    authorized_roots: Optional[List[Path]] = None,
    min_age_days: int = 7,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Exclui arquivos selecionados com revalidação estrita imediatamente antes da exclusão.
    No modo DRY RUN, contabiliza separadamente 'would_delete' sem reportar arquivos como excluídos.
    """
    if authorized_roots is None:
        user_temp = Path(os.environ.get("TEMP", "")).resolve()
        win_temp = Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve() / "Temp"
        authorized_roots = [user_temp, win_temp]

    min_age_seconds = min_age_days * 86400

    result = {
        "deleted_count": 0,
        "deleted_bytes": 0,
        "would_delete_count": 0,
        "would_delete_bytes": 0,
        "failed_count": 0,
        "skipped_locked": 0,
        "skipped_validation": 0,
        "dry_run": dry_run
    }

    total_files = len(files)

    for idx, item in enumerate(files):
        if progress_callback and total_files > 0 and idx % max(1, total_files // 20) == 0:
            pct = int((idx / total_files) * 100)
            progress_callback(pct, f"Processando arquivo {idx + 1} de {total_files}...")

        file_path = Path(item["path"])
        file_size = item.get("size", 0)

        # MODO DRY RUN: Relatório estritamente separado, sem exclusão real
        if dry_run:
            result["would_delete_count"] += 1
            result["would_delete_bytes"] += file_size
            continue

        # Revalidação estrita no instante exato da remoção (Proteção contra alterações TOCTOU)
        is_safe, reason = validate_file_for_deletion(
            file_path,
            authorized_roots=authorized_roots,
            min_age_seconds=min_age_seconds
        )
        if not is_safe:
            result["skipped_validation"] += 1
            app_logger.debug(f"Arquivo ignorado na pré-exclusão: {file_path} - Motivo: {reason}")
            continue

        try:
            file_path.unlink()
            result["deleted_count"] += 1
            result["deleted_bytes"] += file_size
        except (PermissionError, OSError):
            # Arquivo em uso pelo sistema ou outro processo
            result["skipped_locked"] += 1
            result["failed_count"] += 1

    if progress_callback:
        progress_callback(100, "Processamento concluído.")

    return result

def clean_empty_directories(root_dir: Path, authorized_roots: Optional[List[Path]] = None) -> int:
    """Remove pastas vazias residuais sem tocar em reparse points e confinadas nas raízes autorizadas."""
    removed = 0
    if not root_dir.exists() or not root_dir.is_dir():
        return 0

    try:
        for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
            p = Path(dirpath)
            if p == root_dir or is_reparse_point(p):
                continue
            try:
                # Verifica se a pasta está realmente vazia
                if not any(p.iterdir()):
                    p.rmdir()
                    removed += 1
            except (OSError, PermissionError):
                pass
    except Exception:
        pass
    return removed
