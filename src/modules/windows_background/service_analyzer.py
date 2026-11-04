"""
Analisador de Serviços do Windows - ALTUS PC OPTIMIZER.
Classifica serviços em Essencial (Protegido), Sistema, Opcional Documentado e Terceiros.
Impede estritamente desativação em massa ou de serviços críticos de rede, áudio, segurança e kernel.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import psutil

from src.utils.logger import app_logger
from src.utils.command_runner import run_command
from src.core.safety_manager import safety_manager
from src.core.recovery_manager import register_recovery_operation
from src.core.permissions import is_admin

class ServiceCategory(Enum):
    ESSENTIAL = "ESSENCIAL_PROTEGIDO"    # RPC, DHCP, DNS, Defender, Firewall, Audio, etc. - Bloqueado
    SYSTEM = "SISTEMA_RECOMENDADO"       # Componentes centrais do Windows - Preservar
    OPTIONAL = "OPCIONAL_DOCUMENTADO"    # Recursos opcionais suportados (Fax, RetailDemo, etc.)
    THIRD_PARTY = "TERCEIROS"            # Softwares instalados pelo usuário
    UNKNOWN = "DESCONHECIDO"             # Não classificado

# Lista inviolável de serviços essenciais protegidos
PROTECTED_SERVICES = {
    "rpcss", "dhcp", "dnscache", "windefend", "sense", "mpssvc",
    "wuauserv", "bits", "cryptsvc", "eventlog", "audiosrv", "plugplay",
    "nsi", "lanmanworkstation", "dcomlaunch", "lsm", "samss", "bfe",
    "brokerinfrastructure", "systemeventsbroker", "coremessagingregistrar",
    "power", "themes", "netprofm", "wlansvc", "profsvc", "securityhealthservice"
}

# Serviços opcionais documentados pelo Windows que podem ser configurados com segurança
DOCUMENTED_OPTIONAL_SERVICES = {
    "retaildemo": "Serviço de Demonstração em Lojas (Retail Demo do Windows)",
    "fax": "Serviço de Envio e Recebimento de Fax",
    "mapsbroker": "Gerenciador de Mapas Baixados do Windows",
    "xblauthmanager": "Gerenciador de Autenticação Xbox Live (se não joga na plataforma)",
    "xblgamesave": "Serviço de Salvamento em Nuvem da Xbox Live",
    "xboxnetapisvc": "Serviço de Rede Xbox Live",
    "diagtrack": "Experiências do Usuário Conectado e Telemetria (opcional)"
}

@dataclass
class ServiceInfo:
    name: str
    display_name: str
    description: str
    bin_path: str
    start_type: str      # 'automatic', 'manual', 'disabled'
    status: str          # 'running', 'stopped'
    category: str        # 'ESSENCIAL_PROTEGIDO', 'SISTEMA_RECOMENDADO', 'OPCIONAL_DOCUMENTADO', 'TERCEIROS'
    is_protected: bool
    can_configure: bool
    risk_notes: str

def _classify_service(name: str, display_name: str, bin_path: str) -> tuple[ServiceCategory, bool, str]:
    """Classifica rigorosamente o serviço para impedir quebras de estabilidade."""
    n_lower = name.lower()
    b_lower = bin_path.lower()

    # 1. Protegido Irrevogavelmente
    if n_lower in PROTECTED_SERVICES:
        return ServiceCategory.ESSENTIAL, True, "Serviço essencial do Windows: desativação bloqueada pelo Safety Manager."

    # 2. Opcional Documentado
    if n_lower in DOCUMENTED_OPTIONAL_SERVICES:
        return ServiceCategory.OPTIONAL, False, DOCUMENTED_OPTIONAL_SERVICES[n_lower]

    # 3. Terceiros
    if "system32" not in b_lower and "syswow64" not in b_lower:
        return ServiceCategory.THIRD_PARTY, False, "Serviço de software de terceiros instalado."

    # 4. Sistema Padrão
    return ServiceCategory.SYSTEM, False, "Serviço nativo do subsistema do Windows."

def analyze_windows_services() -> List[ServiceInfo]:
    """Varre e diagnostica os serviços do Windows ativos ou registrados."""
    services: List[ServiceInfo] = []

    try:
        for svc in psutil.win_service_iter():
            try:
                name = svc.name()
                display_name = svc.display_name() or name
                desc = svc.description() or "Sem descrição"
                bin_path = svc.binpath() or ""
                start_type = svc.start_type() or "unknown"
                status = svc.status() or "unknown"

                cat, is_prot, notes = _classify_service(name, display_name, bin_path)

                info = ServiceInfo(
                    name=name,
                    display_name=display_name,
                    description=desc,
                    bin_path=bin_path,
                    start_type=start_type,
                    status=status,
                    category=cat.value,
                    is_protected=is_prot,
                    can_configure=(not is_prot and cat in (ServiceCategory.OPTIONAL, ServiceCategory.THIRD_PARTY)),
                    risk_notes=notes
                )
                services.append(info)
            except Exception:
                continue
    except Exception as e:
        app_logger.warning(f"Erro ao consultar serviços: {e}")

    # Ordena: Opcionais e Terceiros primeiro, depois Sistema, depois Essenciais
    services.sort(key=lambda s: (s.is_protected, s.category, s.name))
    return services

def configure_optional_service(
    service_name: str,
    target_start_type: str,  # 'demand' (manual), 'disabled', 'auto'
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    Altera o tipo de inicialização de um serviço opcional suportado.
    Salva o estado anterior no Auto Recovery Center para reversão de 1 clique.
    """
    s_lower = service_name.lower().strip()
    if s_lower in PROTECTED_SERVICES:
        return {
            "success": False,
            "message": f"AÇÃO BLOQUEADA: O serviço '{service_name}' é essencial para o Windows e não pode ser alterado."
        }

    auth = safety_manager.validate_and_authorize(
        op_id="CONFIGURE_OPTIONAL_SERVICE",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    if not is_admin():
        return {
            "success": False,
            "message": "A alteração de serviços do Windows exige privilégios de Administrador."
        }

    # Obtém estado original via psutil
    orig_start_type = "demand"
    try:
        svc = psutil.win_service_get(service_name)
        orig_start_type = svc.start_type()
    except Exception as e:
        return {"success": False, "message": f"Serviço '{service_name}' não encontrado: {e}"}

    record_id = register_recovery_operation(
        op_id="CONFIGURE_OPTIONAL_SERVICE",
        category="SERVICE",
        original_state={
            "service_name": service_name,
            "start_type": orig_start_type
        },
        applied_state={
            "service_name": service_name,
            "start_type": target_start_type
        },
        restore_strategy="RESTORE_SERVICE_START_TYPE",
        status="IN_PROGRESS"
    )

    # Executa sc config com lista de argumentos segura (sem shell=True)
    cmd = ["sc", "config", service_name, f"start={target_start_type}"]
    rc, out, err = run_command(cmd, timeout=15)

    if rc == 0:
        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "APPLIED")
        app_logger.info(f"Serviço '{service_name}' alterado para '{target_start_type}'. Registro: {record_id}")
        return {
            "success": True,
            "message": f"Serviço '{service_name}' configurado para inicialização '{target_start_type}' com sucesso.",
            "record_id": record_id
        }
    else:
        from src.core.recovery_manager import update_operation_status
        update_operation_status(record_id, "FAILED", err or out)
        app_logger.error(f"Falha ao reconfigurar serviço '{service_name}': {err or out}")
        return {
            "success": False,
            "message": f"Falha ao reconfigurar serviço: {err or out}"
        }
