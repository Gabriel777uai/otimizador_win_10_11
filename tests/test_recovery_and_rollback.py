"""
Testes do Auto Recovery Center, Livro-Razão e Mecanismo de Rollback.
Valida reversão de DNS (estático vs DHCP), plano de energia e recuperação de tarefas interrompidas.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.core.recovery_manager import (
    register_recovery_operation, rollback_operation,
    check_and_recover_interrupted_operations, load_ledger, update_operation_status
)

def test_recovery_operation_registration():
    rec_id = register_recovery_operation(
        op_id="APPLY_CUSTOM_DNS",
        category="DNS",
        original_state={"adapter_name": "Ethernet", "mode": "static", "dns_servers": ["10.1.1.5", "10.1.1.50"]},
        applied_state={"mode": "static", "dns_servers": ["1.1.1.1", "1.0.0.1"]},
        restore_strategy="RESTORE_DNS",
        status="APPLIED"
    )
    assert rec_id.startswith("rec_dns_")
    ledger = load_ledger()
    assert any(r["record_id"] == rec_id for r in ledger)

def test_rollback_dns_static_exact_servers():
    rec_id = register_recovery_operation(
        op_id="APPLY_CUSTOM_DNS",
        category="DNS",
        original_state={"adapter_name": "Ethernet", "mode": "static", "dns_servers": ["192.168.1.1", "192.168.1.2"]},
        applied_state={"dns_servers": ["8.8.8.8"]},
        restore_strategy="RESTORE_DNS",
        status="APPLIED"
    )
    
    with patch("src.modules.network.dns_optimizer._apply_dns_state", return_value=(True, "OK")) as mock_apply:
        res = rollback_operation(rec_id)
        assert res["success"] is True
        mock_apply.assert_called_once_with("Ethernet", "static", ["192.168.1.1", "192.168.1.2"])

def test_rollback_dns_dhcp_mode():
    rec_id = register_recovery_operation(
        op_id="APPLY_CUSTOM_DNS",
        category="DNS",
        original_state={"adapter_name": "Wi-Fi", "mode": "dhcp", "dns_servers": []},
        applied_state={"dns_servers": ["1.1.1.1"]},
        restore_strategy="RESTORE_DNS",
        status="APPLIED"
    )
    
    with patch("src.modules.network.dns_optimizer._apply_dns_state", return_value=(True, "OK")) as mock_apply:
        res = rollback_operation(rec_id)
        assert res["success"] is True
        mock_apply.assert_called_once_with("Wi-Fi", "dhcp", [])

def test_interrupted_operation_auto_recovery_on_startup():
    rec_id = register_recovery_operation(
        op_id="POWER_PLAN_SET",
        category="POWER",
        original_state={"power_plan_guid": "381b4222-f694-41f0-9685-ff5bb260df2e"},
        applied_state={"power_plan_guid": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"},
        restore_strategy="RESTORE_POWER_PLAN",
        status="IN_PROGRESS"  # Simula encerramento súbito antes de finalizar
    )

    with patch("src.core.recovery_manager.rollback_operation", return_value={"success": True, "message": "OK"}):
        recovered = check_and_recover_interrupted_operations()
        assert any(r["record_id"] == rec_id for r in recovered)
