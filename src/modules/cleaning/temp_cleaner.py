"""
Módulo de Limpeza Inteligente de Arquivos Temporários.
Regras fundamentais:
- Exclusão com filtro de idade configurável (padrão: >= 7 dias).
- Ignora arquivos em uso ou bloqueados.
- Não segue links simbólicos ou junções (junction points).
- Revalida arquivos imediatamente antes da remoção (proteção TOCTOU).
- Não afeta arquivos pessoais ou do sistema fora de %TEMP% e C:\\Windows\\Temp.
- Relatório separado para simulação (Dry Run).
"""
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from src.utils.logger import app_logger
from src.utils.file_operations import scan_directory, clean_files_safely, clean_empty_directories
from src.utils.validators import is_safe_temp_path
from src.core.safety_manager import safety_manager, RiskLevel

def get_temp_targets() -> List[Path]:
    """Retorna a lista de diretórios temporários autorizados para análise."""
    targets = []
    # Temp do Usuário (%TEMP%)
    user_temp_env = os.environ.get("TEMP")
    if user_temp_env:
        user_temp = Path(user_temp_env).resolve()
        if user_temp.exists() and is_safe_temp_path(user_temp):
            targets.append(user_temp)

    # Temp do Windows (C:\Windows\Temp)
    win_temp = Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve() / "Temp"
    if win_temp.exists() and is_safe_temp_path(win_temp):
        targets.append(win_temp)

    return targets

def analyze_temp_files(
    min_age_days: int = 7,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Analisa os diretórios temporários sem apagar nada.
    Retorna métricas de arquivos elegíveis e espaço potencialmente liberável.
    """
    targets = get_temp_targets()
    total_eligible_bytes = 0
    total_eligible_files = 0
    details = []

    total_targets = len(targets)
    for idx, path in enumerate(targets):
        if progress_callback:
            pct = int((idx / max(total_targets, 1)) * 100)
            progress_callback(pct, f"Analisando {path.name}...")

        metrics = scan_directory(path, min_age_days=min_age_days, progress_callback=progress_callback)
        total_eligible_bytes += metrics["eligible_bytes"]
        total_eligible_files += metrics["eligible_files"]
        details.append(metrics)

    if progress_callback:
        progress_callback(100, "Análise de arquivos concluída.")

    return {
        "status": "OK",
        "min_age_days": min_age_days,
        "eligible_files_count": total_eligible_files,
        "reclaimable_bytes": total_eligible_bytes,
        "reclaimable_mb": round(total_eligible_bytes / (1024 ** 2), 2),
        "details": details
    }

def execute_temp_cleanup(
    min_age_days: int = 7,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Executa a limpeza dos arquivos temporários elegíveis.
    Registra no log e retorna dados precisos do que foi efetivamente liberado vs simulado.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="TEMP_CLEANUP",
        user_confirmed=False
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    if progress_callback:
        progress_callback(10, "Localizando alvos e analisando elegibilidade...")

    targets = get_temp_targets()
    analysis = analyze_temp_files(min_age_days=min_age_days)

    total_deleted_bytes = 0
    total_deleted_files = 0
    total_would_delete_bytes = 0
    total_would_delete_files = 0
    total_skipped = 0

    all_files_to_clean = []
    for item in analysis["details"]:
        all_files_to_clean.extend(item.get("files_to_clean", []))

    total_items = len(all_files_to_clean)

    def sub_progress(p: int, msg: str):
        if progress_callback:
            # Mapeia de 20% a 90%
            overall = 20 + int((p / 100) * 70)
            progress_callback(overall, msg)

    clean_res = clean_files_safely(
        all_files_to_clean,
        authorized_roots=targets,
        min_age_days=min_age_days,
        dry_run=dry_run,
        progress_callback=sub_progress
    )

    if dry_run:
        total_would_delete_files = clean_res["would_delete_count"]
        total_would_delete_bytes = clean_res["would_delete_bytes"]
        would_mb = round(total_would_delete_bytes / (1024 ** 2), 2)
        if progress_callback:
            progress_callback(100, "Simulação concluída.")
        return {
            "success": True,
            "dry_run": True,
            "simulated_files_count": total_would_delete_files,
            "simulated_bytes": total_would_delete_bytes,
            "simulated_mb": would_mb,
            "deleted_files_count": 0,
            "deleted_bytes": 0,
            "deleted_mb": 0.0,
            "message": f"Simulação concluída: {total_would_delete_files} arquivos ({would_mb} MB) seriam removidos com segurança."
        }

    total_deleted_bytes = clean_res["deleted_bytes"]
    total_deleted_files = clean_res["deleted_count"]
    total_skipped = clean_res["skipped_locked"]

    if progress_callback:
        progress_callback(95, "Limpando diretórios vazios residuais...")

    for target in targets:
        clean_empty_directories(target, authorized_roots=targets)

    if progress_callback:
        progress_callback(100, "Limpeza concluída.")

    freed_mb = round(total_deleted_bytes / (1024 ** 2), 2)
    app_logger.info(
        f"Limpeza de temporários concluída: {total_deleted_files} arquivos removidos, "
        f"{freed_mb} MB liberados, {total_skipped} arquivos em uso ignorados."
    )

    return {
        "success": True,
        "dry_run": False,
        "deleted_files_count": total_deleted_files,
        "deleted_bytes": total_deleted_bytes,
        "deleted_mb": freed_mb,
        "skipped_locked_count": total_skipped,
        "message": f"Limpeza concluída com sucesso: {total_deleted_files} arquivos removidos ({freed_mb} MB liberados)."
    }
