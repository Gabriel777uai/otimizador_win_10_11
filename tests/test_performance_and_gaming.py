"""
Testes de Métricas de Performance, Smart Game Session e Thermal Guard.
Valida cálculos de FPS Médio, 1% Low, consistência, proteção contra reciclagem de PID
e regras estritas de Thermal Throttling.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.modules.performance.metrics_calculator import calculate_benchmark_metrics
from src.modules.performance.benchmark_manager import compare_benchmarks
from src.modules.thermal.thermal_manager import ThermalGuard
from src.modules.gaming.game_optimizer import SmartGameSession

def test_benchmark_metrics_calculations():
    # 100 quadros a 16.6 ms (~60 FPS) com 1 quadro engasgado a 100 ms (10 FPS)
    frametimes = [16.6] * 99 + [100.0]
    metrics = calculate_benchmark_metrics(frametimes)

    assert metrics["has_data"] is True
    assert metrics["total_frames"] == 100
    assert 56.0 <= metrics["avg_fps"] <= 61.0
    # 1% low deve capturar o quadro de 100ms
    assert metrics["one_percent_low_fps"] <= 15.0
    assert metrics["min_fps"] <= 12.0
    assert metrics["consistency_score_percent"] > 0

def test_benchmark_comparison_deltas():
    base = {
        "title": "Baseline",
        "game": "TestGame",
        "metrics": {"avg_fps": 60.0, "one_percent_low_fps": 40.0, "avg_frametime_ms": 16.6, "consistency_score_percent": 85.0}
    }
    opt = {
        "title": "Otimizado",
        "game": "TestGame",
        "metrics": {"avg_fps": 72.0, "one_percent_low_fps": 52.0, "avg_frametime_ms": 13.8, "consistency_score_percent": 94.0}
    }
    comp = compare_benchmarks(base, opt)
    assert comp["avg_fps"]["diff"] == 12.0
    assert comp["avg_fps"]["pct_change"] == 20.0
    assert comp["avg_fps"]["improved"] is True
    assert comp["one_percent_low_fps"]["improved"] is True

def test_thermal_throttling_requires_evidence():
    guard = ThermalGuard()
    
    # Caso 1: Temperatura alta (85°C), mas clock em velocidade máxima (4000 MHz) -> NÃO é throttling
    cpu_info_no_drop = {
        "temperature_c": 85.0,
        "frequency": {"current_mhz": 4000.0, "max_mhz": 4000.0}
    }
    eval1 = guard.evaluate_throttling(cpu_info_no_drop, {"available": False})
    assert eval1["throttling_detected"] is False

    # Caso 2: Temperatura crítica (96°C) e clock despencando para 1800 MHz (vs 4000 MHz base) -> É THROTTLING
    cpu_info_drop = {
        "temperature_c": 96.0,
        "frequency": {"current_mhz": 1800.0, "max_mhz": 4000.0}
    }
    eval2 = guard.evaluate_throttling(cpu_info_drop, {"available": False})
    assert eval2["throttling_detected"] is True

def test_smart_game_session_protects_pid_reuse():
    """Garante que a sessão não monitore um processo diferente caso o PID seja reciclado."""
    mock_proc = MagicMock()
    mock_proc.create_time.return_value = 1000.0
    mock_proc.name.return_value = "game.exe"
    mock_proc.nice.return_value = 0

    with patch("psutil.Process", return_value=mock_proc), \
         patch("src.modules.gaming.game_optimizer.is_running_on_battery", return_value=False), \
         patch("src.modules.gaming.game_optimizer.get_current_power_plan_guid", return_value="guid-1"):

        session = SmartGameSession(pid=1234, game_name="TestGame")
        res = session.start_session()
        assert res["success"] is True
        assert session.create_time == 1000.0

        # Simula que o processo com mesmo PID agora tem create_time diferente (processo diferente)
        mock_proc.create_time.return_value = 2000.0
        mock_proc.is_running.return_value = True

        session.stop_session()
        assert session.is_active is False
