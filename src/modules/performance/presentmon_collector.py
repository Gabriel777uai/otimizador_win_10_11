"""
Módulo de Integração com Intel PresentMon.
Gerencia localização do executável oficial, captura de telemetria ETW de DirectX/Vulkan
e processamento estruturado de quadros para medições reais.
"""
import os
import sys
import csv
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from src.utils.logger import app_logger
from src.modules.performance.metrics_calculator import calculate_benchmark_metrics

def get_presentmon_binary_path() -> Optional[Path]:
    """Localiza o binário PresentMon empacotado ou instalado no sistema."""
    candidates = []

    # 1. Diretório do PyInstaller (--onefile / --onedir)
    if hasattr(sys, '_MEIPASS'):
        candidates.append(Path(sys._MEIPASS) / "src" / "resources" / "bin" / "PresentMon.exe")
        candidates.append(Path(sys._MEIPASS) / "PresentMon.exe")

    # 2. Diretório local do projeto
    base_dir = Path(__file__).resolve().parent.parent.parent
    candidates.append(base_dir / "resources" / "bin" / "PresentMon.exe")
    candidates.append(base_dir / "src" / "resources" / "bin" / "PresentMon.exe")

    # 3. Instalações comuns do Windows
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidates.append(Path(prog_files) / "Intel" / "PresentMon" / "PresentMon.exe")
    candidates.append(Path(prog_files) / "Intel PresentMon" / "PresentMon.exe")

    for c in candidates:
        if c.exists() and c.is_file():
            return c

    # 4. Checa PATH do sistema
    import shutil
    which_path = shutil.which("PresentMon.exe") or shutil.which("PresentMon")
    if which_path:
        return Path(which_path)

    return None

def is_presentmon_available() -> bool:
    """Verifica se o binário PresentMon está acessível e executável."""
    path = get_presentmon_binary_path()
    return path is not None and path.exists()

class PresentMonSession:
    """Gerenciador de sessão de captura do PresentMon."""

    def __init__(self, target_process_name: str, target_pid: Optional[int] = None):
        self.target_process_name = target_process_name
        self.target_pid = target_pid
        self.binary_path = get_presentmon_binary_path()
        self._proc: Optional[subprocess.Popen] = None
        self._temp_csv: Optional[Path] = None
        self._is_capturing = False

    def start_capture(self, duration_seconds: int = 30) -> Tuple[bool, str]:
        """Inicia a captura assíncrona de telemetria gráfica."""
        if not self.binary_path or not self.binary_path.exists():
            return False, "Binário do PresentMon não encontrado. O executável deve estar em src/resources/bin/PresentMon.exe."

        # Cria arquivo CSV temporário seguro
        tmp_fd, tmp_path = tempfile.mkstemp(prefix="altus_pmon_", suffix=".csv")
        os.close(tmp_fd)
        self._temp_csv = Path(tmp_path)

        # Monta comando PresentMon padrão da Intel
        # Exemplo: PresentMon.exe -process_name game.exe -output_file out.csv -timed 30 -no_top
        cmd = [
            str(self.binary_path),
            "-output_file", str(self._temp_csv),
            "-no_top",
            "-terminate_on_proc_exit"
        ]

        if self.target_pid:
            cmd.extend(["-process_id", str(self.target_pid)])
        elif self.target_process_name:
            cmd.extend(["-process_name", self.target_process_name])

        if duration_seconds > 0:
            cmd.extend(["-timed", str(duration_seconds)])

        try:
            app_logger.info(f"Iniciando captura PresentMon: {' '.join(cmd)}")
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            self._is_capturing = True
            return True, "Captura iniciada com sucesso."
        except Exception as e:
            app_logger.error(f"Falha ao iniciar processo PresentMon: {e}")
            self.cleanup()
            return False, str(e)

    def stop_capture(self) -> Dict[str, Any]:
        """Encerra a captura e processa o arquivo CSV gerado."""
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()

        self._is_capturing = False
        results = self._parse_csv_data()
        self.cleanup()
        return results

    def _parse_csv_data(self) -> Dict[str, Any]:
        """Lê o arquivo CSV do PresentMon e calcula as métricas reais."""
        if not self._temp_csv or not self._temp_csv.exists() or self._temp_csv.stat().st_size == 0:
            return {
                "has_data": False,
                "error": "Nenhum dado capturado pelo PresentMon durante a sessão."
            }

        frametimes: List[float] = []
        cpu_frametimes: List[float] = []
        gpu_frametimes: List[float] = []

        try:
            with open(self._temp_csv, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # PresentMon v1/v2 compatibilidade de colunas:
                    # 'MsBetweenPresents' ou 'msBetweenPresents'
                    ft_str = row.get("MsBetweenPresents") or row.get("msBetweenPresents") or row.get("msBetweenDisplayChange")
                    if ft_str:
                        try:
                            ft_val = float(ft_str)
                            if 0.1 <= ft_val <= 1000.0:
                                frametimes.append(ft_val)
                        except ValueError:
                            pass

                    # CPU e GPU frametimes se disponíveis
                    cpu_str = row.get("CpuBusyMs") or row.get("msCPUBusy")
                    if cpu_str:
                        try:
                            cpu_frametimes.append(float(cpu_str))
                        except ValueError:
                            pass

                    gpu_str = row.get("GpuBusyMs") or row.get("msGPUBusy")
                    if gpu_str:
                        try:
                            gpu_frametimes.append(float(gpu_str))
                        except ValueError:
                            pass

            if not frametimes:
                return {
                    "has_data": False,
                    "error": "O arquivo CSV foi gerado, mas nenhum quadro compatível foi registrado para o processo alvo."
                }

            metrics = calculate_benchmark_metrics(
                frametimes,
                cpu_frametimes_ms=cpu_frametimes if cpu_frametimes else None,
                gpu_frametimes_ms=gpu_frametimes if gpu_frametimes else None
            )
            metrics["process_name"] = self.target_process_name
            metrics["total_samples"] = len(frametimes)
            return metrics

        except Exception as e:
            app_logger.error(f"Erro ao analisar CSV do PresentMon: {e}")
            return {"has_data": False, "error": f"Erro de leitura: {e}"}

    def cleanup(self):
        """Remove o arquivo temporário de captura."""
        if self._temp_csv and self._temp_csv.exists():
            try:
                self._temp_csv.unlink(missing_ok=True)
            except Exception:
                pass
        self._temp_csv = None
