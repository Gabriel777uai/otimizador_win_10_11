"""
Módulo de Monitoramento de Desempenho e Diagnóstico de Gargalos.
Analisa uso contínuo de CPU, Memória, Disco e processos em segundo plano.
Contextualiza os diagnósticos tecnicamente, sem julgamentos errôneos.
"""
from typing import Dict, Any, List
import psutil
from src.utils.logger import app_logger

def get_top_resource_consumers(limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """Retorna os processos que mais consomem CPU e Memória RAM."""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'memory_percent']):
        try:
            info = p.info
            mem_mb = round(info['memory_info'].rss / (1024 ** 2), 1) if info.get('memory_info') else 0
            procs.append({
                "pid": info['pid'],
                "name": info['name'] or "Processo",
                "cpu_percent": info['cpu_percent'] or 0.0,
                "memory_mb": mem_mb,
                "memory_percent": round(info['memory_percent'] or 0.0, 1)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    top_cpu = sorted(procs, key=lambda x: x['cpu_percent'], reverse=True)[:limit]
    top_memory = sorted(procs, key=lambda x: x['memory_mb'], reverse=True)[:limit]

    return {
        "top_cpu": top_cpu,
        "top_memory": top_memory
    }

def diagnose_bottlenecks() -> List[Dict[str, Any]]:
    """
    Identifica gargalos técnicos reais do sistema.
    Exemplo: Pressão de memória com paginação, CPU saturada, disco com fila alta.
    """
    diagnostics = []

    # 1. Análise de Memória
    vm = psutil.virtual_memory()
    if vm.percent > 90:
        diagnostics.append({
            "severity": "ALERTA",
            "component": "Memória RAM",
            "title": "Pressão severa de memória física",
            "description": f"A utilização da RAM está em {vm.percent}%. O sistema pode recorrer à paginação em disco, causando engasgos (stuttering)."
        })
    elif vm.percent > 80:
        diagnostics.append({
            "severity": "ATENÇÃO",
            "component": "Memória RAM",
            "title": "Utilização elevada de memória",
            "description": f"RAM com {vm.percent}% de ocupação. Recomendado fechar aplicativos secundários ao iniciar jogos pesados."
        })
    else:
        diagnostics.append({
            "severity": "NORMAL",
            "component": "Memória RAM",
            "title": "Memória disponível adequada",
            "description": f"RAM em {vm.percent}% de uso com {round(vm.available / (1024**3), 1)} GB livres."
        })

    # 2. Análise de CPU
    cpu_p = psutil.cpu_percent(interval=0.2)
    if cpu_p > 90:
        diagnostics.append({
            "severity": "ALERTA",
            "component": "Processador (CPU)",
            "title": "CPU próxima da saturação",
            "description": f"Uso instantâneo da CPU em {cpu_p}%. Há processos competindo ativamente por ciclos de computação."
        })
    else:
        diagnostics.append({
            "severity": "NORMAL",
            "component": "Processador (CPU)",
            "title": "Processador operando normalmente",
            "description": f"Carga atual de {cpu_p}%, com ciclos disponíveis para aplicações e jogos."
        })

    # 3. Análise de Disco
    try:
        c_usage = psutil.disk_usage("C:\\")
        if c_usage.percent > 90:
            diagnostics.append({
                "severity": "ALERTA",
                "component": "Armazenamento (C:)",
                "title": "Espaço crítico na unidade do sistema",
                "description": f"Unidade C: possui apenas {round(c_usage.free / (1024**3), 1)} GB livres ({c_usage.percent}% usado). SSDs necessitam de 10-15% de espaço para manter eficiência de TRIM e escrita."
            })
    except Exception:
        pass

    return diagnostics
