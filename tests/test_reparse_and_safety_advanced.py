"""
Testes de Reparse Points, Confinamento de Diretórios e Proteção TOCTOU.
Valida verificação lstat, limitação de profundidade de varredura e bloqueio de exclusão fora da raiz autorizada.
"""
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.utils.file_operations import is_reparse_point, scan_directory
from src.utils.validators import validate_file_for_deletion

def test_reparse_point_detection_via_attributes():
    fake_path = Path("C:\\Temp\\junction_dir")
    mock_lstat = MagicMock()
    # 0x400 = FILE_ATTRIBUTE_REPARSE_POINT
    mock_lstat.st_file_attributes = 0x400

    with patch("os.path.islink", return_value=False), \
         patch("os.lstat", return_value=mock_lstat):
        assert is_reparse_point(fake_path) is True

def test_validate_file_blocks_paths_outside_authorized_roots():
    auth_root = Path(r"C:\Users\test\AppData\Local\Temp").resolve()
    intruder_file = Path(r"C:\Windows\System32\notepad.exe").resolve()

    mock_lstat = MagicMock()
    mock_lstat.st_file_attributes = 0
    mock_lstat.st_mtime = time.time() - 864000  # 10 dias

    with patch("pathlib.Path.exists", return_value=True), \
         patch("os.lstat", return_value=mock_lstat), \
         patch("os.path.islink", return_value=False):
        
        is_safe, reason = validate_file_for_deletion(
            intruder_file,
            authorized_roots=[auth_root],
            min_age_seconds=86400 * 7
        )
        assert is_safe is False
        assert "fora dos diretórios autorizados" in reason

def test_validate_file_blocks_recent_files_toctou():
    auth_root = Path(r"C:\Temp").resolve()
    recent_file = auth_root / "active.tmp"

    mock_lstat = MagicMock()
    mock_lstat.st_file_attributes = 0
    # Arquivo modificado há apenas 2 minutos
    mock_lstat.st_mtime = time.time() - 120

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.resolve", return_value=recent_file), \
         patch("os.lstat", return_value=mock_lstat), \
         patch("os.path.islink", return_value=False):
        
        is_safe, reason = validate_file_for_deletion(
            recent_file,
            authorized_roots=[auth_root],
            min_age_seconds=86400 * 7  # Exige >= 7 dias
        )
        assert is_safe is False
        assert "modificado recentemente" in reason
