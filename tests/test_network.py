"""
Testes do Módulo de Diagnóstico de Rede e Validadores.
"""
from src.utils.validators import is_valid_ipv4
from src.modules.network.network_analyzer import get_network_adapters_info
from src.modules.network.connection_monitor import check_internet_reachability
from src.modules.network.dns_optimizer import DNS_PROFILES

def test_ipv4_validation():
    assert is_valid_ipv4("192.168.1.1")
    assert is_valid_ipv4("8.8.8.8")
    assert is_valid_ipv4("10.0.0.254")
    assert not is_valid_ipv4("999.999.999.999")
    assert not is_valid_ipv4("invalid-ip")
    assert not is_valid_ipv4("192.168.1")

def test_dns_profiles_integrity():
    for name, prof in DNS_PROFILES.items():
        assert "desc" in prof
        if name != "DHCP":
            assert is_valid_ipv4(prof["primary"])
            assert is_valid_ipv4(prof["secondary"])

def test_internet_reachability():
    # Testa conectividade com timeout curto
    res = check_internet_reachability(timeout=2.0)
    assert "connected" in res
    assert "status" in res
