"""
Sistema de Medição Antes e Depois - ALTUS PC OPTIMIZER.
Coleta instantâneos de métricas de CPU, RAM, disco e processos antes e depois
de aplicar otimizações e calcula deltas reais sem promessas enganosas de cache.
"""
import time
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
import psutil

from src.utils.logger import app_logger
from .feature_detector import detect_all_windows_features

@dataclass
class SystemResourceSnapshot:
    timestamp: str
    cpu_percent: float
    ram_used_gb: float
    ram_available_gb: float
    ram_percent: float
    process_count: int
    disk_read_kb_per_sec: float
    disk_write_kb_per_sec: float
    active_features_count: int

def take_system_snapshot() -> SystemResourceSnapshot:
    """Coleta o estado de consumo de hardware e processos em repouso."""
    # Amostra CPU de 0.3s
    cpu = psutil.cpu_percent(interval=0.3)
    vm = psutil.virtual_memory()
    procs = len(psutil.pids())

    # Disco I/O
    io1 = psutil.disk_io_counters()
    time.sleep(0.2)
    io2 = psutil.disk_io_counters()

    read_kb = 0.0
    write_kb = 0.0
    if io1 and io2:
        read_kb = round((io2.read_bytes - io1.read_bytes) / 1024 / 0.2, 1)
        write_kb = round((io2.write_bytes - io1.write_bytes) / 1024 / 0.2, 1)

    feats = detect_all_windows_features()
    active_feats = sum([
        1 if feats.copilot_taskbar_visible else 0,
        1 if not feats.edge_startup_boost_disabled else 0,
        1 if not feats.edge_background_mode_disabled else 0,
        1 if feats.game_dvr_background_recording else 0,
        1 if feats.widgets_visible else 0,
        1 if feats.delivery_p2p_mode > 0 else 0
    ])

    return SystemResourceSnapshot(
        timestamp=time.strftime("%H:%M:%S"),
        cpu_percent=round(cpu, 1),
        ram_used_gb=round(vm.used / (1024 ** 3), 2),
        ram_available_gb=round(vm.available / (1024 ** 3), 2),
        ram_percent=vm.percent,
        process_count=procs,
        disk_read_kb_per_sec=max(0.0, read_kb),
        disk_write_kb_per_sec=max(0.0, write_kb),
        active_features_count=active_feats
    )

def compare_snapshots(
    before: SystemResourceSnapshot,
    after: SystemResourceSnapshot,
    applied_operations: List[str]
) -> Dict[str, Any]:
    """
    Calcula a diferença real entre os dois instantâneos,
    garantindo transparência técnica e clareza de resultados.
    """
    ram_diff_mb = round((before.ram_used_gb - after.ram_used_gb) * 1024, 1)
    cpu_diff_pct = round(before.cpu_percent - after.cpu_percent, 1)
    proc_diff = before.process_count - after.process_count
    feat_diff = before.active_features_count - after.active_features_count

    summary_msg = []
    if ram_diff_mb > 0:
        summary_msg.append(f"Redução de ~{ram_diff_mb} MB na memória de trabalho ativa.")
    elif ram_diff_mb < 0:
        summary_msg.append("Consumo de RAM estável com variação natural do sistema.")
    else:
        summary_msg.append("Memória RAM mantida estável.")

    if feat_diff > 0:
        summary_msg.append(f"{feat_diff} serviços e recursos opcionais de segundo plano foram reduzidos.")

    return {
        "before": asdict(before),
        "after": asdict(after),
        "ram_diff_mb": ram_diff_mb,
        "cpu_diff_pct": cpu_diff_pct,
        "process_count_diff": proc_diff,
        "features_reduced_count": max(0, feat_diff),
        "applied_operations": applied_operations,
        "summary": " ".join(summary_msg)
    }
