"""
Módulo THERMAL GUARD - Monitoramento Térmico e Telemetria de Hardware.
Implementa camada de abstração para sensores térmicos e de clock:
- NVIDIA-SMI (temperatura, frequência, consumo em Watts e rotação de ventoinhas)
- WMI / MSAcpi_ThermalZoneTemperature (quando suportado pela BIOS/placa-mãe)
- Psutil Hardware Clocks (frequências de CPU atuais, mínimas e máximas)
- Detecção baseada em evidências de Thermal Throttling sem instalar drivers de kernel.
"""
import shutil
import subprocess
from typing import Dict, Any, List, Optional
import psutil

from src.utils.logger import app_logger

class ThermalGuard:
    """Gerenciador de telemetria térmica e de frequência."""

    def __init__(self):
        self._history_samples: List[Dict[str, Any]] = []
        self._nvidia_smi_path = shutil.which("nvidia-smi")

    def read_gpu_telemetry(self) -> Dict[str, Any]:
        """Lê telemetria direta da GPU via NVIDIA-SMI se disponível."""
        if not self._nvidia_smi_path:
            return {
                "available": False,
                "reason": "Driver / utilitário NVIDIA-SMI não detectado."
            }

        try:
            cmd = [
                self._nvidia_smi_path,
                "--query-gpu=temperature.gpu,clocks.gr,power.draw,fan.speed",
                "--format=csv,noheader,nounits"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.strip():
                parts = [p.strip() for p in res.stdout.strip().split(",")]
                temp_c = float(parts[0]) if len(parts) > 0 and parts[0] else None
                clock_mhz = float(parts[1]) if len(parts) > 1 and parts[1] else None
                power_w = float(parts[2]) if len(parts) > 2 and parts[2] else None
                fan_pct = float(parts[3]) if len(parts) > 3 and parts[3] and parts[3] != "[Not Supported]" else None

                return {
                    "available": True,
                    "temperature_c": temp_c,
                    "clock_mhz": clock_mhz,
                    "power_watts": power_w,
                    "fan_speed_percent": fan_pct,
                    "provider": "NVIDIA-SMI Nativo"
                }
        except Exception as e:
            app_logger.debug(f"Falha na consulta NVIDIA-SMI: {e}")

        return {"available": False, "reason": "Não foi possível consultar sensores de GPU."}

    def read_cpu_telemetry(self) -> Dict[str, Any]:
        """Lê frequência e temperatura de CPU através de provedores suportados."""
        freq_info = {}
        try:
            cfreq = psutil.cpu_freq()
            if cfreq:
                freq_info = {
                    "current_mhz": round(cfreq.current, 1) if cfreq.current else None,
                    "min_mhz": round(cfreq.min, 1) if cfreq.min else None,
                    "max_mhz": round(cfreq.max, 1) if cfreq.max else None
                }
        except Exception:
            pass

        # Tentativa de leitura de temperatura via WMI MSAcpi_ThermalZoneTemperature
        cpu_temp = None
        try:
            import winreg
            cmd = ["powershell", "-NoProfile", "-Command", "(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue).CurrentTemperature"]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if p.returncode == 0 and p.stdout.strip():
                kelvin_tenths = float(p.stdout.strip().split()[0])
                celsius = round((kelvin_tenths - 2732) / 10.0, 1)
                if 10.0 <= celsius <= 125.0:
                    cpu_temp = celsius
        except Exception:
            pass

        return {
            "frequency": freq_info,
            "temperature_c": cpu_temp,
            "has_temperature": cpu_temp is not None,
            "status": "Normal" if (cpu_temp is None or cpu_temp < 80.0) else "Elevada"
        }

    def evaluate_throttling(self, cpu_info: Dict[str, Any], gpu_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Avalia rigorosamente indícios de thermal throttling com base em evidências técnicas:
        Exige alta temperatura combinada com queda acentuada de clock ou limitação térmica comprovada.
        NUNCA declara throttling apenas porque a temperatura está alta.
        """
        indicators = []
        is_throttling = False

        # Avaliação da CPU
        cpu_temp = cpu_info.get("temperature_c")
        cpu_freq = cpu_info.get("frequency", {})
        curr_mhz = cpu_freq.get("current_mhz")
        base_mhz = cpu_freq.get("max_mhz")

        if cpu_temp and cpu_temp >= 95.0:
            if curr_mhz and base_mhz and curr_mhz < (base_mhz * 0.70):
                indicators.append(f"Indício de Throttling na CPU: Temperatura em {cpu_temp}°C com queda severa de clock ({curr_mhz} MHz vs base {base_mhz} MHz).")
                is_throttling = True
            else:
                indicators.append(f"CPU operando em temperatura elevada ({cpu_temp}°C), mas sem evidência conclusiva de limitação de clock.")

        # Avaliação da GPU
        if gpu_info.get("available"):
            gpu_temp = gpu_info.get("temperature_c")
            if gpu_temp and gpu_temp >= 88.0:
                indicators.append(f"Temperatura da GPU elevada ({gpu_temp}°C).")

        return {
            "throttling_detected": is_throttling,
            "status": "Crítico / Throttling Evidente" if is_throttling else ("Atenção Térmica" if indicators else "Térmica Normal e Estável"),
            "evidence": indicators if indicators else ["Todas as frequências e temperaturas estão dentro dos parâmetros operacionais seguros."]
        }

    def get_full_thermal_snapshot(self) -> Dict[str, Any]:
        """Gera um instantâneo completo dos dados térmicos e de hardware."""
        cpu = self.read_cpu_telemetry()
        gpu = self.read_gpu_telemetry()
        analysis = self.evaluate_throttling(cpu, gpu)

        snapshot = {
            "cpu": cpu,
            "gpu": gpu,
            "analysis": analysis
        }

        self._history_samples.append(snapshot)
        if len(self._history_samples) > 60:
            self._history_samples.pop(0)

        return snapshot

thermal_guard = ThermalGuard()
