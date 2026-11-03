"""
Testes de Detecção de Hardware e Sistema.
"""
from src.core.system_detection import (
    get_cpu_info, get_memory_info, get_os_info, get_disk_info, get_full_system_snapshot
)

def test_cpu_detection():
    cpu = get_cpu_info()
    assert "model" in cpu
    assert cpu["cores_physical"] >= 1
    assert cpu["threads_logical"] >= 1
    assert isinstance(cpu["current_percent"], (int, float))

def test_memory_detection():
    mem = get_memory_info()
    assert mem["total_gb"] > 0
    assert mem["percent_used"] >= 0
    assert mem["available_gb"] >= 0

def test_os_detection():
    os_info = get_os_info()
    assert "caption" in os_info
    assert "build" in os_info

def test_full_system_snapshot():
    snap = get_full_system_snapshot()
    assert "os" in snap
    assert "cpu" in snap
    assert "memory" in snap
    assert "disks" in snap
