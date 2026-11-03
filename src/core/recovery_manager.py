"""
AUTO RECOVERY CENTER - Gerenciador Central de Recuperação e Rollback do ALTUS PC OPTIMIZER.
Mantém o registro central (recovery ledger) de todas as modificações no sistema,
oferece estratégias automatizadas de reversão para DNS, Energia, Inicialização e Processos,
e detecta operações interrompidas na inicialização do aplicativo.
"""
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.utils.logger import app_logger, get_app_dir
from src.utils.command_runner import run_command
from src.core.permissions import is_admin

LEDGER_FILENAME = "recovery_ledger.json"

def get_backups_dir() -> Path:
    bdir = get_app_dir() / "Backups"
    bdir.mkdir(parents=True, exist_ok=True)
    return bdir

def get_ledger_path() -> Path:
    return get_backups_dir() / LEDGER_FILENAME

def create_system_restore_point(description: str = "Ponto Altus PC Optimizer") -> Dict[str, Any]:
    """Cria um ponto de restauração oficial no Windows via PowerShell."""
    if not is_admin():
        return {
            "success": False,
            "message": "A criação de ponto de restauração exige privilégios de Administrador."
        }

    app_logger.info(f"Criando Ponto de Restauração: {description}")
    cmd = [
        "powershell", "-NoProfile", "-Command",
        f'Checkpoint-Computer -Description "{description}" -RestorePointType "MODIFY_SETTINGS" -ErrorAction Stop'
    ]

    rc, out, err = run_command(cmd, timeout=90)
    if rc == 0:
        return {
            "success": True,
            "message": "Ponto de restauração do sistema criado com sucesso."
        }
    else:
        app_logger.warning(f"Falha ao criar ponto de restauração: {err or out}")
        return {
            "success": False,
            "message": f"Não foi possível criar o ponto de restauração: {err or out or 'Proteção de sistema desativada'}"
        }

def load_ledger() -> List[Dict[str, Any]]:
    """Carrega o livro-razão de operações recuperáveis."""
    lp = get_ledger_path()
    if not lp.exists():
        return []
    try:
        data = json.loads(lp.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as e:
        app_logger.warning(f"Erro ao ler ledger de recuperação: {e}")
        return []

def save_ledger(records: List[Dict[str, Any]]):
    """Grava o livro-razão de operações recuperáveis."""
    try:
        lp = get_ledger_path()
        lp.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        app_logger.error(f"Erro ao salvar ledger de recuperação: {e}")

def register_recovery_operation(
    op_id: str,
    category: str,
    original_state: Dict[str, Any],
    applied_state: Dict[str, Any],
    restore_strategy: str,
    status: str = "IN_PROGRESS"
) -> str:
    """
    Registra formalmente uma modificação de sistema no livro-razão de recuperação.
    Retorna o record_id único gerado.
    """
    record_id = f"rec_{category.lower()}_{int(time.time() * 1000)}"
    record = {
        "record_id": record_id,
        "op_id": op_id,
        "category": category,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "original_state": original_state,
        "applied_state": applied_state,
        "restore_strategy": restore_strategy,
        "status": status  # IN_PROGRESS, APPLIED, ROLLED_BACK, FAILED
    }

    records = load_ledger()
    records.insert(0, record)
    save_ledger(records)
    app_logger.info(f"Operação registrada no Auto Recovery Center: {record_id} ({category})")
    return record_id

def update_operation_status(record_id: str, new_status: str, error_message: str = ""):
    """Atualiza o status de uma operação no livro-razão."""
    records = load_ledger()
    for r in records:
        if r.get("record_id") == record_id:
            r["status"] = new_status
            if error_message:
                r["error_message"] = error_message
            break
    save_ledger(records)

def rollback_operation(record_id: str) -> Dict[str, Any]:
    """
    Executa a estratégia de rollback correspondente para reverter uma modificação anterior.
    """
    records = load_ledger()
    record = None
    for r in records:
        if r.get("record_id") == record_id:
            record = r
            break

    if not record:
        return {"success": False, "message": f"Registro de recuperação '{record_id}' não localizado."}

    strategy = record.get("restore_strategy")
    orig = record.get("original_state", {})
    app_logger.info(f"Executando rollback de {record_id} via estratégia '{strategy}'...")

    # 1. Estratégia de Restauração de DNS
    if strategy == "RESTORE_DNS":
        from src.modules.network.dns_optimizer import _apply_dns_state
        adapter = orig.get("adapter_name") or orig.get("adapter", "Ethernet")
        mode = orig.get("mode", "dhcp")
        servers = orig.get("dns_servers", [])
        ok, msg = _apply_dns_state(adapter, mode, servers)
        if ok:
            update_operation_status(record_id, "ROLLED_BACK")
            return {"success": True, "message": f"DNS da interface '{adapter}' revertido com sucesso para {mode.upper()}."}
        return {"success": False, "message": msg}

    # 2. Estratégia de Restauração de Plano de Energia
    elif strategy == "RESTORE_POWER_PLAN":
        guid = orig.get("power_plan_guid")
        if guid:
            rc, out, err = run_command(["powercfg", "/setactive", guid], timeout=10)
            if rc == 0:
                update_operation_status(record_id, "ROLLED_BACK")
                return {"success": True, "message": f"Plano de energia original ({guid}) restaurado com sucesso."}
            return {"success": False, "message": err or out or "Falha ao ativar plano de energia."}
        return {"success": False, "message": "GUID do plano original não informado."}

    # 3. Estratégia de Reativação de Inicializador
    elif strategy == "RESTORE_STARTUP_ENTRY":
        from src.modules.gaming.startup_optimizer import enable_startup_entry
        res = enable_startup_entry(orig, user_confirmed=True)
        if res.get("success"):
            update_operation_status(record_id, "ROLLED_BACK")
        return res

    return {"success": False, "message": f"Estratégia de rollback '{strategy}' não suportada ou não reversível."}

def check_and_recover_interrupted_operations() -> List[Dict[str, Any]]:
    """
    Executado na inicialização do aplicativo:
    Verifica se há operações que permaneceram com status 'IN_PROGRESS' devido a encerramento súbito
    e tenta executar o rollback seguro.
    """
    records = load_ledger()
    recovered = []
    has_changes = False

    for r in records:
        if r.get("status") == "IN_PROGRESS":
            app_logger.warning(f"Operação interrompida detectada no startup: {r['record_id']} ({r.get('restore_strategy')}). Tentando rollback seguro...")
            rb_res = rollback_operation(r["record_id"])
            if rb_res.get("success"):
                r["status"] = "ROLLED_BACK_ON_STARTUP"
                recovered.append(r)
                has_changes = True
            else:
                r["status"] = "RECOVERY_FAILED_ON_STARTUP"
                has_changes = True

    if has_changes:
        save_ledger(records)

    return recovered

# Compatibilidade retroativa de backups simples
def save_state_backup(category: str, data: Dict[str, Any]) -> str:
    """Salva backup em arquivo JSON versionado e registra no ledger."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_name = f"{category}_{timestamp}.json"
    target_path = get_backups_dir() / file_name

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": timestamp,
                "category": category,
                "data": data
            }, f, indent=2, ensure_ascii=False)
        
        # Registra também no Auto Recovery Ledger
        register_recovery_operation(
            op_id=f"APPLY_{category.upper()}",
            category=category,
            original_state=data,
            applied_state={},
            restore_strategy=f"RESTORE_{category.upper()}",
            status="APPLIED"
        )
        return str(target_path)
    except Exception as e:
        app_logger.error(f"Erro ao salvar backup: {e}")
        return ""

def load_latest_backup(category: str) -> Optional[Dict[str, Any]]:
    """Carrega o backup mais recente de uma determinada categoria."""
    bdir = get_backups_dir()
    files = sorted(bdir.glob(f"{category}_*.json"), reverse=True)
    if not files:
        return None

    try:
        with open(files[0], "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        app_logger.error(f"Erro ao ler backup {files[0]}: {e}")
        return None
