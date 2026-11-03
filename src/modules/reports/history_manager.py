"""
Gerenciador de Histórico de Operações e Manutenções.
Registra cada ação realizada com carimbo de data/hora, status e espaço liberado.
"""
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from src.utils.logger import app_logger, get_app_dir

def get_history_file() -> Path:
    return get_app_dir() / "operation_history.json"

def log_operation_event(
    operation_name: str,
    status: str,
    details: str = "",
    freed_mb: float = 0.0,
    files_affected: int = 0,
    error_message: str = ""
):
    """Registra uma operação no histórico persistente do usuário."""
    event = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "operation": operation_name,
        "status": status,
        "details": details,
        "freed_mb": round(freed_mb, 2),
        "files_affected": files_affected,
        "error_message": error_message
    }

    history = get_operation_history()
    history.insert(0, event)  # Mais recente primeiro

    # Mantém os últimos 500 registros
    if len(history) > 500:
        history = history[:500]

    try:
        with open(get_history_file(), "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        app_logger.error(f"Erro ao salvar histórico de operação: {e}")

def get_operation_history() -> List[Dict[str, Any]]:
    """Lê todo o histórico de operações gravado."""
    h_file = get_history_file()
    if not h_file.exists():
        return []

    try:
        with open(h_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        app_logger.warning(f"Erro ao ler histórico: {e}")
        return []

def clear_operation_history() -> bool:
    """Limpa o histórico de operações."""
    try:
        with open(get_history_file(), "w", encoding="utf-8") as f:
            json.dump([], f)
        return True
    except Exception:
        return False
