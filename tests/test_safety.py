"""
Testes de Segurança e do Safety Manager do ALTUS PC OPTIMIZER.
"""
import pytest
from src.core.safety_manager import safety_manager, RiskLevel, FORBIDDEN_OPERATIONS

def test_forbidden_operations_are_blocked():
    """Garante que operações proibidas sejam bloqueadas sem exceção."""
    for op_id in FORBIDDEN_OPERATIONS.keys():
        auth = safety_manager.validate_and_authorize(
            op_id=op_id,
            risk_level=RiskLevel.LEVEL_1_SAFE
        )
        assert not auth["authorized"]
        assert auth["level"] == RiskLevel.FORBIDDEN
        assert "BLOQUEADA" in auth["reason"]

def test_safe_operations_allowed():
    """Garante que operações de Nível 1 seguras sejam autorizadas."""
    auth = safety_manager.validate_and_authorize(
        op_id="ANALYZE_TEMP",
        risk_level=RiskLevel.LEVEL_1_SAFE,
        requires_admin=False
    )
    assert auth["authorized"]

def test_controlled_operations_require_confirmation():
    """Garante que operações de Nível 2 exijam confirmação do usuário."""
    # Sem confirmação
    auth_denied = safety_manager.validate_and_authorize(
        op_id="CUSTOM_ACTION",
        risk_level=RiskLevel.LEVEL_2_CONTROLLED,
        user_confirmed=False
    )
    assert not auth_denied["authorized"]
    assert auth_denied.get("needs_confirmation") is True

    # Com confirmação
    auth_ok = safety_manager.validate_and_authorize(
        op_id="CUSTOM_ACTION",
        risk_level=RiskLevel.LEVEL_2_CONTROLLED,
        user_confirmed=True
    )
    assert auth_ok["authorized"]
