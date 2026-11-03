"""
Módulo de Integração com o Agendador de Tarefas do Windows (Task Scheduler).
Cria, edita, consulta e remove tarefas agendadas oficiais no Windows (schtasks.exe)
para a manutenção periódica e segura de Nível 1.
"""
import sys
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from src.utils.logger import app_logger
from src.utils.command_runner import run_command

TASK_NAME = "AltusMaintenanceTask"

def get_current_executable_command() -> str:
    """Determina o caminho do executável ou comando python para a tarefa agendada."""
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}" --auto-maintenance'
    else:
        python_exe = sys.executable
        main_py = Path(__file__).resolve().parent.parent.parent.parent / "main.py"
        return f'"{python_exe}" "{main_py}" --auto-maintenance'

def get_scheduled_task_status() -> Dict[str, Any]:
    """Consulta o status da tarefa agendada no Windows."""
    cmd = ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST", "/v"]
    rc, out, _ = run_command(cmd, timeout=8)

    if rc != 0:
        return {
            "exists": False,
            "status": "Não agendado",
            "next_run": "Nenhum",
            "last_run": "Nenhum"
        }

    status = "Agendado"
    next_run = "Desconhecido"
    last_run = "Nunca"

    for line in out.splitlines():
        line_clean = line.strip()
        if "Hora da Próxima Execução:" in line or "Next Run Time:" in line:
            next_run = line.split(":", 1)[1].strip()
        elif "Hora da Última Execução:" in line or "Last Run Time:" in line:
            last_run = line.split(":", 1)[1].strip()
        elif "Status:" in line:
            status = line.split(":", 1)[1].strip()

    return {
        "exists": True,
        "status": status,
        "next_run": next_run,
        "last_run": last_run
    }

def create_or_update_scheduled_task(day_of_week: str = "SUN", time_str: str = "12:00") -> Dict[str, Any]:
    """
    Cria ou atualiza a tarefa semanal no Agendador de Tarefas do Windows.
    Executa exclusivamente em Nível 1.
    """
    exec_cmd = get_current_executable_command()
    app_logger.info(f"Configurando tarefa no Agendador do Windows: {TASK_NAME} ({day_of_week} às {time_str})...")

    # schtasks /create /tn AltusMaintenanceTask /tr "..." /sc WEEKLY /d SUN /st 12:00 /f /rl HIGHEST
    cmd = [
        "schtasks", "/create",
        "/tn", TASK_NAME,
        "/tr", exec_cmd,
        "/sc", "WEEKLY",
        "/d", day_of_week,
        "/st", time_str,
        "/f"
    ]

    rc, out, err = run_command(cmd, timeout=12)
    if rc == 0:
        app_logger.info(f"Tarefa {TASK_NAME} agendada com sucesso no Windows.")
        return {
            "success": True,
            "message": f"Manutenção agendada configurada no Windows: Semanalmente ({day_of_week}) às {time_str}."
        }
    return {
        "success": False,
        "message": f"Não foi possível criar a tarefa agendada: {err or out}"
    }

def delete_scheduled_task() -> Dict[str, Any]:
    """Remove a tarefa agendada do Windows."""
    app_logger.info(f"Removendo tarefa agendada {TASK_NAME}...")
    cmd = ["schtasks", "/delete", "/tn", TASK_NAME, "/f"]
    rc, out, err = run_command(cmd, timeout=8)
    if rc == 0:
        return {"success": True, "message": "Tarefa agendada removida com sucesso do Windows."}
    return {"success": False, "message": f"Falha ao remover tarefa: {err or out}"}
