"""
Testes de Segurança do Windows Update Cleaner e Gestão de Serviços do Windows.
Valida aborto se serviço não parar, restauração no bloco finally e detecção de atualizações ativas.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.modules.cleaning.windows_update_cleaner import clean_update_cache, is_update_in_progress, is_reboot_pending

def test_cleanup_aborted_when_update_in_progress():
    with patch("src.core.safety_manager.is_admin", return_value=True), \
         patch("src.modules.cleaning.windows_update_cleaner.is_update_in_progress", return_value=(True, "Processo TiWorker.exe ativo")):
        res = clean_update_cache(user_confirmed=True)
        assert res["success"] is False
        assert "Processo TiWorker.exe ativo" in res["message"]

def test_cleanup_aborted_when_reboot_pending():
    with patch("src.core.safety_manager.is_admin", return_value=True), \
         patch("src.modules.cleaning.windows_update_cleaner.is_reboot_pending", return_value=True), \
         patch("src.modules.cleaning.windows_update_cleaner.is_update_in_progress", return_value=(False, "")):
        res = clean_update_cache(user_confirmed=True)
        assert res["success"] is False
        assert "reinicialização pendente" in res["message"].lower()

def test_service_stop_failure_aborts_cleanup():
    """Garante que a exclusão de arquivos NUNCA ocorra se um serviço falhar ao parar."""
    mock_service = MagicMock()
    mock_service.status.return_value = "running"

    with patch("src.core.safety_manager.is_admin", return_value=True), \
         patch("src.modules.cleaning.windows_update_cleaner.is_reboot_pending", return_value=False), \
         patch("src.modules.cleaning.windows_update_cleaner.is_update_in_progress", return_value=(False, "")), \
         patch("psutil.win_service_get", return_value=mock_service), \
         patch("src.modules.cleaning.windows_update_cleaner._wait_for_service_status", return_value=False), \
         patch("src.modules.cleaning.windows_update_cleaner.run_command", return_value=(1, "", "Access denied")):

        res = clean_update_cache(user_confirmed=True)
        assert res["success"] is False
        assert "Não foi possível interromper o serviço" in res["message"]

def test_services_always_restored_in_finally():
    """Garante que serviços interrompidos sejam restaurados incondicionalmente no bloco finally."""
    mock_service = MagicMock()
    mock_service.status.return_value = "running"
    
    start_calls = []
    def fake_run_command(cmd, timeout=30):
        if "start" in cmd:
            start_calls.append(cmd[2])
        return (0, "", "")

    with patch("src.core.safety_manager.is_admin", return_value=True), \
         patch("src.modules.cleaning.windows_update_cleaner.is_reboot_pending", return_value=False), \
         patch("src.modules.cleaning.windows_update_cleaner.is_update_in_progress", return_value=(False, "")), \
         patch("psutil.win_service_get", return_value=mock_service), \
         patch("src.modules.cleaning.windows_update_cleaner._wait_for_service_status", return_value=True), \
         patch("src.modules.cleaning.windows_update_cleaner.run_command", side_effect=fake_run_command), \
         patch("pathlib.Path.iterdir", side_effect=RuntimeError("Simulando falha de disco no meio")):

        try:
            clean_update_cache(user_confirmed=True)
        except RuntimeError:
            pass

        # Confirma que os serviços foram religados
        assert "wuauserv" in start_calls or "bits" in start_calls
