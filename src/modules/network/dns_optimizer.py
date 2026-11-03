"""
Módulo de Configuração de DNS Personalizado e Otimização de Resolução.
Oferece provedores confiáveis com backup rigoroso, verificação de integridade e restauração exata de estado (DHCP ou Estático).
"""
import re
import json
from typing import Dict, Any, List, Optional, Tuple, Callable
from src.utils.logger import app_logger
from src.utils.command_runner import run_command
from src.core.safety_manager import safety_manager, RiskLevel
from src.core.recovery_manager import save_state_backup, load_latest_backup
from src.modules.network.network_analyzer import get_network_gateway_and_dns, get_network_adapters_info

DNS_PROFILES = {
    "Cloudflare": {"primary": "1.1.1.1", "secondary": "1.0.0.1", "desc": "Alta velocidade e foco em privacidade."},
    "Google": {"primary": "8.8.8.8", "secondary": "8.8.4.4", "desc": "Alta disponibilidade e alcance global."},
    "Quad9": {"primary": "9.9.9.9", "secondary": "149.112.112.112", "desc": "Proteção integrada contra domínios maliciosos."},
    "DHCP": {"primary": "", "secondary": "", "desc": "Obtido automaticamente pelo roteador local (Padrão)."}
}

def get_adapter_dns_details(adapter_name: str) -> Dict[str, Any]:
    """
    Obtém com precisão o estado de configuração DNS de uma interface específica:
    - Modo: 'dhcp' ou 'static'
    - Servidores configurados em ordem exata
    - Interface Index e Alias estáveis
    """
    cmd = ["netsh", "interface", "ipv4", "show", "dns", f"name={adapter_name}"]
    rc, out, _ = run_command(cmd, timeout=10)
    
    is_static = "estaticamente" in out.lower() or "statically" in out.lower()
    is_dhcp = "dhcp" in out.lower() and not is_static
    ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", out)

    # Identificador estável via PowerShell
    idx_cmd = [
        "powershell", "-NoProfile", "-Command",
        f"(Get-NetAdapter -Name '{adapter_name}' -ErrorAction SilentlyContinue).ifIndex"
    ]
    _, idx_out, _ = run_command(idx_cmd, timeout=6)
    if_index = idx_out.strip() if idx_out.strip() else "0"

    mode = "static" if is_static else ("dhcp" if is_dhcp else "unknown")

    return {
        "adapter_name": adapter_name,
        "interface_index": if_index,
        "mode": mode,
        "is_dhcp": is_dhcp,
        "is_static": is_static,
        "dns_servers": ips,
        "primary_dns": ips[0] if ips else None,
        "secondary_dns": ips[1] if len(ips) > 1 else None
    }

def get_current_dns_status() -> Dict[str, Any]:
    """Obtém status do DNS atual e adaptadores principais."""
    adapters = get_network_adapters_info()
    primary_adapter = adapters[0]["interface"] if adapters else "Ethernet"
    details = get_adapter_dns_details(primary_adapter)
    net = get_network_gateway_and_dns()

    return {
        "adapter": primary_adapter,
        "details": details,
        "current_dns": details["dns_servers"] if details["dns_servers"] else ["Automático (DHCP)"],
        "gateway": net.get("gateway", "N/A"),
        "available_profiles": DNS_PROFILES
    }

def _apply_dns_state(adapter_name: str, mode: str, servers: List[str]) -> Tuple[bool, str]:
    """Aplica o estado exato de DNS (modo DHCP ou Estático com lista ordenada de IPs)."""
    if mode == "dhcp" or not servers:
        cmd = ["netsh", "interface", "ipv4", "set", "dns", f"name={adapter_name}", "source=dhcp"]
        rc, out, err = run_command(cmd, timeout=15)
        if rc == 0:
            return True, f"DNS da interface '{adapter_name}' redefinido para DHCP automático."
        return False, err or out or "Falha ao definir DHCP."

    # Configuração estática
    primary = servers[0]
    cmd_primary = ["netsh", "interface", "ipv4", "set", "dns", f"name={adapter_name}", "static", primary, "primary"]
    rc_p, out_p, err_p = run_command(cmd_primary, timeout=15)
    if rc_p != 0:
        return False, f"Falha ao configurar DNS primário ({primary}): {err_p or out_p}"

    # Adiciona servidores secundários mantendo o índice
    for idx, srv in enumerate(servers[1:], start=2):
        cmd_sec = ["netsh", "interface", "ipv4", "add", "dns", f"name={adapter_name}", srv, f"index={idx}"]
        rc_s, out_s, err_s = run_command(cmd_sec, timeout=15)
        if rc_s != 0:
            return False, f"Falha ao configurar DNS secundário ({srv}): {err_s or out_s}"

    return True, f"DNS estático configurado com sucesso ({', '.join(servers)})."

def apply_custom_dns(
    adapter_name: str,
    profile_name: str,
    user_confirmed: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Aplica configuração de DNS selecionada com backup completo do estado anterior.
    Realiza rollback automático caso a configuração falhe parcialmente.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="APPLY_CUSTOM_DNS",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    if profile_name not in DNS_PROFILES:
        return {"success": False, "message": f"Perfil DNS '{profile_name}' não reconhecido."}

    if progress_callback:
        progress_callback(15, "Capturando estado atual do DNS para backup seguro...")

    # 1. Backup detalhado do estado anterior
    previous_state = get_adapter_dns_details(adapter_name)
    save_state_backup("DNS_CONFIG", {
        "adapter_name": adapter_name,
        "interface_index": previous_state.get("interface_index"),
        "mode": previous_state.get("mode"),
        "dns_servers": previous_state.get("dns_servers"),
        "timestamp_label": "Backup pré-alteração de DNS"
    })
    app_logger.info(f"Backup de DNS realizado para {adapter_name}: modo={previous_state.get('mode')}, servidores={previous_state.get('dns_servers')}")

    profile = DNS_PROFILES[profile_name]

    if progress_callback:
        progress_callback(50, f"Aplicando perfil {profile_name}...")

    # 2. Aplicação com verificação e proteção de rollback
    if profile_name == "DHCP":
        success, msg = _apply_dns_state(adapter_name, "dhcp", [])
        if not success:
            return {"success": False, "message": msg}
    else:
        servers = [profile["primary"]]
        if profile.get("secondary"):
            servers.append(profile["secondary"])

        success, msg = _apply_dns_state(adapter_name, "static", servers)
        if not success:
            app_logger.error(f"Erro na configuração de DNS. Iniciando rollback para estado original: {msg}")
            if progress_callback:
                progress_callback(75, "Erro detectado. Executando rollback para o estado anterior...")
            
            # Rollback imediato
            rollback_ok, rollback_msg = _apply_dns_state(
                adapter_name,
                previous_state["mode"],
                previous_state["dns_servers"]
            )
            return {
                "success": False,
                "message": f"{msg} | Rollback executado: {'Sucesso' if rollback_ok else 'Falha (' + rollback_msg + ')'}"
            }

    if progress_callback:
        progress_callback(100, "Concluído.")

    app_logger.info(f"DNS {profile_name} aplicado com sucesso na interface '{adapter_name}'.")
    return {
        "success": True,
        "message": f"DNS alterado com sucesso para {profile_name}. Backup do estado anterior salvo com segurança."
    }

def restore_previous_dns(
    user_confirmed: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Restaura exatamente o estado de DNS do último backup (DHCP ou Estático com seus servidores originais).
    Nunca converte para DHCP se a configuração original era estática.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="RESTORE_DNS",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    if progress_callback:
        progress_callback(20, "Carregando último backup de DNS...")

    backup = load_latest_backup("DNS_CONFIG")
    if not backup or "data" not in backup:
        return {"success": False, "message": "Nenhum backup prévio de DNS encontrado."}

    data = backup["data"]
    adapter = data.get("adapter_name", "Ethernet")
    orig_mode = data.get("mode", "dhcp")
    orig_servers = data.get("dns_servers", [])

    app_logger.info(f"Restaurando DNS de '{adapter}' para estado original: modo={orig_mode}, servidores={orig_servers}")

    if progress_callback:
        progress_callback(60, f"Restaurando DNS ({orig_mode})...")

    success, msg = _apply_dns_state(adapter, orig_mode, orig_servers)

    if progress_callback:
        progress_callback(100, "Concluído.")

    if success:
        return {
            "success": True,
            "message": f"Configuração de DNS de '{adapter}' restaurada com sucesso: Modo {orig_mode.upper()}, Servidores: {orig_servers or ['Automático']}."
        }
    return {
        "success": False,
        "message": f"Falha na restauração do DNS: {msg}"
    }
