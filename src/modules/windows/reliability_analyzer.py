"""
Módulo WINDOWS RELIABILITY ANALYZER - Diagnóstico de Estabilidade do Windows.
Varre o Visualizador de Eventos (Event Log) oficial da Microsoft buscando falhas de aplicativos,
erros de drivers, reinicializações inesperadas (Kernel-Power 41/6008), falhas de disco e serviços.
Gera linha do tempo categorizada com impactos e recomendações técnicas fundamentadas.
"""
import re
import json
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.utils.logger import app_logger, get_app_dir

def parse_wmi_timestamp(raw_date: Optional[str]) -> str:
    """Converte /Date(1793532740535)/ para data/hora formatada."""
    if not raw_date:
        return "N/A"
    try:
        match = re.search(r"\d+", str(raw_date))
        if match:
            ts_sec = int(match.group(0)) / 1000.0
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts_sec))
    except Exception:
        pass
    return str(raw_date)[:19]

def classify_event(provider: str, event_id: int, message: str) -> Dict[str, str]:
    """Classifica o evento com base em padrões de diagnóstico do Windows."""
    p_lower = provider.lower()
    m_lower = message.lower()

    if "application error" in p_lower or "application hang" in p_lower or event_id in (1000, 1002):
        return {
            "category": "Falha de Aplicativo",
            "impact": "Travamento ou encerramento inesperado de um aplicativo do usuário.",
            "recommendation": "Verifique atualizações do aplicativo específico ou consulte falhas de memória."
        }

    if "kernel-power" in p_lower or event_id in (41, 1074, 6008):
        return {
            "category": "Reinicialização / Desligamento",
            "impact": "O computador foi reinicializado sem um desligamento prévio ordenado (queda de energia ou BSOD).",
            "recommendation": "Verifique a estabilidade da fonte de alimentação, temperaturas de CPU/GPU e logs de despejo de memória (minidump)."
        }

    if any(k in p_lower for k in ("display", "nvlddmkm", "amdkmdag", "igfx", "kernel-pnp")):
        return {
            "category": "Driver de Dispositivo / Gráficos",
            "impact": "O driver de hardware ou de vídeo parou de responder ou falhou durante a operação.",
            "recommendation": "Atualize o driver do fabricante ou execute uma instalação limpa (DDU)."
        }

    if any(k in p_lower for k in ("disk", "ntfs", "volsnap", "storahci", "iaStor")) or event_id in (7, 11, 55, 129):
        return {
            "category": "Armazenamento e Disco",
            "impact": "Aviso ou lentidão de resposta na controladora de armazenamento ou no sistema de arquivos.",
            "recommendation": "Execute o diagnóstico CHKDSK /scan pelo ALTUS e verifique os dados SMART da unidade."
        }

    if "service control manager" in p_lower or event_id in (7000, 7009, 7034):
        return {
            "category": "Serviços do Windows",
            "impact": "Um serviço do sistema ou de terceiros finalizou inesperadamente ou demorou a responder.",
            "recommendation": "Verifique se o serviço é essencial e avalie suas permissões de logon e dependências."
        }

    return {
        "category": "Sistema Operacional",
        "impact": "Evento de erro registrado pelo subsistema do Windows.",
        "recommendation": "Monitore a recorrência do evento. Erros isolados não indicam falha permanente."
    }

def get_system_reliability_events(days_back: int = 7, max_events: int = 40) -> List[Dict[str, Any]]:
    """
    Consulta os logs oficiais do Windows (System e Application) filtrando por Níveis 1 (Crítico) e 2 (Erro).
    Retorna a linha do tempo estruturada de incidentes de estabilidade.
    """
    events = []
    ps_cmd = (
        f"Get-WinEvent -FilterHashtable @{{LogName=@('System', 'Application'); Level=@(1,2); StartTime=(Get-Date).AddDays(-{days_back})}} "
        f"-MaxEvents {max_events} -ErrorAction SilentlyContinue | "
        "Select-Object TimeCreated, LogName, ProviderName, Id, LevelDisplayName, Message | ConvertTo-Json -Compress"
    )

    try:
        app_logger.info(f"Consultando eventos de estabilidade do Windows ({days_back} dias)...")
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=15
        )

        if res.returncode == 0 and res.stdout.strip():
            raw_data = json.loads(res.stdout.strip())
            if isinstance(raw_data, dict):
                raw_data = [raw_data]

            for item in raw_data:
                provider = str(item.get("ProviderName") or "Sistema")
                ev_id = int(item.get("Id") or 0)
                msg = str(item.get("Message") or "").strip()
                lvl = str(item.get("LevelDisplayName") or "Erro")
                time_str = parse_wmi_timestamp(item.get("TimeCreated"))

                classification = classify_event(provider, ev_id, msg)

                # Resumo curto legível
                summary = msg.splitlines()[0] if msg else f"Evento {ev_id} registrado por {provider}"
                if len(summary) > 160:
                    summary = summary[:157] + "..."

                events.append({
                    "timestamp": time_str,
                    "provider": provider,
                    "event_id": ev_id,
                    "severity": lvl,
                    "category": classification["category"],
                    "summary": summary,
                    "full_message": msg,
                    "impact": classification["impact"],
                    "recommendation": classification["recommendation"]
                })

    except Exception as e:
        app_logger.warning(f"Erro ao consultar Event Log do Windows: {e}")

    return events
