"""
Sistema Centralizado de Progresso - ALTUS PC OPTIMIZER.
Permite aos módulos de execução relatar o progresso de forma desacoplada, thread-safe e em tempo real.
Suporta barras indeterminadas, porcentagens reais, contagem de itens e cancelamento cooperativo.
"""
import time
from enum import Enum
from typing import Optional, Dict, Any, Callable
from PySide6.QtCore import QObject, Signal

class OperationState(Enum):
    WAITING = "Aguardando"
    PREPARING = "Preparando"
    RUNNING = "Em execução"
    FINALIZING = "Concluindo"
    COMPLETED = "Concluído"
    CANCELLED = "Cancelado"
    ERROR = "Erro"

class ProgressReporter(QObject):
    """Objeto emissor de sinais para uma operação individual."""
    started = Signal(str, str, int)  # op_name, step_name, total_items
    progress_changed = Signal(int, int, str, float)  # current, total, step_desc, percent
    state_changed = Signal(OperationState, str)  # new_state, message
    indeterminate_changed = Signal(bool, str)  # is_indeterminate, step_desc
    finished = Signal(dict)  # results dict
    error_occurred = Signal(str)  # error message

    def __init__(self):
        super().__init__()
        self._is_cancelled = False
        self._start_time: float = 0.0
        self._total_items = 0
        self._current_items = 0
        self._is_indeterminate = False

    def start(self, op_name: str, initial_step: str = "Preparando...", total_items: int = 0):
        self._is_cancelled = False
        self._start_time = time.time()
        self._total_items = total_items
        self._current_items = 0
        self._is_indeterminate = False
        self.started.emit(op_name, initial_step, total_items)
        self.state_changed.emit(OperationState.RUNNING, initial_step)

    def set_indeterminate(self, is_indeterminate: bool = True, step_desc: str = ""):
        self._is_indeterminate = is_indeterminate
        self.indeterminate_changed.emit(is_indeterminate, step_desc)

    def update(self, current: int, total: int = 0, step_desc: str = ""):
        if self._is_cancelled:
            return

        if total > 0:
            self._total_items = total
        self._current_items = current

        percent = 0.0
        if self._total_items > 0:
            percent = min(100.0, round((current / self._total_items) * 100.0, 1))

        self.progress_changed.emit(current, self._total_items, step_desc, percent)

    def update_percent(self, percent: int, step_desc: str = ""):
        """Atualização direta de porcentagem de 0 a 100 ou indeterminado se < 0."""
        if self._is_cancelled:
            return

        if percent < 0:
            self.set_indeterminate(True, step_desc)
        else:
            if self._is_indeterminate:
                self.set_indeterminate(False, step_desc)
            self.progress_changed.emit(percent, 100, step_desc, float(percent))

    def complete(self, result_data: Optional[Dict[str, Any]] = None):
        elapsed = round(time.time() - self._start_time, 2)
        res = result_data or {}
        res["elapsed_seconds"] = elapsed
        self.state_changed.emit(OperationState.COMPLETED, "Operação concluída.")
        self.finished.emit(res)

    def fail(self, error_message: str):
        self.state_changed.emit(OperationState.ERROR, error_message)
        self.error_occurred.emit(error_message)

    def cancel(self):
        self._is_cancelled = True
        self.state_changed.emit(OperationState.CANCELLED, "Operação cancelada pelo usuário.")

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    @property
    def elapsed_time_str(self) -> str:
        if self._start_time == 0.0:
            return "0s"
        seconds = int(time.time() - self._start_time)
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"

    def as_callback(self) -> Callable[[int, str], None]:
        """Gera um callback compatível com módulos backend (pct, msg)."""
        def _cb(pct: int, msg: str):
            if not self._is_cancelled:
                self.update_percent(pct, msg)
        return _cb

class OperationProgressManager:
    """Gerenciador singleton para criação de repórteres de progresso."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OperationProgressManager, cls).__new__(cls)
        return cls._instance

    def create_reporter(self) -> ProgressReporter:
        return ProgressReporter()

progress_manager = OperationProgressManager()
