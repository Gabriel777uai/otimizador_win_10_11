"""
Módulo de Exportação de Relatórios de Desempenho em CSV e HTML.
Gera relatórios técnicos elegantes e compartilháveis para benchmarks e comparativos.
"""
import csv
from pathlib import Path
from typing import Dict, Any
from src.utils.logger import get_app_dir

def export_benchmark_to_csv(comparison: Dict[str, Any], filepath: Path) -> bool:
    """Exporta a comparação de benchmarks para arquivo CSV estruturado."""
    try:
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ALTUS PC OPTIMIZER - Relatório de Desempenho e Comparação"])
            writer.writerow(["Jogo", comparison.get("game")])
            writer.writerow(["Resolução", comparison.get("resolution")])
            writer.writerow(["Configurações Gráficas", comparison.get("settings")])
            writer.writerow([])
            writer.writerow(["Métrica", "Baseline (Original)", "Otimizado (Altus)", "Variação Absoluta", "Variação Percentual (%)", "Evolução"])

            metrics = [
                ("FPS Médio", "avg_fps"),
                ("1% Low FPS", "one_percent_low_fps"),
                ("0.1% Low FPS", "zero_one_percent_low_fps"),
                ("Frametime Médio (ms)", "avg_frametime_ms"),
                ("Índice de Consistência (%)", "consistency_score")
            ]

            for label, key in metrics:
                data = comparison.get(key, {})
                evol = "Melhoria" if data.get("improved") else ("Inalterado" if data.get("diff") == 0 else "Regressão")
                writer.writerow([
                    label,
                    data.get("baseline"),
                    data.get("optimized"),
                    data.get("diff"),
                    f"{data.get('pct_change')}%",
                    evol
                ])
        return True
    except Exception:
        return False

def export_benchmark_to_html(comparison: Dict[str, Any], filepath: Path) -> bool:
    """Gera um relatório HTML visual moderno, responsivo e tecnológico."""
    try:
        def row_html(label, data, unit=""):
            improved = data.get("improved")
            pct = data.get("pct_change", 0)
            diff = data.get("diff", 0)
            sign = "+" if diff > 0 else ""
            color = "#10b981" if improved else ("#ef4444" if pct < -1 else "#94a3b8")
            badge = f"<span style='color: {color}; font-weight: bold;'>{sign}{pct}% ({sign}{diff} {unit})</span>"
            return f"""
            <tr>
                <td style="padding: 12px 16px; border-bottom: 1px solid #162238; color: #cbd5e1;">{label}</td>
                <td style="padding: 12px 16px; border-bottom: 1px solid #162238; color: #ffffff; font-weight: bold;">{data.get('baseline')} {unit}</td>
                <td style="padding: 12px 16px; border-bottom: 1px solid #162238; color: #00d2ff; font-weight: bold;">{data.get('optimized')} {unit}</td>
                <td style="padding: 12px 16px; border-bottom: 1px solid #162238;">{badge}</td>
            </tr>
            """

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>ALTUS PC OPTIMIZER — Relatório de Desempenho</title>
    <style>
        body {{
            background-color: #050b14;
            color: #e2e8f0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 30px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background-color: #0b1324;
            border: 1px solid #1e3a5f;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }}
        h1 {{
            color: #00d2ff;
            margin-top: 0;
            font-size: 24px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 24px;
            background-color: #070d19;
            padding: 16px;
            border-radius: 8px;
            border: 1px solid #162238;
        }}
        .meta-item span {{
            display: block;
            font-size: 11px;
            color: #64748b;
            text-transform: uppercase;
            font-weight: bold;
        }}
        .meta-item strong {{
            color: #ffffff;
            font-size: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th {{
            background-color: #0e1a30;
            color: #00d2ff;
            text-align: left;
            padding: 12px 16px;
            font-size: 12px;
            text-transform: uppercase;
            border-bottom: 2px solid #00d2ff;
        }}
        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #475569;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>ALTUS PC OPTIMIZER — Relatório de Benchmark</h1>
        <div class="meta-grid">
            <div class="meta-item">
                <span>Jogo / Aplicação</span>
                <strong>{comparison.get('game')}</strong>
            </div>
            <div class="meta-item">
                <span>Resolução do Teste</span>
                <strong>{comparison.get('resolution')}</strong>
            </div>
            <div class="meta-item">
                <span>Perfil de Gráficos</span>
                <strong>{comparison.get('settings')}</strong>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Métrica de Telemetria</th>
                    <th>Linha de Base</th>
                    <th>Com Otimização ALTUS</th>
                    <th>Impacto Observado</th>
                </tr>
            </thead>
            <tbody>
                {row_html("FPS Médio", comparison.get("avg_fps", {}), "FPS")}
                {row_html("1% Low (Piores 1% de quadros)", comparison.get("one_percent_low_fps", {}), "FPS")}
                {row_html("0.1% Low (Engasgos severos)", comparison.get("zero_one_percent_low_fps", {}), "FPS")}
                {row_html("Frametime Médio", comparison.get("avg_frametime_ms", {}), "ms")}
                {row_html("Consistência de Quadros", comparison.get("consistency_score", {}), "%")}
            </tbody>
        </table>

        <div class="footer">
            Gerado automaticamente pelo ALTUS PC OPTIMIZER — Telemetria de Desempenho e Engenharia de Sistemas Windows.
        </div>
    </div>
</body>
</html>
"""
        filepath.write_text(html, encoding="utf-8")
        return True
    except Exception:
        return False
