"""
Testes do Módulo de Limpeza Segura e Validação de Diretórios.
"""
from pathlib import Path
from src.utils.validators import is_safe_temp_path
from src.utils.file_operations import scan_directory, clean_files_safely
from src.modules.cleaning.temp_cleaner import analyze_temp_files, execute_temp_cleanup

def test_safe_temp_path_validation():
    # Caminhos críticos que NÃO podem ser aceitos
    assert not is_safe_temp_path(Path("C:\\Windows"))
    assert not is_safe_temp_path(Path("C:\\Windows\\System32"))
    assert not is_safe_temp_path(Path("C:\\Program Files"))
    assert not is_safe_temp_path(Path("C:\\"))

def test_temp_cleanup_dry_run():
    # Executa em modo DRY RUN para garantir que nenhum arquivo real seja apagado
    res = execute_temp_cleanup(min_age_days=7, dry_run=True)
    assert res["success"] is True
    assert res["dry_run"] is True
    assert "deleted_files_count" in res
    assert "deleted_bytes" in res

def test_clean_files_safely_dry_run():
    fake_files = [
        {"path": "C:\\temp\\fake1.tmp", "size": 1024, "age_days": 10},
        {"path": "C:\\temp\\fake2.tmp", "size": 2048, "age_days": 15}
    ]
    res = clean_files_safely(fake_files, dry_run=True)
    # Requisito 1.6: arquivos simulados devem estar em would_delete_count e NUNCA em deleted_count
    assert res["would_delete_count"] == 2
    assert res["would_delete_bytes"] == 3072
    assert res["deleted_count"] == 0
    assert res["deleted_bytes"] == 0
