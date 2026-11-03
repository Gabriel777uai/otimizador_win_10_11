"""
Módulo GAME PERFORMANCE MODE & SMART GAME SESSION.
Acompanha ativamente sessões de jogos com controle de ciclo de vida:
- Detecção e proteção contra reutilização de PID (monitorando create_time).
- Preservação e restauração do plano de energia original e prioridades de processo.
- Proteção estrita de segurança: NUNCA aplica Realtime, NUNCA finaliza processos do usuário.
- Respeito à bateria em notebooks: NUNCA força Alto Desempenho operando em bateria.
- Detecção de concorrência e geração de relatórios de sessão.
"""
import re
import time
import winreg
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import psutil

from src.utils.logger import app_logger
from src.utils.command_runner import run_command
from src.core.safety_manager import safety_manager, RiskLevel
from src.modules.reports.history_manager import log_operation_event

# GUIDs do Windows
HIGH_PERFORMANCE_GUID = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"

def is_running_on_battery() -> bool:
    """Verifica se o computador é um notebook operando na bateria."""
    try:
        battery = psutil.sensors_battery()
        if battery is not None:
            return not battery.power_plugged
    except Exception:
        pass
    return False

def get_current_power_plan_guid() -> Optional[str]:
    """Obtém o GUID do esquema de energia atualmente ativo no Windows."""
    rc, out, _ = run_command(["powercfg", "/getactivescheme"], timeout=8)
    if rc == 0 and out.strip():
        match = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", out)
        if match:
            return match.group(1).lower()
    return None

def set_high_performance_power_plan() -> bool:
    """Aplica o plano de energia de Alto Desempenho do Windows."""
    rc, _, _ = run_command(["powercfg", "/setactive", HIGH_PERFORMANCE_GUID], timeout=8)
    return rc == 0

def check_windows_game_mode() -> Dict[str, Any]:
    """Verifica se o Windows Game Mode está habilitado no sistema."""
    status = "Habilitado"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\GameBar",
            0,
            winreg.KEY_READ
        )
        val, _ = winreg.QueryValueEx(key, "AllowAutoGameMode")
        winreg.CloseKey(key)
        if val == 0:
            status = "Desativado"
    except Exception:
        status = "Habilitado (Padrão do Windows)"

    return {
        "status": status,
        "recommendation": "O Windows Game Mode otimiza a entrega de quadros e prioriza a GPU."
    }

class SmartGameSession:
    """
    Sessão inteligente de monitoramento e otimização de jogos.
    Garante aplicação segura, auditoria de recursos e rollback incondicional.
    """
    def __init__(self, pid: int, game_name: str, on_session_end: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.pid = pid
        self.game_name = game_name
        self.on_session_end = on_session_end
        
        self.create_time: float = 0.0
        self.process_name: str = ""
        self.original_nice: Optional[int] = None
        self.original_plan_guid: Optional[str] = None
        self.power_plan_changed = False
        
        self.is_active = False
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        
        self.cpu_samples: List[float] = []
        self.ram_samples: List[float] = []
        self.concurrent_alerts: List[str] = []
        self._thread: Optional[threading.Thread] = None

    def start_session(self) -> Dict[str, Any]:
        """Inicia a sessão aplicando apenas os ajustes seguros autorizados."""
        # 1. Identifica processo e captura create_time para evitar colisão de PID
        try:
            proc = psutil.Process(self.pid)
            self.create_time = proc.create_time()
            self.process_name = proc.name()
            self.original_nice = proc.nice()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            return {"success": False, "message": f"Não foi possível acessar o processo (PID {self.pid}): {e}"}

        # 2. Captura plano de energia atual
        self.original_plan_guid = get_current_power_plan_guid()
        on_battery = is_running_on_battery()

        # 3. Ajuste controlado de energia (apenas se conectado à tomada)
        if on_battery:
            app_logger.info("Dispositivo operando na bateria. Plano de Alto Desempenho NÃO será forçado para preservar a autonomia.")
        else:
            if self.original_plan_guid and self.original_plan_guid != HIGH_PERFORMANCE_GUID.lower():
                rc, _, _ = run_command(["powercfg", "/setactive", HIGH_PERFORMANCE_GUID], timeout=8)
                if rc == 0:
                    self.power_plan_changed = True
                    app_logger.info("Plano de energia de Alto Desempenho ativado para a sessão de jogo.")

        # 4. Ajuste controlado de prioridade: AboveNormal (NUNCA Realtime)
        try:
            if hasattr(psutil, "ABOVE_NORMAL_PRIORITY_CLASS"):
                proc.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
                app_logger.info(f"Prioridade AboveNormal configurada para {self.process_name} (PID: {self.pid}).")
        except Exception as e:
            app_logger.warning(f"Não foi possível ajustar prioridade do processo: {e}")

        self.start_time = time.time()
        self.is_active = True

        # 5. Inicia thread de monitoramento contínuo
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

        return {
            "success": True,
            "game": self.game_name,
            "pid": self.pid,
            "on_battery": on_battery,
            "power_plan_boosted": self.power_plan_changed,
            "message": f"Sessão Smart Game iniciada com sucesso para {self.game_name}."
        }

    def _monitor_loop(self):
        """Loop de monitoramento que rastreia recursos e aguarda encerramento do processo."""
        app_logger.info(f"Loop de monitoramento ativo para {self.game_name} (PID: {self.pid}).")

        while self.is_active:
            try:
                proc = psutil.Process(self.pid)
                # Proteção contra reciclagem de PID: confere create_time
                if not proc.is_running() or proc.create_time() != self.create_time:
                    break

                # Coleta amostras de telemetria
                c_cpu = proc.cpu_percent(interval=0.1)
                c_ram = proc.memory_info().rss / (1024 ** 2)
                self.cpu_samples.append(c_cpu)
                self.ram_samples.append(c_ram)

                # Rastreia concorrência (processos que não sejam o jogo consumindo CPU pesada)
                for other in psutil.process_iter(['name', 'cpu_percent']):
                    try:
                        if other.pid != self.pid and other.pid != os.getpid():
                            other_cpu = other.info.get('cpu_percent') or 0
                            if other_cpu > 25.0:
                                alert_msg = f"Concorrência: {other.info.get('name')} consumindo {other_cpu}% de CPU."
                                if alert_msg not in self.concurrent_alerts and len(self.concurrent_alerts) < 5:
                                    self.concurrent_alerts.append(alert_msg)
                                    app_logger.warning(alert_msg)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

            time.sleep(2)

        self._finalize_session()

    def _finalize_session(self):
        """Restaura incondicionalmente o estado original e registra relatório."""
        self.is_active = False
        self.end_time = time.time()
        duration_sec = round(self.end_time - self.start_time, 1)

        app_logger.info(f"Jogo {self.game_name} finalizado. Restaurando ambiente original...")

        # 1. Restaura prioridade se o processo ainda existir em transição
        try:
            proc = psutil.Process(self.pid)
            if proc.is_running() and proc.create_time() == self.create_time and self.original_nice is not None:
                proc.nice(self.original_nice)
        except Exception:
            pass

        # 2. Restaura plano de energia original caso tenha sido alterado
        if self.power_plan_changed and self.original_plan_guid:
            app_logger.info(f"Restaurando plano de energia original: {self.original_plan_guid}...")
            run_command(["powercfg", "/setactive", self.original_plan_guid], timeout=8)

        # 3. Estatísticas finais
        avg_cpu = round(sum(self.cpu_samples) / max(len(self.cpu_samples), 1), 1)
        peak_ram = round(max(self.ram_samples), 1) if self.ram_samples else 0.0

        report = {
            "game_name": self.game_name,
            "duration_seconds": duration_sec,
            "duration_minutes": round(duration_sec / 60.0, 1),
            "avg_cpu_percent": avg_cpu,
            "peak_ram_mb": peak_ram,
            "concurrent_alerts": self.concurrent_alerts,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        log_operation_event(
            f"Smart Game Session: {self.game_name}",
            "Concluído",
            f"Duração: {round(duration_sec/60, 1)} min | RAM Pico: {peak_ram} MB | CPU Média: {avg_cpu}%"
        )

        if self.on_session_end:
            try:
                self.on_session_end(report)
            except Exception as e:
                app_logger.warning(f"Erro no callback de encerramento de sessão: {e}")

    def stop_session(self):
        """Interrompe a sessão sob comando manual."""
        self.is_active = False
