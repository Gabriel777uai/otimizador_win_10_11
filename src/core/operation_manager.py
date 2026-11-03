"""
Gerenciador de Operações de Manutenção do ALTUS PC OPTIMIZER.
Coordena a análise preliminar e a execução segura das rotinas.
"""
import time
from typing import Dict, Any, List, Callable, Optional
from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager, RiskLevel

class OperationManager:
    """Orquestrador de tarefas e rotinas de manutenção."""

    def __init__(self):
        pass

    def run_preliminary_analysis(
        self,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executa varredura e diagnóstico inicial SEM modificar absolutamente nada.
        Retorna mapa de itens que podem ser otimizados.
        """
        from src.modules.cleaning.temp_cleaner import analyze_temp_files
        from src.modules.cleaning.thumbnail_cleaner import analyze_thumbnail_cache
        from src.modules.cleaning.dns_cache_cleaner import check_dns_cache_status
        from src.modules.gaming.startup_optimizer import get_startup_entries
        from src.core.system_detection import get_memory_info, get_cpu_info

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "items": {},
            "total_reclaimable_bytes": 0,
            "system_status": {}
        }

        if progress_callback:
            progress_callback(10, "Analisando arquivos temporários do usuário e sistema...")
        temp_data = analyze_temp_files(min_age_days=7)
        report["items"]["temp_files"] = temp_data
        report["total_reclaimable_bytes"] += temp_data.get("reclaimable_bytes", 0)

        if progress_callback:
            progress_callback(40, "Verificando cache de miniaturas do Windows Explorer...")
        thumb_data = analyze_thumbnail_cache()
        report["items"]["thumbnails"] = thumb_data
        report["total_reclaimable_bytes"] += thumb_data.get("reclaimable_bytes", 0)

        if progress_callback:
            progress_callback(60, "Verificando resolvedor e cache DNS...")
        dns_data = check_dns_cache_status()
        report["items"]["dns_cache"] = dns_data

        if progress_callback:
            progress_callback(80, "Verificando programas de inicialização...")
        startup_entries = get_startup_entries()
        report["items"]["startup_programs"] = {
            "count": len(startup_entries),
            "entries": startup_entries[:5]  # Amostra
        }

        if progress_callback:
            progress_callback(95, "Coletando telemetria de CPU e Memória...")
        mem = get_memory_info()
        cpu = get_cpu_info()
        report["system_status"] = {
            "cpu_percent": cpu.get("current_percent", 0),
            "ram_used_percent": mem.get("percent_used", 0),
            "ram_free_gb": mem.get("available_gb", 0)
        }

        if progress_callback:
            progress_callback(100, "Análise preliminar concluída.")

        return report

operation_manager = OperationManager()
