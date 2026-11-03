"""
Validadores de segurança para operações de disco, rede e sistema.
Garante proteção de dados pessoais, diretórios críticos do Windows e integridade de caminhos.
"""
import os
import re
import time
from pathlib import Path
from typing import List, Tuple

# Diretórios críticos do Windows que NUNCA podem ser limpos por rotinas padrão
CRITICAL_WINDOWS_DIRS = [
    Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve(),
    Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32",
    Path(os.environ.get("SystemRoot", r"C:\Windows")) / "SysWOW64",
    Path(os.environ.get("SystemRoot", r"C:\Windows")) / "WinSxS",
    Path(r"C:\Program Files").resolve(),
    Path(r"C:\Program Files (x86)").resolve(),
]

# Diretórios de dados pessoais do usuário que NUNCA devem ser tocados
PROTECTED_USER_DIRS = ["Documents", "Desktop", "Downloads", "Pictures", "Videos", "Music"]

def is_safe_temp_path(target: Path) -> bool:
    """Verifica se o diretório é legitimamente uma pasta temporária permitida do usuário ou sistema."""
    try:
        target_resolved = target.resolve()
    except Exception:
        return False

    user_temp_env = os.environ.get("TEMP", "")
    user_temp = Path(user_temp_env).resolve() if user_temp_env else None
    win_temp = Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve() / "Temp"

    # Não permitir raízes de unidade (ex: C:\)
    if len(target_resolved.parts) <= 1:
        return False

    # Deve estar sob user_temp ou win_temp
    is_under_user_temp = False
    is_under_win_temp = False
    try:
        if user_temp:
            is_under_user_temp = (target_resolved == user_temp or user_temp in target_resolved.parents)
    except Exception:
        pass

    try:
        is_under_win_temp = (target_resolved == win_temp or win_temp in target_resolved.parents)
    except Exception:
        pass

    if not (is_under_user_temp or is_under_win_temp):
        return False

    # Não pode coincidir nem ser ancestral de pastas pessoais do usuário
    user_profile = Path(os.environ.get("USERPROFILE", "")).resolve()
    for prot in PROTECTED_USER_DIRS:
        prot_path = user_profile / prot
        if prot_path == target_resolved or prot_path in target_resolved.parents:
            return False

    return True

def validate_file_for_deletion(
    file_path: Path,
    authorized_roots: List[Path],
    min_age_seconds: int = 0
) -> Tuple[bool, str]:
    """
    Validação em tempo real imediatamente antes da exclusão de um arquivo (Proteção TOCTOU).
    Verifica existência, raízes autorizadas, atributos de reparse point e idade.
    """
    try:
        if not file_path.exists():
            return False, "Arquivo não existe mais."

        # Usa lstat para inspecionar o próprio link/arquivo sem seguir
        lst = os.lstat(file_path)

        # Checa reparse point (0x400) ou symlink
        if os.path.islink(file_path) or (getattr(lst, "st_file_attributes", 0) & 0x400) != 0:
            return False, "Arquivo é um Reparse Point ou Link Simbólico (preservado por segurança)."

        resolved = file_path.resolve()

        # Garante confinamento dentro das raízes autorizadas
        is_confined = False
        for root in authorized_roots:
            try:
                root_resolved = root.resolve()
                if resolved == root_resolved or root_resolved in resolved.parents:
                    is_confined = True
                    break
            except Exception:
                continue

        if not is_confined:
            return False, f"Caminho '{file_path}' está fora dos diretórios autorizados de limpeza."

        # Revalida idade imediatamente antes da exclusão
        if min_age_seconds > 0:
            file_age = time.time() - lst.st_mtime
            if file_age < min_age_seconds:
                return False, f"Arquivo foi modificado recentemente ({round(file_age/86400, 2)} dias); preservado."

        return True, "Arquivo válido para exclusão."

    except Exception as e:
        return False, f"Exceção durante validação: {e}"

def is_valid_ipv4(ip: str) -> bool:
    """Valida formato de endereço IPv4."""
    pattern = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    return bool(re.match(pattern, ip.strip()))
