"""
Módulo de Diagnóstico e Histórico do Windows Update.
Inspeciona status dos serviços essenciais e histórico de hotfixes instalados.
"""
from typing import Dict, Any, List
import psutil
from src.utils.logger import app_logger
from src.utils.command_runner import run_command

def check_update_services() -> List[Dict[str, Any]]:
    """Inspeciona o estado dos serviços essenciais do ecossistema de atualização."""
    services = ["wuauserv", "bits", "cryptsvc", "dosvc"]
    status_list = []

    for s_name in services:
        try:
            srv = psutil.win_service_get(s_name)
            status_list.append({
                "service": s_name,
                "display_name": srv.display_name(),
                "status": srv.status(),
                "start_type": srv.start_type()
            })
        except Exception:
            status_list.append({
                "service": s_name,
                "display_name": s_name,
                "status": "Não encontrado",
                "start_type": "Desconhecido"
            })
    return status_list

def get_installed_hotfixes(limit: int = 10) -> List[Dict[str, Any]]:
    """Consulta os últimos pacotes de atualização (KB) instalados."""
    cmd = [
        "powershell", "-NoProfile", "-Command",
        f"Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First {limit} HotFixID, Description, InstalledOn | ConvertTo-Json -Compress"
    ]
    rc, out, _ = run_command(cmd, timeout=8)
    hotfixes = []
    if rc == 0 and out.strip():
        import json
        try:
            data = json.loads(out.strip())
            if isinstance(data, dict):
                data = [data]
            for item in data:
                hotfixes.append({
                    "id": item.get("HotFixID", "KB Desconhecido"),
                    "description": item.get("Description", "Atualização"),
                    "installed_on": str(item.get("InstalledOn", "N/A"))
                })
        except Exception:
            pass
    return hotfixes
