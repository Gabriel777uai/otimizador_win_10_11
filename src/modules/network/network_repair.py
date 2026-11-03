"""
Módulo de Reparação e Diagnóstico de Falhas de Rede.
Oferece renovação de concessão DHCP e redefinição de catálogo Winsock como último recurso.
Suporta acompanhamento de progresso real.
"""
from typing import Dict, Any, Optional, Callable
from src.utils.logger import app_logger
from src.utils.command_runner import run_command
from src.core.safety_manager import safety_manager, RiskLevel

def renew_ip_lease(
    user_confirmed: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Executa liberação e renovação da concessão IP via DHCP.
    Avisa o usuário que haverá perda momentânea de conexão.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="REPAIR_NETWORK_DHCP",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    if progress_callback:
        progress_callback(20, "Liberando concessão de IP atual (ipconfig /release)...")
    app_logger.info("Executando ipconfig /release e ipconfig /renew...")
    run_command(["ipconfig", "/release"], timeout=20)

    if progress_callback:
        progress_callback(60, "Solicitando nova concessão IP ao servidor DHCP (ipconfig /renew)...")
    rc, out, err = run_command(["ipconfig", "/renew"], timeout=35)

    if progress_callback:
        progress_callback(100, "Concluído.")

    if rc == 0:
        return {"success": True, "message": "Concessão IP renovada com sucesso via DHCP."}
    return {"success": False, "message": f"Erro na renovação do IP: {err or out}"}

def reset_winsock_catalog(
    user_confirmed: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Redefine o catálogo de sockets Winsock do Windows para o padrão de fábrica.
    Ação Avançada (Nível 3) - Exige reinicialização da máquina para efeito completo.
    """
    auth = safety_manager.validate_and_authorize(
        op_id="RESET_WINSOCK",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    if progress_callback:
        progress_callback(30, "Redefinindo catálogo de sockets Winsock (Nível 3)...")
    app_logger.warning("Executando netsh winsock reset (Nível 3)...")
    rc, out, err = run_command(["netsh", "winsock", "reset"], timeout=20)

    if progress_callback:
        progress_callback(100, "Concluído.")

    if rc == 0:
        return {
            "success": True,
            "requires_reboot": True,
            "message": "Catálogo Winsock redefinido com sucesso. É necessário reiniciar o computador para concluir o reparo de rede."
        }
    return {"success": False, "message": f"Falha ao redefinir Winsock: {err or out}"}
