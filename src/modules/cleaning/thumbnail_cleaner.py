"""
Módulo de Limpeza do Cache de Miniaturas (Thumbnails) do Windows.
Localiza e remove thumbcache_*.db sem interromper o Explorer à força.
Suporta acompanhamento de progresso real e relatório separado de Dry Run.
"""
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager, RiskLevel

def get_thumbnail_cache_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Microsoft" / "Windows" / "Explorer"
    return Path()

def analyze_thumbnail_cache(progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict[str, Any]:
    """Analisa arquivos de cache de miniatura existentes com progresso."""
    cache_dir = get_thumbnail_cache_dir()
    files_found: List[Dict[str, Any]] = []
    total_bytes = 0

    if progress_callback:
        progress_callback(20, "Localizando arquivos de cache de miniaturas...")

    if cache_dir.exists() and cache_dir.is_dir():
        try:
            items = list(cache_dir.glob("thumbcache_*.db"))
            total_items = len(items)
            for idx, p in enumerate(items):
                if progress_callback and total_items > 0:
                    pct = 20 + int((idx / total_items) * 70)
                    progress_callback(pct, f"Analisando {p.name}...")
                try:
                    size = p.stat().st_size
                    total_bytes += size
                    files_found.append({"path": str(p), "size": size})
                except (OSError, PermissionError):
                    continue
        except Exception as e:
            app_logger.warning(f"Erro ao listar miniaturas: {e}")

    if progress_callback:
        progress_callback(100, "Varredura de miniaturas concluída.")

    return {
        "status": "OK",
        "count": len(files_found),
        "reclaimable_bytes": total_bytes,
        "reclaimable_mb": round(total_bytes / (1024 ** 2), 2),
        "files": files_found
    }

def clean_thumbnail_cache(
    dry_run: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Remove arquivos de miniatura desbloqueados com progresso real item por item.
    Arquivos bloqueados pela sessão ativa do Explorer são ignorados com segurança.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="THUMBNAIL_CLEANUP",
        user_confirmed=False
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    if progress_callback:
        progress_callback(10, "Iniciando análise de miniaturas...")

    analysis = analyze_thumbnail_cache()
    files = analysis["files"]
    total_files = len(files)

    deleted_count = 0
    deleted_bytes = 0
    would_delete_count = 0
    would_delete_bytes = 0
    skipped_count = 0

    for idx, item in enumerate(files):
        if progress_callback and total_files > 0:
            pct = 15 + int((idx / total_files) * 80)
            progress_callback(pct, f"Processando miniatura {idx + 1} de {total_files}...")

        p = Path(item["path"])
        sz = item["size"]

        if dry_run:
            would_delete_count += 1
            would_delete_bytes += sz
            continue

        try:
            p.unlink(missing_ok=True)
            deleted_count += 1
            deleted_bytes += sz
        except (PermissionError, OSError):
            skipped_count += 1

    if progress_callback:
        progress_callback(100, "Concluído.")

    if dry_run:
        would_mb = round(would_delete_bytes / (1024 ** 2), 2)
        return {
            "success": True,
            "dry_run": True,
            "would_delete_count": would_delete_count,
            "would_delete_bytes": would_delete_bytes,
            "would_delete_mb": would_mb,
            "deleted_count": 0,
            "deleted_bytes": 0,
            "skipped_locked": 0,
            "message": f"Simulação concluída: {would_delete_count} arquivos de miniatura ({would_mb} MB) podem ser liberados."
        }

    freed_mb = round(deleted_bytes / (1024 ** 2), 2)
    app_logger.info(
        f"Limpeza de miniaturas: {deleted_count} removidos ({freed_mb} MB), "
        f"{skipped_count} bloqueados pelo Explorer ignorados."
    )

    return {
        "success": True,
        "dry_run": False,
        "deleted_count": deleted_count,
        "deleted_bytes": deleted_bytes,
        "freed_mb": freed_mb,
        "skipped_locked": skipped_count,
        "message": f"Cache de miniaturas limpo: {deleted_count} arquivos removidos ({freed_mb} MB liberados). {skipped_count} em uso foram preservados."
    }
