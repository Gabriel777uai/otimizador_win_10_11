"""
Módulo de Integridade e Reparação de Arquivos do Windows (SFC e DISM).
Operações de Nível 3 (Avançado):
- Exigem confirmação explícita e privilégios administrativos.
- NUNCA executam /ResetBase (bloqueado pelo Safety Manager).
- Suporta barra indeterminada e acompanhamento de etapas.
"""
from typing import Dict, Any, Callable, Optional
from src.utils.logger import app_logger
from src.utils.command_runner import run_command
from src.core.safety_manager import safety_manager, RiskLevel

def run_sfc_scan(
    user_confirmed: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """Executa a verificação e correção de arquivos protegidos do Windows (sfc /scannow)."""
    auth = safety_manager.validate_and_authorize(
        op_id="SFC_SCAN",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    if progress_callback:
        # Barra indeterminada enquanto o utilitário nativo SFC processa os componentes
        progress_callback(-1, "Executando sfc.exe /scannow (Verificação de arquivos protegidos)...")

    app_logger.info("Iniciando sfc /scannow...")
    rc, out, err = run_command(["sfc.exe", "/scannow"], timeout=900)

    if progress_callback:
        progress_callback(100, "Varredura SFC finalizada.")

    msg = out if out.strip() else err
    repaired = "encontrou arquivos corrompidos e os reparou com êxito" in msg.lower() or "repaired" in msg.lower()
    no_violations = "não encontrou nenhuma violação" in msg.lower() or "did not find any integrity violations" in msg.lower()
    success = rc == 0 or repaired or no_violations

    return {
        "success": success,
        "return_code": rc,
        "repaired": repaired,
        "no_violations": no_violations,
        "output": msg,
        "message": "Arquivos do sistema verificados e íntegros." if no_violations else ("Arquivos corrompidos reparados com sucesso." if repaired else msg[:200])
    }

def run_dism_scan(
    mode: str = "ScanHealth",
    user_confirmed: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Executa verificação ou reparo da imagem do Windows via DISM.
    Modos permitidos: CheckHealth, ScanHealth, RestoreHealth.
    /ResetBase é terminantemente proibido.
    """
    if mode not in ("CheckHealth", "ScanHealth", "RestoreHealth"):
        return {"success": False, "message": f"Modo DISM não autorizado: {mode}"}

    auth = safety_manager.validate_and_authorize(
        op_id="DISM_RESTORE" if mode == "RestoreHealth" else "CUSTOM_ACTION",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    if progress_callback:
        progress_callback(-1, f"Executando DISM /{mode} no repositório de componentes...")

    app_logger.info(f"Iniciando DISM /Online /Cleanup-Image /{mode}...")
    cmd = ["DISM.exe", "/Online", "/Cleanup-Image", f"/{mode}"]
    rc, out, err = run_command(cmd, timeout=900)

    if progress_callback:
        progress_callback(100, "Operação DISM concluída.")

    msg = out if out.strip() else err
    success = rc == 0

    return {
        "success": success,
        "return_code": rc,
        "mode": mode,
        "output": msg,
        "message": f"DISM /{mode} concluído com sucesso." if success else f"DISM falhou: {err or out[:200]}"
    }
