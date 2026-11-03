"""
Módulo de Gerenciamento e Comparação de Benchmarks - PERFORMANCE LAB.
Salva execuções, realiza comparações estatísticas antes/depois da otimização
e exporta resultados em CSV e HTML.
"""
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.utils.logger import get_app_dir, app_logger

def get_benchmarks_file() -> Path:
    b_dir = get_app_dir() / "Benchmarks"
    b_dir.mkdir(parents=True, exist_ok=True)
    return b_dir / "benchmarks_history.json"

def load_all_benchmarks() -> List[Dict[str, Any]]:
    """Carrega o histórico de benchmarks salvos."""
    b_file = get_benchmarks_file()
    if not b_file.exists():
        return []
    try:
        data = json.loads(b_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as e:
        app_logger.warning(f"Erro ao carregar histórico de benchmarks: {e}")
        return []

def save_benchmark_run(run_data: Dict[str, Any]) -> bool:
    """Salva uma nova execução de benchmark."""
    try:
        b_file = get_benchmarks_file()
        history = load_all_benchmarks()
        
        # Garante ID e timestamp
        if "id" not in run_data:
            run_data["id"] = f"bench_{int(time.time())}"
        if "timestamp" not in run_data:
            run_data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        history.insert(0, run_data)
        b_file.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
        app_logger.info(f"Benchmark salvo: {run_data.get('title', run_data['id'])}")
        return True
    except Exception as e:
        app_logger.error(f"Erro ao salvar benchmark: {e}")
        return False

def compare_benchmarks(baseline: Dict[str, Any], optimized: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compara duas sessões de benchmark (Linha de Base vs Otimizado)
    calculando variações absolutas e percentuais reais.
    """
    def _calc_diff(base_val: float, opt_val: float, higher_is_better: bool = True):
        diff = opt_val - base_val
        pct = round(((opt_val - base_val) / max(base_val, 0.001)) * 100.0, 1)
        improved = diff > 0 if higher_is_better else diff < 0
        return {
            "baseline": round(base_val, 1),
            "optimized": round(opt_val, 1),
            "diff": round(diff, 1),
            "pct_change": pct,
            "improved": improved
        }

    b_m = baseline.get("metrics", baseline)
    o_m = optimized.get("metrics", optimized)

    comparison = {
        "title": f"Comparação: {baseline.get('title', 'Baseline')} vs {optimized.get('title', 'Otimizado')}",
        "game": optimized.get("game", baseline.get("game", "Desconhecido")),
        "resolution": optimized.get("resolution", baseline.get("resolution", "N/A")),
        "settings": optimized.get("settings", baseline.get("settings", "Padrão")),
        "duration_baseline_sec": b_m.get("duration_seconds", 0),
        "duration_optimized_sec": o_m.get("duration_seconds", 0),
        "avg_fps": _calc_diff(b_m.get("avg_fps", 0), o_m.get("avg_fps", 0), higher_is_better=True),
        "one_percent_low_fps": _calc_diff(b_m.get("one_percent_low_fps", 0), o_m.get("one_percent_low_fps", 0), higher_is_better=True),
        "zero_one_percent_low_fps": _calc_diff(b_m.get("zero_one_percent_low_fps", 0), o_m.get("zero_one_percent_low_fps", 0), higher_is_better=True),
        "avg_frametime_ms": _calc_diff(b_m.get("avg_frametime_ms", 0), o_m.get("avg_frametime_ms", 0), higher_is_better=False),
        "consistency_score": _calc_diff(b_m.get("consistency_score_percent", 0), o_m.get("consistency_score_percent", 0), higher_is_better=True),
    }

    return comparison
