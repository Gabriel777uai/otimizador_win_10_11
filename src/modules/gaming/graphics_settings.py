"""
Módulo de Informações e Configurações Gráficas.
Identifica resoluções e taxas de atualização suportadas pelo monitor.
Não executa overclock nem hacks inseguros no Registro.
"""
import ctypes
import os
import subprocess
from ctypes import wintypes
from typing import Dict, Any, List
from src.utils.logger import app_logger

class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmOrientation", ctypes.c_short),
        ("dmPaperSize", ctypes.c_short),
        ("dmPaperLength", ctypes.c_short),
        ("dmPaperWidth", ctypes.c_short),
        ("dmScale", ctypes.c_short),
        ("dmCopies", ctypes.c_short),
        ("dmDefaultSource", ctypes.c_short),
        ("dmPrintQuality", ctypes.c_short),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod", wintypes.DWORD),
        ("dmICMIntent", wintypes.DWORD),
        ("dmMediaType", wintypes.DWORD),
        ("dmDitherType", wintypes.DWORD),
        ("dmReserved1", wintypes.DWORD),
        ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD),
        ("dmPanningHeight", wintypes.DWORD),
    ]

def get_current_display_mode() -> Dict[str, Any]:
    """Obtém resolução atual e taxa de atualização (Hz) do monitor primário."""
    devmode = DEVMODEW()
    devmode.dmSize = ctypes.sizeof(DEVMODEW)

    ENUM_CURRENT_SETTINGS = -1
    try:
        if ctypes.windll.user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(devmode)):
            return {
                "width": devmode.dmPelsWidth,
                "height": devmode.dmPelsHeight,
                "refresh_rate_hz": devmode.dmDisplayFrequency,
                "color_depth_bits": devmode.dmBitsPerPel,
                "resolution": f"{devmode.dmPelsWidth}x{devmode.dmPelsHeight} @ {devmode.dmDisplayFrequency}Hz"
            }
    except Exception as e:
        app_logger.warning(f"Erro ao obter modo de exibição: {e}")

    return {
        "width": 1920,
        "height": 1080,
        "refresh_rate_hz": 60,
        "color_depth_bits": 32,
        "resolution": "Padrão (1920x1080 @ 60Hz)"
    }

def open_windows_graphics_settings():
    """Abre o painel oficial de configurações de elementos gráficos do Windows."""
    try:
        os.system("start ms-settings:display-advancedgraphicsettings")
    except Exception as e:
        app_logger.warning(f"Não foi possível abrir painel de gráficos do Windows: {e}")
