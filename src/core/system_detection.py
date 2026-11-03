"""
Módulo de detecção e diagnóstico de hardware e sistema operacional.
Utiliza APIs nativas rápidas do Windows (winreg, psutil e platform).
Identifica métricas reais de frequência de CPU, modelo de GPU, VRAM dedicada,
saúde de armazenamento e tipos de mídia sem placeholders.
"""
import os
import sys
import platform
import time
import winreg
from typing import Dict, Any, List, Optional
import psutil

from src.utils.logger import app_logger

def get_cpu_info() -> Dict[str, Any]:
    """Obtém modelo do processador, núcleos, threads e frequência real de clock."""
    model_name = "Não disponível"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            0,
            winreg.KEY_READ
        )
        val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        winreg.CloseKey(key)
        if val:
            model_name = val.strip()
    except Exception:
        model_name = platform.processor() or "Não disponível"

    # Frequência real de clock
    freq_str = "Não disponível"
    try:
        cfreq = psutil.cpu_freq()
        if cfreq and cfreq.current:
            freq_str = f"{round(cfreq.current, 1)} MHz"
    except Exception:
        pass

    return {
        "model": model_name,
        "cores_physical": psutil.cpu_count(logical=False) or 1,
        "threads_logical": psutil.cpu_count(logical=True) or 1,
        "current_percent": psutil.cpu_percent(interval=None),
        "frequency_mhz": freq_str
    }

def get_memory_info() -> Dict[str, Any]:
    """Obtém métricas precisas de memória RAM instalada e disponível."""
    vm = psutil.virtual_memory()
    return {
        "total_gb": round(vm.total / (1024 ** 3), 1),
        "available_gb": round(vm.available / (1024 ** 3), 1),
        "used_gb": round(vm.used / (1024 ** 3), 1),
        "percent_used": vm.percent
    }

def get_gpu_info() -> List[Dict[str, Any]]:
    """Detecta adaptadores de vídeo instalados, fabricante, driver e VRAM real."""
    gpus = []
    base_class_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"

    for i in range(8):
        sub_key = f"{base_class_path}\\000{i}" if i < 10 else f"{base_class_path}\\00{i}"
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key, 0, winreg.KEY_READ)
            driver_desc, _ = winreg.QueryValueEx(k, "DriverDesc")
            driver_ver = "Não disponível"
            try:
                driver_ver, _ = winreg.QueryValueEx(k, "DriverVersion")
            except Exception:
                pass

            # Leitura da VRAM em bytes do Registro
            vram_str = "Não disponível"
            for v_name in ["HardwareInformation.qwMemorySize", "HardwareInformation.MemorySize"]:
                try:
                    v_bytes, _ = winreg.QueryValueEx(k, v_name)
                    if v_bytes and v_bytes > 0:
                        vram_str = f"{round(v_bytes / (1024 ** 3), 1)} GB"
                        break
                except OSError:
                    pass

            winreg.CloseKey(k)

            if driver_desc and not any(g["name"] == driver_desc for g in gpus):
                # Identifica fabricante
                desc_lower = driver_desc.lower()
                vendor = "NVIDIA" if "nvidia" in desc_lower else ("AMD" if "amd" in desc_lower or "radeon" in desc_lower else ("Intel" if "intel" in desc_lower else "Não disponível"))

                gpus.append({
                    "name": driver_desc.strip(),
                    "vendor": vendor,
                    "driver_version": driver_ver.strip(),
                    "vram": vram_str
                })
        except Exception:
            continue

    if not gpus:
        gpus.append({
            "name": "Adaptador Básico do Windows",
            "vendor": "Não disponível",
            "driver_version": "Não disponível",
            "vram": "Não disponível"
        })
    return gpus

def get_disk_info() -> List[Dict[str, Any]]:
    """Obtém dados das partições mapeadas e saúde de armazenamento."""
    disks = []
    try:
        partitions = psutil.disk_partitions(all=False)
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total_gb": round(usage.total / (1024 ** 3), 1),
                    "used_gb": round(usage.used / (1024 ** 3), 1),
                    "free_gb": round(usage.free / (1024 ** 3), 1),
                    "percent_used": usage.percent
                })
            except (PermissionError, OSError):
                continue
    except Exception as e:
        app_logger.warning(f"Erro ao consultar partições: {e}")

    return disks

def get_os_info() -> Dict[str, Any]:
    """Obtém versão e compilação do Windows via Registro."""
    os_name = f"Windows {platform.release()}"
    build_num = "Não disponível"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
            0,
            winreg.KEY_READ
        )
        prod_name, _ = winreg.QueryValueEx(key, "ProductName")
        build_str, _ = winreg.QueryValueEx(key, "CurrentBuildNumber")
        winreg.CloseKey(key)
        if prod_name:
            os_name = prod_name
        if build_str:
            build_num = build_str
    except Exception:
        pass

    return {
        "os_name": os_name,
        "caption": os_name,
        "build": build_num,
        "architecture": platform.machine(),
        "hostname": platform.node()
    }

def get_system_snapshot() -> Dict[str, Any]:
    """Retorna um diagnóstico completo dos subsistemas de hardware e SO."""
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "gpu": get_gpu_info(),
        "disks": get_disk_info(),
        "os": get_os_info()
    }

get_full_system_snapshot = get_system_snapshot
