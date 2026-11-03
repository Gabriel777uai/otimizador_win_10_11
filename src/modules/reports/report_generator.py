"""
Gerador de Relatórios Técnicos e Executivos de Manutenção (HTML e TXT).
Cria documentos completos com dados de hardware, espaço liberado e auditoria.
"""
import time
from pathlib import Path
from typing import Dict, Any, List
from src.utils.logger import get_app_dir
from src.core.system_detection import get_full_system_snapshot
from src.modules.reports.history_manager import get_operation_history

def generate_html_report(save_path: Path) -> bool:
    """Gera um relatório completo em HTML estilizado com identidade visual do ALTUS."""
    snapshot = get_full_system_snapshot()
    history = get_operation_history()[:20]

    os_info = snapshot.get("os", {})
    cpu_info = snapshot.get("cpu", {})
    mem_info = snapshot.get("memory", {})
    gpus = snapshot.get("gpu", [])
    disks = snapshot.get("disks", [])

    gpu_name = gpus[0]["name"] if gpus else "Não detectada"

    disks_html = ""
    for d in disks:
        disks_html += f"""
        <tr>
            <td><strong>{d.get('mountpoint')}</strong></td>
            <td>{d.get('device')}</td>
            <td>{d.get('total_gb')} GB</td>
            <td>{d.get('free_gb')} GB ({100 - d.get('percent_used', 0):.1f}% livre)</td>
            <td>{d.get('fstype')}</td>
        </tr>
        """

    history_html = ""
    for h in history:
        status_color = "#00e676" if h.get("status") == "Concluído" or h.get("status") == "OK" else "#ff5252"
        history_html += f"""
        <tr>
            <td>{h.get('timestamp')}</td>
            <td><strong>{h.get('operation')}</strong></td>
            <td style="color: {status_color}; font-weight: bold;">{h.get('status')}</td>
            <td>{h.get('freed_mb', 0)} MB</td>
            <td>{h.get('details', '')}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>ALTUS PC OPTIMIZER - Relatório de Manutenção</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0b111e;
            color: #d1d9e6;
            margin: 0;
            padding: 30px;
        }}
        .header {{
            background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%);
            border: 1px solid #1e3a5f;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 25px;
        }}
        h1 {{
            color: #00d2ff;
            margin: 0 0 10px 0;
            font-size: 24px;
        }}
        .subtitle {{
            color: #8da4c4;
            font-size: 14px;
        }}
        .card {{
            background-color: #111a2e;
            border: 1px solid #1c2a47;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #00d2ff;
            font-size: 18px;
            border-bottom: 1px solid #1c2a47;
            padding-bottom: 8px;
            margin-top: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            text-align: left;
            padding: 10px 14px;
            border-bottom: 1px solid #162238;
            font-size: 13px;
        }}
        th {{
            background-color: #162238;
            color: #8da4c4;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
        }}
        .metric-box {{
            background-color: #162238;
            padding: 14px;
            border-radius: 6px;
            border-left: 3px solid #00d2ff;
        }}
        .metric-label {{
            font-size: 12px;
            color: #8da4c4;
            text-transform: uppercase;
        }}
        .metric-value {{
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            margin-top: 4px;
        }}
        .footer {{
            text-align: center;
            font-size: 12px;
            color: #5d7290;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ALTUS PC OPTIMIZER — RELATÓRIO DO SISTEMA</h1>
        <div class="subtitle">Gerado em: {time.strftime('%d/%m/%Y às %H:%M:%S')} | Sistema: {os_info.get('caption')}</div>
    </div>

    <div class="card">
        <h2>Visão Geral de Hardware e Recursos</h2>
        <div class="grid">
            <div class="metric-box">
                <div class="metric-label">Processador (CPU)</div>
                <div class="metric-value">{cpu_info.get('model')}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Núcleos / Threads</div>
                <div class="metric-value">{cpu_info.get('cores_physical')} C / {cpu_info.get('threads_logical')} T</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Memória RAM</div>
                <div class="metric-value">{mem_info.get('total_gb')} GB ({mem_info.get('used_gb')} GB usado)</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Placa de Vídeo (GPU)</div>
                <div class="metric-value">{gpu_name}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Tempo de Atividade (Uptime)</div>
                <div class="metric-value">{os_info.get('uptime')}</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>Unidades de Armazenamento</h2>
        <table>
            <thead>
                <tr>
                    <th>Unidade</th>
                    <th>Identificador</th>
                    <th>Tamanho Total</th>
                    <th>Espaço Disponível</th>
                    <th>Sistema de Arquivos</th>
                </tr>
            </thead>
            <tbody>
                {disks_html}
            </tbody>
        </table>
    </div>

    <div class="card">
        <h2>Histórico Recente de Otimizações e Manutenção</h2>
        <table>
            <thead>
                <tr>
                    <th>Data / Hora</th>
                    <th>Operação</th>
                    <th>Status</th>
                    <th>Espaço Liberado</th>
                    <th>Observações</th>
                </tr>
            </thead>
            <tbody>
                {history_html if history_html else '<tr><td colspan="5">Nenhuma operação registrada ainda.</td></tr>'}
            </tbody>
        </table>
    </div>

    <div class="footer">
        ALTUS PC OPTIMIZER • Desenvolvido com Padrões de Segurança do Windows • Todos os direitos reservados.
    </div>
</body>
</html>
"""
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return True
    except Exception:
        return False

def generate_txt_report(save_path: Path) -> bool:
    """Gera um relatório técnico em formato TXT puro."""
    snapshot = get_full_system_snapshot()
    history = get_operation_history()[:15]

    os_info = snapshot.get("os", {})
    cpu_info = snapshot.get("cpu", {})
    mem_info = snapshot.get("memory", {})

    lines = [
        "=" * 70,
        "ALTUS PC OPTIMIZER - RELATÓRIO TÉCNICO DE SISTEMA E MANUTENÇÃO",
        "=" * 70,
        f"Data da Emissão : {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Sistema Operac. : {os_info.get('caption')} (Build {os_info.get('build')})",
        f"Uptime Atual    : {os_info.get('uptime')}",
        "-" * 70,
        "1. RESUMO DE HARDWARE",
        f"  Processador   : {cpu_info.get('model')}",
        f"  Núcleos/Thr.  : {cpu_info.get('cores_physical')} Núcleos / {cpu_info.get('threads_logical')} Threads",
        f"  Memória RAM   : {mem_info.get('total_gb')} GB Total ({mem_info.get('available_gb')} GB livres)",
        "-" * 70,
        "2. UNIDADES DE DISCO",
    ]

    for d in snapshot.get("disks", []):
        lines.append(f"  Unidade {d.get('mountpoint')} -> {d.get('free_gb')} GB livres de {d.get('total_gb')} GB ({d.get('fstype')})")

    lines.extend([
        "-" * 70,
        "3. HISTÓRICO DE OPERAÇÕES RECENTES"
    ])

    for h in history:
        lines.append(f"  [{h.get('timestamp')}] {h.get('operation')} - Status: {h.get('status')} - Liberado: {h.get('freed_mb')} MB")

    lines.extend([
        "=" * 70,
        "FIM DO RELATÓRIO - ALTUS PC OPTIMIZER",
        "=" * 70
    ])

    try:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return True
    except Exception:
        return False
