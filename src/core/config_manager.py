"""
Módulo de Gerenciamento e Persistência de Configurações - ALTUS PC OPTIMIZER.
Salva preferências de interface, temas, animações e agendamento em settings.json no diretório do usuário.
"""
import json
from pathlib import Path
from typing import Dict, Any
from src.utils.logger import get_app_dir, app_logger

DEFAULT_CONFIG: Dict[str, Any] = {
    "theme": "Dark Navy (Padrão Altus)",
    "enable_animations": True,
    "enable_toasts": True,
    "scheduled_maintenance_enabled": False,
    "scheduled_frequency": "WEEKLY",
    "scheduled_day": "SUN",
    "scheduled_time": "12:00"
}

def get_config_file_path() -> Path:
    return get_app_dir() / "settings.json"

def load_app_config() -> Dict[str, Any]:
    """Carrega as configurações do usuário do arquivo settings.json."""
    cfg_path = get_config_file_path()
    if not cfg_path.exists():
        save_app_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        # Garante que novas chaves existam
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
        return merged
    except Exception as e:
        app_logger.warning(f"Erro ao carregar settings.json: {e}")
        return DEFAULT_CONFIG.copy()

def save_app_config(config_data: Dict[str, Any]) -> bool:
    """Persiste as configurações do usuário em disco."""
    try:
        cfg_path = get_config_file_path()
        cfg_path.write_text(json.dumps(config_data, indent=2, ensure_ascii=False), encoding="utf-8")
        app_logger.info("Configurações do usuário persistidas com sucesso.")
        return True
    except Exception as e:
        app_logger.error(f"Erro ao salvar settings.json: {e}")
        return False
