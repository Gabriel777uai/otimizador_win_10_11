"""
Módulo de Diagnóstico de Discos e Otimização Inteligente de Armazenamento.
Relaciona cada partição/volume ao seu respectivo disco físico.
Utiliza comportamento nativo seguro de Optimize-Volume com validação estrita de letra de unidade.
"""
import re
import json
from typing import List, Dict, Any, Optional, Callable
from src.utils.logger import app_logger
from src.utils.command_runner import run_command
from src.core.safety_manager import safety_manager, RiskLevel

def validate_drive_letter(drive_letter: str) -> str:
    """Valida estritamente a letra da unidade (deve ser exatamente um caractere A-Z)."""
    clean = drive_letter.replace(":", "").replace("\\", "").replace("/", "").strip().upper()
    if not re.match(r"^[A-Z]$", clean):
        raise ValueError(f"Letra de unidade inválida: '{drive_letter}'. Deve ser uma única letra de A a Z.")
    return clean

def get_volume_physical_disk_info(drive_letter: str) -> Dict[str, Any]:
    """
    Identifica com precisão o disco físico correspondente a uma letra de volume.
    Relaciona partição -> disco físico sem inferências globais.
    """
    clean_letter = validate_drive_letter(drive_letter)
    
    cmd = [
        "powershell", "-NoProfile", "-Command",
        f"Get-Partition -DriveLetter {clean_letter} -ErrorAction SilentlyContinue | Get-Disk -ErrorAction SilentlyContinue | "
        "Select-Object Number, FriendlyName, BusType, MediaType, HealthStatus, Size | ConvertTo-Json -Compress"
    ]
    rc, out, _ = run_command(cmd, timeout=10)
    
    disk_info = {
        "drive_letter": clean_letter,
        "disk_number": None,
        "model": "Desconhecido",
        "bus_type": "Desconhecido",
        "media_type": "Desconhecido",
        "health": "Desconhecido",
        "is_ssd": False,
        "is_hdd": False,
        "is_identified": False
    }

    if rc == 0 and out.strip():
        try:
            data = json.loads(out.strip())
            if isinstance(data, list) and data:
                data = data[0]

            bus = str(data.get("BusType") or "").strip()
            media = str(data.get("MediaType") or "").strip()
            model = str(data.get("FriendlyName") or "Disco Físico").strip()

            disk_info["disk_number"] = data.get("Number")
            disk_info["model"] = model
            disk_info["bus_type"] = bus if bus else "Desconhecido"
            disk_info["media_type"] = media if media else "Desconhecido"
            disk_info["health"] = str(data.get("HealthStatus") or "Saudável")

            # Evidência técnica real:
            # NVMe é comprovadamente SSD.
            # MediaType 'SSD' é comprovadamente SSD.
            # MediaType 'HDD' é comprovadamente HDD.
            if bus.upper() == "NVME" or media.upper() == "SSD":
                disk_info["is_ssd"] = True
                disk_info["is_identified"] = True
                disk_info["media_type"] = "SSD (NVMe)" if bus.upper() == "NVME" else "SSD"
            elif media.upper() == "HDD":
                disk_info["is_hdd"] = True
                disk_info["is_identified"] = True
                disk_info["media_type"] = "HDD (Magnético)"
            else:
                disk_info["is_identified"] = False
                disk_info["media_type"] = "Desconhecido / Não Especificado"

        except Exception as e:
            app_logger.warning(f"Erro ao processar dados de partição para {clean_letter}: {e}")

    return disk_info

def get_physical_disks_status() -> List[Dict[str, Any]]:
    """Consulta discos físicos presentes no sistema via CIM/PowerShell."""
    disks = []
    cmd = [
        "powershell", "-NoProfile", "-Command",
        "Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, BusType, HealthStatus, Size | ConvertTo-Json -Compress"
    ]
    rc, out, _ = run_command(cmd, timeout=10)
    if rc == 0 and out.strip():
        try:
            data = json.loads(out.strip())
            if isinstance(data, dict):
                data = [data]
            for d in data:
                size_gb = round(d.get("Size", 0) / (1024 ** 3), 1)
                bus = str(d.get("BusType") or "Desconhecido")
                media = str(d.get("MediaType") or "Desconhecido")
                if bus.upper() == "NVME" and media == "Desconhecido":
                    media = "SSD (NVMe)"

                disks.append({
                    "device_id": str(d.get("DeviceId", "0")),
                    "name": d.get("FriendlyName", "Disco Físico"),
                    "media_type": media,
                    "bus_type": bus,
                    "health": d.get("HealthStatus", "Saudável"),
                    "size_gb": size_gb
                })
        except Exception:
            pass
    return disks

def optimize_volume_smart(
    drive_letter: str = "C",
    user_confirmed: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Executa a otimização de volume utilizando o comportamento automático seguro do Windows
    (Optimize-Volume), relacionando a ação às evidências do disco específico da unidade.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="OPTIMIZE_VOLUME",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    try:
        clean_letter = validate_drive_letter(drive_letter)
    except ValueError as ve:
        return {"success": False, "message": str(ve)}

    if progress_callback:
        progress_callback(15, f"Identificando características de hardware da unidade {clean_letter}:...")

    # Identifica o disco específico desta unidade (nunca usa dados de outro disco)
    disk_info = get_volume_physical_disk_info(clean_letter)
    app_logger.info(f"Otimização em {clean_letter}: -> Modelo: {disk_info['model']}, Tipo: {disk_info['media_type']}, Bus: {disk_info['bus_type']}")

    if progress_callback:
        progress_callback(35, f"Iniciando otimização na unidade {clean_letter}: ({disk_info['media_type']})...")

    # Comando seguro nativo:
    # Se comprovadamente SSD: aciona -ReTrim explicitamente
    # Se comprovadamente HDD: aciona -Defrag explicitamente
    # Se Desconhecido: aciona Optimize-Volume padrão, deixando o subsistema de armazenamento do Windows decidir
    if disk_info["is_ssd"]:
        action_name = "TRIM (SSD)"
        cmd = ["powershell", "-NoProfile", "-Command", f"Optimize-Volume -DriveLetter {clean_letter} -ReTrim -Verbose"]
    elif disk_info["is_hdd"]:
        action_name = "Desfragmentação (HDD)"
        cmd = ["powershell", "-NoProfile", "-Command", f"Optimize-Volume -DriveLetter {clean_letter} -Defrag -Verbose"]
    else:
        action_name = "Otimização Automática do Windows"
        cmd = ["powershell", "-NoProfile", "-Command", f"Optimize-Volume -DriveLetter {clean_letter} -Verbose"]

    if progress_callback:
        progress_callback(60, f"Executando {action_name}...")

    rc, out, err = run_command(cmd, timeout=120)

    if progress_callback:
        progress_callback(100, "Concluído.")

    if rc == 0:
        app_logger.info(f"Otimização ({action_name}) concluída com sucesso na unidade {clean_letter}:.")
        return {
            "success": True,
            "action": action_name,
            "drive": f"{clean_letter}:",
            "disk_model": disk_info["model"],
            "media_type": disk_info["media_type"],
            "message": f"{action_name} executada com sucesso na unidade {clean_letter}: ({disk_info['model']})."
        }

    return {
        "success": False,
        "action": action_name,
        "drive": f"{clean_letter}:",
        "message": f"Falha na otimização da unidade {clean_letter}:: {err or out}"
    }

def run_chkdsk_scan(
    drive_letter: str = "C",
    user_confirmed: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Executa chkdsk /scan (somente leitura seguro online).
    Não desmonta a unidade nem interrompe serviços de sistema.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="CHKDSK_SCAN",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    try:
        clean_letter = validate_drive_letter(drive_letter)
    except ValueError as ve:
        return {"success": False, "message": str(ve)}

    if progress_callback:
        progress_callback(15, f"Iniciando verificação online na unidade {clean_letter}:...")

    app_logger.info(f"Iniciando verificação segura chkdsk /scan em {clean_letter}:...")
    cmd = ["chkdsk", f"{clean_letter}:", "/scan"]
    
    if progress_callback:
        progress_callback(50, f"Analisando integridade do sistema de arquivos de {clean_letter}:...")

    rc, out, err = run_command(cmd, timeout=180)

    if progress_callback:
        progress_callback(100, "Concluído.")

    is_healthy = "nenhum problema" in out.lower() or "no problems" in out.lower() or rc == 0

    return {
        "success": rc == 0,
        "is_healthy": is_healthy,
        "drive": f"{clean_letter}:",
        "output": out,
        "message": "Nenhum problema encontrado no sistema de arquivos." if is_healthy else f"Verificação concluída com avisos:\n{out[:300]}"
    }
