"""
Módulo de Detecção e Gerenciamento de Jogos.
Detecta bibliotecas da Steam e permite cadastro manual de títulos favoritos.
"""
import os
import json
import winreg
from pathlib import Path
from typing import List, Dict, Any
from src.utils.logger import app_logger, get_app_dir

def get_games_config_file() -> Path:
    return get_app_dir() / "games_library.json"

def detect_steam_games() -> List[Dict[str, Any]]:
    """Localiza jogos instalados na Steam através dos manifests oficiais."""
    games = []
    steam_path = None

    # Tenta achar caminho da Steam no Registro
    for hkey in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            k = winreg.OpenKey(hkey, r"Software\Valve\Steam")
            steam_path, _ = winreg.QueryValueEx(k, "SteamPath")
            winreg.CloseKey(k)
            if steam_path:
                break
        except Exception:
            continue

    if not steam_path:
        # Caminho padrão
        def_path = Path(r"C:\Program Files (x86)\Steam")
        if def_path.exists():
            steam_path = str(def_path)

    if not steam_path:
        return games

    steam_dir = Path(steam_path)
    steamapps = steam_dir / "steamapps"
    dirs_to_check = [steamapps]

    # Checar libraryfolders.vdf para bibliotecas em outros discos
    library_vdf = steamapps / "libraryfolders.vdf"
    if library_vdf.exists():
        try:
            with open(library_vdf, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if '"path"' in line:
                        parts = line.split('"path"')
                        if len(parts) > 1:
                            raw_p = parts[1].replace('"', '').strip()
                            extra_lib = Path(raw_p) / "steamapps"
                            if extra_lib.exists() and extra_lib not in dirs_to_check:
                                dirs_to_check.append(extra_lib)
        except Exception as e:
            app_logger.warning(f"Erro ao ler libraryfolders da Steam: {e}")

    for lib in dirs_to_check:
        common = lib / "common"
        if not common.exists():
            continue
        try:
            for item in common.iterdir():
                if item.is_dir():
                    # Procura executável principal
                    exes = list(item.glob("*.exe"))
                    main_exe = exes[0].name if exes else ""
                    exe_path = str(exes[0]) if exes else ""
                    games.append({
                        "name": item.name,
                        "source": "Steam",
                        "folder": str(item),
                        "executable": main_exe,
                        "exe_path": exe_path,
                        "favorite": False
                    })
        except Exception:
            continue

    return games

def load_user_games() -> List[Dict[str, Any]]:
    """Carrega os jogos cadastrados ou salvos pelo usuário."""
    cfg = get_games_config_file()
    if not cfg.exists():
        # Primeira execução: detecta Steam
        steam_games = detect_steam_games()
        save_user_games(steam_games)
        return steam_games

    try:
        with open(cfg, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        app_logger.error(f"Erro ao carregar lista de jogos: {e}")
        return []

def save_user_games(games: List[Dict[str, Any]]) -> bool:
    """Salva a biblioteca de jogos em disco."""
    cfg = get_games_config_file()
    try:
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump(games, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        app_logger.error(f"Erro ao salvar biblioteca de jogos: {e}")
        return False

def add_manual_game(name: str, exe_path: str) -> bool:
    """Adiciona manualmente um jogo à biblioteca."""
    p = Path(exe_path)
    if not p.exists() or not p.is_file():
        return False

    games = load_user_games()
    # Verifica se já existe
    for g in games:
        if g.get("exe_path", "").lower() == str(p).lower():
            return True

    games.append({
        "name": name,
        "source": "Manual",
        "folder": str(p.parent),
        "executable": p.name,
        "exe_path": str(p),
        "favorite": True
    })
    return save_user_games(games)


def find_running_game_process() -> Optional[Dict[str, Any]]:
    """
    Rastreia processos em execução e compara com os jogos cadastrados na biblioteca.
    Retorna o primeiro jogo em execução detectado com PID e create_time protegidos.
    """
    import psutil
    games = load_user_games()
    if not games:
        return None

    # Mapeia nomes de executáveis
    exe_map = {}
    for g in games:
        exe_name = g.get("executable", "").lower()
        if exe_name:
            exe_map[exe_name] = g

    for proc in psutil.process_iter(['pid', 'name', 'exe', 'create_time']):
        try:
            pname = (proc.info.get('name') or '').lower()
            if pname in exe_map:
                game_info = exe_map[pname]
                return {
                    "pid": proc.info['pid'],
                    "process_name": proc.info['name'],
                    "exe_path": proc.info.get('exe') or game_info.get("exe_path"),
                    "create_time": proc.info.get('create_time', 0.0),
                    "game_title": game_info.get("name", pname)
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return None
