"""
Analisador de Processos e Consumo em Segundo Plano - ALTUS PC OPTIMIZER.
Identifica métricas reais de CPU, Working Set, Private Bytes, I/O e classifica
processos por risco, fabricante e impacto operacional.
"""
import os
import sys
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import psutil

from src.utils.logger import app_logger

# Processos protegidos do Windows que nunca devem ser terminados
PROTECTED_SYSTEM_PROCESSES = {
    "system", "system idle process", "smss.exe", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "winlogon.exe", "svchost.exe", "dwm.exe",
    "fontdrvhost.exe", "spoolsv.exe", "sihost.exe", "taskhostw.exe",
    "explorer.exe", "ctfmon.exe", "runtimebroker.exe"
}

# Processos e componentes de antivírus e segurança protegidos
SECURITY_PROCESSES = {
    "msmpeng.exe", "securityhealthservice.exe", "nissrv.exe", "sgrmbroker.exe",
    "smartscreen.exe", "securityhealthsystray.exe", "mpcmdrun.exe"
}

@dataclass
class BackgroundProcessInfo:
    pid: int
    name: str
    exe_path: str
    publisher: str
    description: str
    cpu_percent: float
    memory_rss_mb: float
    memory_vms_mb: float
    disk_read_kb: float
    disk_write_kb: float
    uptime_seconds: float
    category: str       # 'ESSENTIAL', 'SECURITY', 'DRIVER', 'MICROSOFT', 'WEBVIEW2', 'THIRD_PARTY'
    impact_level: str   # 'BAIXO', 'MODERADO', 'ALTO'
    is_safe_to_close: bool
    risk_reason: str

def _get_publisher_from_path(path: str) -> str:
    """Extrai fabricante e metadados básicos do executável no Windows."""
    if not path or not os.path.exists(path):
        return "Microsoft Corporation" if "windows" in (path or "").lower() else "Desconhecido"
    
    path_lower = path.lower()
    if r"windows\system32" in path_lower or r"windows\syswow64" in path_lower:
        return "Microsoft Corporation"
    elif "nvidia" in path_lower:
        return "NVIDIA Corporation"
    elif "amd" in path_lower or "radeon" in path_lower:
        return "Advanced Micro Devices"
    elif "intel" in path_lower:
        return "Intel Corporation"
    elif "realtek" in path_lower:
        return "Realtek Semiconductor"
    elif "discord" in path_lower:
        return "Discord Inc."
    elif "steam" in path_lower or "valve" in path_lower:
        return "Valve Corporation"
    elif "spotify" in path_lower:
        return "Spotify AB"
    elif "google" in path_lower or "chrome" in path_lower:
        return "Google LLC"
    return "Aplicativo de Terceiros"

def _classify_process(name: str, path: str, publisher: str) -> tuple[str, bool, str]:
    """
    Classifica processo por categoria e risco de encerramento.
    Retorna (categoria, is_safe_to_close, risk_reason).
    """
    n_lower = name.lower()
    p_lower = (path or "").lower()
    
    # 1. Componente Essencial do Windows
    if n_lower in PROTECTED_SYSTEM_PROCESSES or "system32" in p_lower and n_lower.startswith("svc"):
        return "ESSENTIAL", False, "Processo essencial para estabilidade do kernel e sessão do Windows."
    
    # 2. Antivírus e Segurança
    if n_lower in SECURITY_PROCESSES or "defender" in p_lower or "antivirus" in p_lower:
        return "SECURITY", False, "Mecanismo de proteção e segurança ativa do sistema operacional."
    
    # 3. Drivers de Hardware
    if any(k in n_lower or k in p_lower for k in ["nvx", "nvcontainer", "amdsrv", "igfx", "rtk", "realtek"]):
        return "DRIVER", False, "Componente de driver de vídeo, áudio ou chipset de hardware."
    
    # 4. Host WebView2
    if "msedgewebview2" in n_lower:
        return "WEBVIEW2", False, "Runtime de WebView2 compartilhado com outros softwares em execução."
    
    # 5. Componentes e Aplicativos Microsoft
    if "microsoft" in publisher.lower() or "windows" in p_lower or n_lower in ["msedge.exe", "onedrive.exe"]:
        return "MICROSOFT", True, "Aplicação ou serviço opcional da Microsoft em segundo plano."
    
    # 6. Terceiros
    return "THIRD_PARTY", True, "Software de terceiros executando em segundo plano."

def analyze_background_processes(sample_duration_seconds: float = 0.5) -> List[BackgroundProcessInfo]:
    """
    Realiza amostragem de processos ativos, calculando métricas de CPU e RAM
    e classificando candidatos a otimização de segundo plano.
    """
    initial_snapshots = {}
    now = time.time()
    
    # Primeira coleta de CPU
    for p in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            p.cpu_percent(interval=None)
            initial_snapshots[p.pid] = p
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if sample_duration_seconds > 0:
        time.sleep(sample_duration_seconds)

    results: List[BackgroundProcessInfo] = []

    for pid, p in initial_snapshots.items():
        try:
            if not p.is_running():
                continue

            cpu = p.cpu_percent(interval=None)
            mem_info = p.memory_info()
            rss_mb = round(mem_info.rss / (1024 ** 2), 1)
            vms_mb = round(mem_info.vms / (1024 ** 2), 1)

            # E/S de Disco
            disk_r_kb = 0.0
            disk_w_kb = 0.0
            try:
                io = p.io_counters()
                disk_r_kb = round(io.read_bytes / 1024, 1)
                disk_w_kb = round(io.write_bytes / 1024, 1)
            except Exception:
                pass

            # Tempo de execução
            uptime = 0.0
            try:
                create_t = p.create_time()
                uptime = max(0.0, now - create_t)
            except Exception:
                pass

            name = p.name()
            exe_path = ""
            try:
                exe_path = p.exe()
            except Exception:
                pass

            publisher = _get_publisher_from_path(exe_path)
            category, safe_to_close, reason = _classify_process(name, exe_path, publisher)

            # Nível de impacto
            if cpu > 5.0 or rss_mb > 350:
                impact = "ALTO"
            elif cpu > 1.0 or rss_mb > 120:
                impact = "MODERADO"
            else:
                impact = "BAIXO"

            info = BackgroundProcessInfo(
                pid=pid,
                name=name,
                exe_path=exe_path,
                publisher=publisher,
                description=f"{publisher} ({name})",
                cpu_percent=round(cpu, 1),
                memory_rss_mb=rss_mb,
                memory_vms_mb=vms_mb,
                disk_read_kb=disk_r_kb,
                disk_write_kb=disk_w_kb,
                uptime_seconds=round(uptime, 0),
                category=category,
                impact_level=impact,
                is_safe_to_close=safe_to_close,
                risk_reason=reason
            )
            results.append(info)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Ordena por consumo de memória decrescente
    results.sort(key=lambda x: (x.cpu_percent, x.memory_rss_mb), reverse=True)
    return results

def get_top_background_consumers(limit: int = 15) -> List[Dict[str, Any]]:
    """Retorna os principais processos em segundo plano classificados para exibição."""
    procs = analyze_background_processes(sample_duration_seconds=0.2)
    # Filtra apenas processos não essenciais ou com impacto perceptível
    return [asdict(p) for p in procs[:limit]]
