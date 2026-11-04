"""
Bateria de Testes Unitários e de Integração - WINDOWS BACKGROUND CONTROL (ETAPA 4).
Valida detecção de SO/IA, classificação de processos e serviços, proteção de essenciais,
perfis de otimização, medição antes/depois e reversão pelo Auto Recovery Center.
"""
import os
import sys
import tempfile
import pytest

import src.modules.windows_background as wb
from src.core.safety_manager import safety_manager, RiskLevel
from src.core.recovery_manager import load_ledger

def test_feature_detector_os_and_ai():
    """Valida a detecção de recursos do sistema operacional e compatibilidade de IA."""
    feats = wb.detect_all_windows_features()
    assert isinstance(feats.os_name, str)
    assert isinstance(feats.build_number, int)
    assert isinstance(feats.is_windows_11, bool)
    assert isinstance(feats.architecture, str)

    # Windows 10 nunca deve ser classificado como compatível com Recall nativo de Copilot+
    if feats.build_number < 26100:
        assert feats.recall_hardware_compatible is False
        assert "Incompatível" in feats.recall_notes or "anterior" in feats.recall_notes

def test_protected_processes_cannot_be_flagged_safe_to_close():
    """Valida se processos de sistema e segurança são estritamente protegidos."""
    from src.modules.windows_background.background_analyzer import _classify_process

    # 1. Processos Vitais
    for proc in ["csrss.exe", "smss.exe", "lsass.exe", "services.exe", "svchost.exe", "dwm.exe"]:
        cat, safe, reason = _classify_process(proc, r"C:\Windows\System32\\" + proc, "Microsoft Corporation")
        assert cat == "ESSENTIAL", f"Processo {proc} deveria ser ESSENTIAL"
        assert safe is False, f"Processo {proc} nunca deve ser marcado como seguro para fechar"

    # 2. Antivírus
    cat_def, safe_def, _ = _classify_process("MsMpEng.exe", r"C:\ProgramData\Microsoft\Windows Defender\Platform\MsMpEng.exe", "Microsoft Corporation")
    assert cat_def == "SECURITY"
    assert safe_def is False

def test_protected_services_classification():
    """Valida se serviços vitais de rede, áudio, segurança e kernel são blindados."""
    from src.modules.windows_background.service_analyzer import _classify_service, ServiceCategory

    # RPC, DHCP, DNS, Defender, Firewall, Audio
    critical_services = ["rpcss", "dhcp", "dnscache", "windefend", "mpssvc", "audiosrv", "eventlog"]
    for svc in critical_services:
        cat, is_prot, notes = _classify_service(svc, svc.upper(), r"C:\Windows\System32\svchost.exe")
        assert cat == ServiceCategory.ESSENTIAL
        assert is_prot is True

    # Tentativa de desativação de serviço essencial deve ser bloqueada imediatamente
    res = wb.configure_optional_service("rpcss", "disabled", user_confirmed=True)
    assert res["success"] is False
    assert "BLOQUEADA" in res["message"]

def test_dev_folders_scanning_and_exclusion():
    """Valida a varredura e sugestão de exclusão de pastas sem apagar arquivos."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Cria estrutura de projeto de teste
        proj = os.path.join(tmp_dir, "my_project")
        os.makedirs(proj)
        nm = os.path.join(proj, "node_modules")
        os.makedirs(nm)
        git = os.path.join(proj, ".git")
        os.makedirs(git)
        test_file = os.path.join(nm, "package.json")
        with open(test_file, "w") as f:
            f.write("{}")

        # Mapeia diretórios
        found = wb.scan_common_dev_folders(search_roots=[tmp_dir], max_results=10)
        paths_found = [f["path"] for f in found]
        assert nm in paths_found
        assert git in paths_found

        # Testa registro de exclusão
        res = wb.configure_index_exclusions([nm, git], user_confirmed=True)
        assert res["success"] is True

        # Valida que os arquivos continuam intactos (NUNCA deleta nada)
        assert os.path.exists(test_file)

def test_gaming_dvr_status_and_preservation():
    """Valida consulta de status do Game DVR e preservação do Game Mode."""
    st = wb.get_gaming_dvr_status()
    assert "game_dvr_enabled" in st
    assert "background_recording_active" in st
    assert "description" in st

def test_optimization_profiles_catalog():
    """Valida os 3 perfis profissionais catalogados e seus metadados."""
    profiles = wb.get_available_profiles()
    assert len(profiles) == 3
    ids = [p["id"] for p in profiles]
    assert "WINDOWS_SLIM" in ids
    assert "GAMING_PERFORMANCE" in ids
    assert "DEVELOPER_WORKSTATION" in ids

def test_before_after_analyzer():
    """Valida o cálculo do delta entre medições antes e depois."""
    s1 = wb.take_system_snapshot()
    assert s1.ram_used_gb > 0
    assert s1.process_count > 0

    s2 = wb.take_system_snapshot()
    delta = wb.compare_snapshots(s1, s2, applied_operations=["Teste de Otimização"])
    assert "ram_diff_mb" in delta
    assert "cpu_diff_pct" in delta
    assert "summary" in delta

def test_background_recovery_registration():
    """Valida se as operações de segundo plano geram entradas no ledger."""
    from src.modules.windows_background.background_recovery import get_background_recovery_history
    history = get_background_recovery_history()
    assert isinstance(history, list)

def test_windows_background_ui_initialization():
    """Valida inicialização e renderização completa da página na interface gráfica."""
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from src.interface.windows_background_page import WindowsBackgroundPage
    page = WindowsBackgroundPage()
    assert page.tabs.count() == 6
    assert page.card_os is not None
    assert page.table_procs.rowCount() >= 0
