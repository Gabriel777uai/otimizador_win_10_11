"""
Módulo de Cálculo de Métricas de Desempenho e Consistência de Quadros (Frame Pacing).
Calcula com precisão matemática FPS Médio, 1% Low, 0.1% Low, percentis de frametime e variabilidade.
"""
import math
import statistics
from typing import List, Dict, Any, Optional

def compute_percentile(sorted_data: List[float], percentile: float) -> float:
    """Calcula percentil usando interpolação linear padrão."""
    if not sorted_data:
        return 0.0
    if len(sorted_data) == 1:
        return sorted_data[0]
    
    k = (len(sorted_data) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1

def calculate_benchmark_metrics(
    frametimes_ms: List[float],
    cpu_frametimes_ms: Optional[List[float]] = None,
    gpu_frametimes_ms: Optional[List[float]] = None,
    latencies_ms: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Processa uma lista de frametimes em milissegundos e produz estatísticas completas
    conforme os padrões da indústria (PresentMon / GamersNexus / Hardware Unboxed).
    """
    valid_fts = [ft for ft in frametimes_ms if ft is not None and ft > 0.05 and ft < 1000.0]
    if not valid_fts:
        return {
            "has_data": False,
            "error": "Nenhum dado de frametime válido registrado."
        }

    total_frames = len(valid_fts)
    total_time_ms = sum(valid_fts)
    duration_seconds = total_time_ms / 1000.0

    # FPS instantâneo de cada frame
    fps_list = [1000.0 / ft for ft in valid_fts]
    sorted_fps = sorted(fps_list)
    sorted_fts = sorted(valid_fts)

    # 1. FPS Médio real (Total de frames / Duração total em segundos)
    avg_fps = round(total_frames / duration_seconds, 1) if duration_seconds > 0 else 0.0

    # 2. FPS Mínimo e Máximo
    min_fps = round(sorted_fps[0], 1)
    max_fps = round(sorted_fps[-1], 1)

    # 3. 1% Low (Média dos piores 1% de quadros - Padrão rigoroso)
    # Piores frametimes = maiores tempos de quadro (final da lista ordenada de fts)
    num_1pct = max(1, int(math.ceil(total_frames * 0.01)))
    worst_1pct_fts = sorted_fts[-num_1pct:]
    avg_worst_1pct_ft = statistics.mean(worst_1pct_fts)
    one_percent_low_fps = round(1000.0 / avg_worst_1pct_ft, 1) if avg_worst_1pct_ft > 0 else 0.0

    # 4. 0.1% Low (Média dos piores 0.1% de quadros)
    num_01pct = max(1, int(math.ceil(total_frames * 0.001)))
    worst_01pct_fts = sorted_fts[-num_01pct:]
    avg_worst_01pct_ft = statistics.mean(worst_01pct_fts)
    zero_one_percent_low_fps = round(1000.0 / avg_worst_01pct_ft, 1) if avg_worst_01pct_ft > 0 else 0.0

    # 5. Métricas de Frametime (ms)
    avg_frametime = round(statistics.mean(valid_fts), 2)
    frametime_stdev = round(statistics.stdev(valid_fts), 2) if len(valid_fts) > 1 else 0.0
    frametime_p50 = round(compute_percentile(sorted_fts, 50.0), 2)
    frametime_p95 = round(compute_percentile(sorted_fts, 95.0), 2)
    frametime_p99 = round(compute_percentile(sorted_fts, 99.0), 2)

    # Consistência / Estabilidade (0 a 100%): relação entre frametime médio e variabilidade
    # Variação menor = consistência mais próxima de 100%
    if avg_frametime > 0:
        cv = (frametime_stdev / avg_frametime) * 100.0
        consistency_pct = max(0.0, min(100.0, round(100.0 - cv, 1)))
    else:
        consistency_pct = 0.0

    result = {
        "has_data": True,
        "total_frames": total_frames,
        "duration_seconds": round(duration_seconds, 2),
        "avg_fps": avg_fps,
        "min_fps": min_fps,
        "max_fps": max_fps,
        "one_percent_low_fps": one_percent_low_fps,
        "zero_one_percent_low_fps": zero_one_percent_low_fps,
        "avg_frametime_ms": avg_frametime,
        "frametime_stdev_ms": frametime_stdev,
        "frametime_p50_ms": frametime_p50,
        "frametime_p95_ms": frametime_p95,
        "frametime_p99_ms": frametime_p99,
        "consistency_score_percent": consistency_pct,
        "frametimes_sample": valid_fts[-120:] if len(valid_fts) > 120 else valid_fts
    }

    # CPU e GPU Frametimes se disponíveis
    if cpu_frametimes_ms:
        valid_cpu = [c for c in cpu_frametimes_ms if c is not None and c > 0]
        if valid_cpu:
            result["avg_cpu_frametime_ms"] = round(statistics.mean(valid_cpu), 2)
    if gpu_frametimes_ms:
        valid_gpu = [g for g in gpu_frametimes_ms if g is not None and g > 0]
        if valid_gpu:
            result["avg_gpu_frametime_ms"] = round(statistics.mean(valid_gpu), 2)
    if latencies_ms:
        valid_lat = [l for l in latencies_ms if l is not None and l > 0]
        if valid_lat:
            result["avg_latency_ms"] = round(statistics.mean(valid_lat), 2)

    return result
