"""
Módulo de Análise de Armazenamento e Gerenciamento da Lixeira.
Utiliza APIs nativas do Windows para medição e esvaziamento seguro da Lixeira.
"""
import ctypes
import os
from ctypes import wintypes
from typing import Dict, Any, List
from pathlib import Path
import psutil

from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager, RiskLevel

class SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("i64Size", ctypes.c_int64),
        ("i64NumItems", ctypes.c_int64)
    ]

def get_recycle_bin_info() -> Dict[str, Any]:
    """Obtém o tamanho total ocupado pela lixeira e o número de itens."""
    info = SHQUERYRBINFO()
    info.cbSize = ctypes.sizeof(SHQUERYRBINFO)

    try:
        res = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
        if res == 0:
            return {
                "size_bytes": info.i64Size,
                "size_mb": round(info.i64Size / (1024 ** 2), 2),
                "num_items": info.i64NumItems
            }
    except Exception as e:
        app_logger.warning(f"Erro ao consultar Lixeira: {e}")

    return {"size_bytes": 0, "size_mb": 0.0, "num_items": 0}

def empty_recycle_bin(user_confirmed: bool = False) -> Dict[str, Any]:
    """
    Esvazia a Lixeira permanentemente.
    Exige confirmação explícita separada (Nível 2). Nunca executa silenciosamente.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="EMPTY_RECYCLE_BIN",
        risk_level=RiskLevel.LEVEL_2_CONTROLLED,
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    # Flags: SHERB_NOCONFIRMATION = 0x00000001, SHERB_NOPROGRESSUI = 0x00000002, SHERB_NOSOUND = 0x00000004
    try:
        prev_info = get_recycle_bin_info()
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
        if res == 0:
            app_logger.info(f"Lixeira esvaziada com sucesso. Itens removidos: {prev_info['num_items']}")
            return {
                "success": True,
                "freed_mb": prev_info["size_mb"],
                "items_cleared": prev_info["num_items"],
                "message": "Lixeira esvaziada com sucesso."
            }
        else:
            return {"success": False, "message": f"Código retornado pelo Windows: {res}"}
    except Exception as e:
        app_logger.error(f"Erro ao esvaziar lixeira: {e}")
        return {"success": False, "message": str(e)}

def get_storage_overview() -> List[Dict[str, Any]]:
    """Retorna o panorama de espaço e utilização de todas as unidades mapeadas."""
    overview = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            overview.append({
                "mountpoint": part.mountpoint,
                "device": part.device,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "percent_used": usage.percent
            })
        except Exception:
            continue
    return overview
