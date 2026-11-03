"""
Módulo de registro e logging centralizado do ALTUS PC OPTIMIZER.
Salva logs no diretório padrão de dados do usuário (platformdirs).
"""
import os
import sys
import logging
from pathlib import Path
from platformdirs import user_data_dir

APP_NAME = "AltusPCOptimizer"
APP_AUTHOR = "AltusSoftware"

def get_app_dir() -> Path:
    """Retorna o diretório base de dados da aplicação."""
    path = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_logs_dir() -> Path:
    """Retorna o diretório de logs da aplicação."""
    logs_dir = get_app_dir() / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir

def setup_logger(name: str = "AltusOptimizer") -> logging.Logger:
    """Configura o logger principal da aplicação."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler de arquivo
    log_file = get_logs_dir() / "altus_optimizer.log"
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Erro ao inicializar FileHandler de log: {e}", file=sys.stderr)

    # Handler de console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    return logger

app_logger = setup_logger()
