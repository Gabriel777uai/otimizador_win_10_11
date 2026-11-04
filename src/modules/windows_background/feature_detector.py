"""
Detector de Recursos e Compatibilidade do Windows - ALTUS PC OPTIMIZER.
Identifica build, edição, presença de recursos de IA, Copilot, Recall, Edge, Xbox,
Widgets, Telemetria e políticas suportadas pelo sistema operacional.
"""
import os
import sys
import platform
import winreg
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from src.utils.logger import app_logger

@dataclass
class WindowsFeatureStatus:
    os_name: str
    is_windows_11: bool
    build_number: int
    display_version: str
    edition: str
    architecture: str
    
    # Recursos de IA
    copilot_installed: bool
    copilot_taskbar_visible: bool
    copilot_policy_disabled: bool
    copilot_processes_active: int
    
    recall_hardware_compatible: bool
    recall_available: bool
    recall_disabled: bool
    recall_notes: str
    
    # Microsoft Edge
    edge_installed: bool
    edge_startup_boost_disabled: bool
    edge_background_mode_disabled: bool
    
    # Xbox e Gravação
    game_dvr_enabled: bool
    game_dvr_background_recording: bool
    
    # Telemetria e Diagnóstico
    telemetry_level: int  # 0=Security/Enterprise, 1=Basic, 3=Full
    tailored_experiences_disabled: bool
    feedback_frequency_zero: bool
    
    # Widgets e Experiências
    widgets_visible: bool
    suggestions_disabled: bool
    
    # Otimização de Entrega
    delivery_p2p_mode: int  # 0=HTTP Only, 1=LAN, 3=Internet
    
    # Indexador de Pesquisa
    wsearch_running: bool

def _read_reg_value(root_key, sub_key: str, value_name: str) -> tuple[Optional[Any], Optional[int]]:
    """Lê valor e tipo do Registro com segurança."""
    try:
        key = winreg.OpenKey(root_key, sub_key, 0, winreg.KEY_READ)
        val, val_type = winreg.QueryValueEx(key, value_name)
        winreg.CloseKey(key)
        return val, val_type
    except (FileNotFoundError, OSError):
        return None, None

def detect_os_details() -> Dict[str, Any]:
    """Identifica edição, versão, compilação e arquitetura do Windows."""
    build_num = 19045
    prod_name = "Windows"
    display_ver = "Desconhecida"
    edition = "Core / Home"
    
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", 0, winreg.KEY_READ)
        try: prod_name, _ = winreg.QueryValueEx(k, "ProductName")
        except Exception: pass
        try: 
            b_str, _ = winreg.QueryValueEx(k, "CurrentBuildNumber")
            build_num = int(b_str)
        except Exception: pass
        try: display_ver, _ = winreg.QueryValueEx(k, "DisplayVersion")
        except Exception: 
            try: display_ver, _ = winreg.QueryValueEx(k, "ReleaseId")
            except Exception: pass
        try: edition, _ = winreg.QueryValueEx(k, "EditionID")
        except Exception: pass
        winreg.CloseKey(k)
    except Exception as e:
        app_logger.warning(f"Erro ao ler informações do SO no Registro: {e}")

    arch = platform.machine()
    is_win11 = build_num >= 22000

    return {
        "os_name": prod_name,
        "is_windows_11": is_win11,
        "build_number": build_num,
        "display_version": display_ver,
        "edition": edition,
        "architecture": arch
    }

def detect_copilot_status() -> Dict[str, Any]:
    """Verifica instalação, visibilidade na barra de tarefas e processos do Microsoft Copilot."""
    # 1. Botão na Barra de Tarefas (Windows 11)
    val, _ = _read_reg_value(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ShowCopilotButton")
    taskbar_visible = (val != 0) if val is not None else True

    # 2. Política de Desativação
    pol_user, _ = _read_reg_value(winreg.HKEY_CURRENT_USER, r"Software\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot")
    pol_mach, _ = _read_reg_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot")
    policy_disabled = (pol_user == 1 or pol_mach == 1)

    # 3. Processos ativos relacionados ao Copilot
    import psutil
    copilot_proc_count = 0
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            name = (p.info.get('name') or '').lower()
            cmd = " ".join(p.info.get('cmdline') or []).lower()
            if "copilot" in name or "copilot" in cmd:
                copilot_proc_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # 4. Detecção de pacote AppX ou executável
    copilot_installed = False
    pkg_dirs = [
        os.path.expandvars(r"%LOCALAPPDATA%\Packages"),
        os.path.expandvars(r"%PROGRAMFILES%\WindowsApps")
    ]
    for d in pkg_dirs:
        if os.path.exists(d):
            try:
                for entry in os.listdir(d):
                    if "Microsoft.Copilot" in entry or "Microsoft.Windows.Ai.Copilot" in entry:
                        copilot_installed = True
                        break
            except (PermissionError, OSError):
                pass
        if copilot_installed:
            break

    # Se estiver no Win 11 Build >= 22621 e com botão ativo, considera presente no sistema
    os_info = detect_os_details()
    if os_info["is_windows_11"] and os_info["build_number"] >= 22621:
        copilot_installed = True

    return {
        "installed": copilot_installed,
        "taskbar_visible": taskbar_visible and not policy_disabled,
        "policy_disabled": policy_disabled,
        "active_processes": copilot_proc_count
    }

def detect_recall_status(os_info: Dict[str, Any]) -> Dict[str, Any]:
    """Verifica compatibilidade de hardware e estado do Windows Recall."""
    build = os_info.get("build_number", 0)
    arch = os_info.get("architecture", "").lower()
    
    # Recall requer Copilot+ PC (Snapdragon X / NPU >= 40 TOPS) e Win 11 Build 26100+ (24H2)
    is_compatible_build = build >= 26100
    is_arm_or_npu = ("arm" in arch or "aarch" in arch)

    compatible = is_compatible_build and is_arm_or_npu
    notes = "Recurso não suportado neste hardware (requer PC Copilot+ com NPU e Windows 11 Build 26100+)."
    
    if not is_compatible_build:
        notes = f"Incompatível: Versão do Windows ({build}) anterior à compilação 26100 (24H2)."
    elif not is_arm_or_npu:
        notes = "Arquitetura x64 padrão sem NPU Copilot+ identificada. O Recall não está ativo neste sistema."
    else:
        notes = "Hardware Copilot+ compatível identificado."

    # Verifica se a política de desativação está presente
    val, _ = _read_reg_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI", "DisableAIDataAnalysis")
    disabled = (val == 1)

    return {
        "hardware_compatible": compatible,
        "available": compatible,
        "disabled": disabled,
        "notes": notes
    }

def detect_edge_status() -> Dict[str, Any]:
    """Verifica configurações de Startup Boost e execução em segundo plano do Edge."""
    edge_paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe")
    ]
    installed = any(os.path.exists(p) for p in edge_paths)

    # Startup Boost (1 = Ativado por padrão no Edge, 0 = Desativado)
    val_boost, _ = _read_reg_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Edge", "StartupBoostEnabled")
    boost_disabled = (val_boost == 0)

    # Execução em segundo plano (1 = Ativado por padrão no Edge, 0 = Desativado)
    val_bg, _ = _read_reg_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Edge", "BackgroundModeEnabled")
    bg_disabled = (val_bg == 0)

    return {
        "installed": installed,
        "startup_boost_disabled": boost_disabled,
        "background_mode_disabled": bg_disabled
    }

def detect_gaming_dvr_status() -> Dict[str, Any]:
    """Verifica captura contínua e gravação em segundo plano do Game DVR / Xbox."""
    val_dvr, _ = _read_reg_value(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore", "GameDVR_Enabled")
    dvr_enabled = (val_dvr != 0) if val_dvr is not None else True

    val_hist, _ = _read_reg_value(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "HistoricalCaptureEnabled")
    val_app, _ = _read_reg_value(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled")
    
    bg_recording = (val_hist == 1) or (val_app == 1)

    return {
        "game_dvr_enabled": dvr_enabled,
        "background_recording_active": bg_recording
    }

def detect_telemetry_status() -> Dict[str, Any]:
    """Verifica nível de telemetria e coleta de dados diagnósticos configurados."""
    val_tel, _ = _read_reg_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry")
    level = val_tel if val_tel is not None else 3  # Padrão Windows é 3 (Full) ou 1

    val_tailor, _ = _read_reg_value(winreg.HKEY_CURRENT_USER, r"Software\Policies\Microsoft\Windows\CloudContent", "DisableTailoredExperiencesWithDiagnosticData")
    tailored_disabled = (val_tailor == 1)

    val_siuf, _ = _read_reg_value(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Siuf\Rules", "NumberOfSIUFInPeriod")
    feedback_zero = (val_siuf == 0)

    return {
        "level": level,
        "tailored_experiences_disabled": tailored_disabled,
        "feedback_frequency_zero": feedback_zero
    }

def detect_widgets_and_suggestions() -> Dict[str, Any]:
    """Verifica estado de Widgets, Notícias e Sugestões do Windows."""
    # Widgets no Windows 11 (TaskbarDa: 0=Oculto, 1=Visível)
    val_w11, _ = _read_reg_value(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarDa")
    # Notícias no Windows 10
    val_w10, _ = _read_reg_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Dsh", "AllowNewsAndInterests")
    
    widgets_visible = True
    if val_w11 is not None:
        widgets_visible = (val_w11 == 1)
    elif val_w10 is not None:
        widgets_visible = (val_w10 != 0)

    # Sugestões e Dicas Promocionais
    val_sug, _ = _read_reg_value(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338388Enabled")
    suggestions_disabled = (val_sug == 0)

    return {
        "widgets_visible": widgets_visible,
        "suggestions_disabled": suggestions_disabled
    }

def detect_delivery_optimization() -> Dict[str, Any]:
    """Verifica modo de entrega do Delivery Optimization (P2P)."""
    val, _ = _read_reg_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization", "DODownloadMode")
    # 0 = HTTP Only (Apenas servidores oficiais Microsoft, sem P2P)
    # 1 = LAN P2P
    # 3 = Internet P2P
    mode = val if val is not None else 1
    return {
        "mode": mode,
        "is_p2p_disabled": (mode == 0)
    }

def detect_wsearch_service() -> bool:
    """Verifica se o serviço de indexação do Windows Search (WSearch) está em execução."""
    import psutil
    try:
        svc = psutil.win_service_get("WSearch")
        return svc.status() == "running"
    except Exception:
        return False

def detect_all_windows_features() -> WindowsFeatureStatus:
    """Coleta e unifica o diagnóstico completo de todos os recursos de segundo plano."""
    os_info = detect_os_details()
    copilot = detect_copilot_status()
    recall = detect_recall_status(os_info)
    edge = detect_edge_status()
    gaming = detect_gaming_dvr_status()
    telemetry = detect_telemetry_status()
    widgets = detect_widgets_and_suggestions()
    delivery = detect_delivery_optimization()
    wsearch = detect_wsearch_service()

    return WindowsFeatureStatus(
        os_name=os_info["os_name"],
        is_windows_11=os_info["is_windows_11"],
        build_number=os_info["build_number"],
        display_version=os_info["display_version"],
        edition=os_info["edition"],
        architecture=os_info["architecture"],
        
        copilot_installed=copilot["installed"],
        copilot_taskbar_visible=copilot["taskbar_visible"],
        copilot_policy_disabled=copilot["policy_disabled"],
        copilot_processes_active=copilot["active_processes"],
        
        recall_hardware_compatible=recall["hardware_compatible"],
        recall_available=recall["available"],
        recall_disabled=recall["disabled"],
        recall_notes=recall["notes"],
        
        edge_installed=edge["installed"],
        edge_startup_boost_disabled=edge["startup_boost_disabled"],
        edge_background_mode_disabled=edge["background_mode_disabled"],
        
        game_dvr_enabled=gaming["game_dvr_enabled"],
        game_dvr_background_recording=gaming["background_recording_active"],
        
        telemetry_level=telemetry["level"],
        tailored_experiences_disabled=telemetry["tailored_experiences_disabled"],
        feedback_frequency_zero=telemetry["feedback_frequency_zero"],
        
        widgets_visible=widgets["widgets_visible"],
        suggestions_disabled=widgets["suggestions_disabled"],
        
        delivery_p2p_mode=delivery["mode"],
        wsearch_running=wsearch
    )
