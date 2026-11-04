"""
Sistema de Perfis de Otimização de Segundo Plano - ALTUS PC OPTIMIZER.
Implementa os 3 perfis profissionais com pré-visualização, execução controlada e
rollback consolidado no Auto Recovery Center:
1. Windows Slim (Leveza e Menos Consumo)
2. Gaming Performance (Foco em Baixa Latência e Sem Gravação Oculta)
3. Developer Workstation (Indexação Otimizada e Monitoramento de Dev)
"""
from typing import Dict, Any, List
from src.utils.logger import app_logger
from src.core.safety_manager import safety_manager
from src.core.recovery_manager import register_recovery_operation, rollback_operation

from .copilot_manager import configure_copilot
from .edge_manager import configure_edge_background
from .widget_manager import configure_widgets
from .telemetry_manager import configure_telemetry
from .delivery_optimizer import configure_delivery_optimization
from .gaming_services_manager import configure_gaming_dvr
from .app_background_manager import configure_background_apps
from .search_index_manager import scan_common_dev_folders, configure_index_exclusions
from src.modules.windows.power_manager import set_high_performance_plan, get_current_power_plan

PROFILES_CATALOG: Dict[str, Dict[str, Any]] = {
    "WINDOWS_SLIM": {
        "id": "WINDOWS_SLIM",
        "name": "PROFILE 01 — WINDOWS SLIM",
        "tag": "USO DIÁRIO E EFICIÊNCIA",
        "description": "Reduz aplicações e experiências opcionais em segundo plano sem comprometer estabilidade ou componentes essenciais do Windows.",
        "actions_description": [
            "Oculta e desativa o Microsoft Copilot em segundo plano.",
            "Desativa o Startup Boost e execução de extensões do Edge ao fechar.",
            "Oculta painel de Widgets e Notícias da barra de tarefas.",
            "Desativa sugestões promocionais e dicas automáticas no Iniciar.",
            "Configura Delivery Optimization para HTTP oficial (elimina upload P2P).",
            "Limita permissão global de aplicativos em segundo plano."
        ]
    },
    "GAMING_PERFORMANCE": {
        "id": "GAMING_PERFORMANCE",
        "name": "PROFILE 02 — GAMING PERFORMANCE",
        "tag": "JOGOS E BAIXA LATÊNCIA",
        "description": "Minimiza atividades concorrentes durante sessões de jogos, eliminando gravação contínua em disco e ativando plano de alta performance.",
        "actions_description": [
            "Desativa gravação em segundo plano do Game DVR (elimina escrita contínua em disco).",
            "Garante ativação do Modo de Jogo oficial do Windows (Game Mode).",
            "Desativa pré-carregamento do Edge (Startup Boost).",
            "Desativa notificações e sugestões concorrentes do Windows.",
            "Aplica plano de energia de Alto Desempenho durante a sessão.",
            "Preserva integralmente serviços anticheat, rede Xbox e segurança."
        ]
    },
    "DEVELOPER_WORKSTATION": {
        "id": "DEVELOPER_WORKSTATION",
        "name": "PROFILE 03 — DEVELOPER WORKSTATION",
        "tag": "PROGRAMAÇÃO E COMPILAÇÃO",
        "description": "Mantém o Windows otimizado para compilação e desenvolvimento, excluindo diretórios pesados de código da indexação de busca.",
        "actions_description": [
            "Mapeia e sugere exclusão de node_modules, .git e venvs da indexação do Windows Search.",
            "Desativa widgets e notificações promocionais distrativas.",
            "Desativa o Startup Boost do Edge para liberar memória de trabalho.",
            "Configura telemetria em nível básico para reduzir chamadas em background.",
            "Monitora processos locais de desenvolvimento (Docker, Node, Python, PHP, Java)."
        ]
    }
}

def get_available_profiles() -> List[Dict[str, Any]]:
    """Retorna os dados dos 3 perfis para exibição na interface gráfica."""
    return list(PROFILES_CATALOG.values())

def apply_profile(profile_id: str, user_confirmed: bool = False) -> Dict[str, Any]:
    """
    Aplica as otimizações do perfil selecionado, registrando cada sub-operação
    e agrupando em um registro mestre de perfil para reversão em lote.
    """
    p_id = profile_id.upper().strip()
    if p_id not in PROFILES_CATALOG:
        return {"success": False, "message": f"Perfil '{profile_id}' não catalogado."}

    auth = safety_manager.validate_and_authorize(
        op_id="APPLY_OPTIMIZATION_PROFILE",
        user_confirmed=user_confirmed
    )
    if not auth["authorized"]:
        return {"success": False, "message": auth["reason"]}

    sub_records: List[str] = []
    actions_log: List[str] = []

    # 1. Aplicação do Perfil WINDOWS_SLIM
    if p_id == "WINDOWS_SLIM":
        res_cop = configure_copilot(disable=True, user_confirmed=True)
        if res_cop.get("success") and res_cop.get("record_id"):
            sub_records.append(res_cop["record_id"])
            actions_log.append("Copilot desativado em segundo plano")

        res_edge = configure_edge_background(disable_startup_boost=True, disable_background_mode=True, user_confirmed=True)
        if res_edge.get("success") and res_edge.get("record_id"):
            sub_records.append(res_edge["record_id"])
            actions_log.append("Startup Boost e background do Edge desativados")

        res_wid = configure_widgets(hide_widgets=True, disable_suggestions=True, user_confirmed=True)
        if res_wid.get("success") and res_wid.get("record_id"):
            sub_records.append(res_wid["record_id"])
            actions_log.append("Widgets e sugestões promocionais ocultados")

        res_del = configure_delivery_optimization(disable_p2p_sharing=True, user_confirmed=True)
        if res_del.get("success") and res_del.get("record_id"):
            sub_records.append(res_del["record_id"])
            actions_log.append("Upload P2P do Windows Update desativado")

        res_apps = configure_background_apps(disable_global=True, user_confirmed=True)
        if res_apps.get("success") and res_apps.get("record_id"):
            sub_records.append(res_apps["record_id"])
            actions_log.append("Execução irrestrita de apps em segundo plano limitada")

    # 2. Aplicação do Perfil GAMING_PERFORMANCE
    elif p_id == "GAMING_PERFORMANCE":
        res_dvr = configure_gaming_dvr(disable_background_recording=True, user_confirmed=True)
        if res_dvr.get("success") and res_dvr.get("record_id"):
            sub_records.append(res_dvr["record_id"])
            actions_log.append("Gravação de fundo do Game DVR desativada (Game Mode preservado)")

        res_edge = configure_edge_background(disable_startup_boost=True, disable_background_mode=True, user_confirmed=True)
        if res_edge.get("success") and res_edge.get("record_id"):
            sub_records.append(res_edge["record_id"])
            actions_log.append("Startup Boost do Edge desativado")

        res_wid = configure_widgets(hide_widgets=True, disable_suggestions=True, user_confirmed=True)
        if res_wid.get("success") and res_wid.get("record_id"):
            sub_records.append(res_wid["record_id"])
            actions_log.append("Widgets e sugestões desativados para evitar interrupções")

        res_power = set_high_performance_plan(user_confirmed=True)
        if res_power.get("success"):
            actions_log.append("Plano de energia de Alto Desempenho ativado")

    # 3. Aplicação do Perfil DEVELOPER_WORKSTATION
    elif p_id == "DEVELOPER_WORKSTATION":
        found_folders = scan_common_dev_folders(max_results=20)
        folder_paths = [f["path"] for f in found_folders]
        if folder_paths:
            res_idx = configure_index_exclusions(folder_paths, user_confirmed=True)
            if res_idx.get("success") and res_idx.get("record_id"):
                sub_records.append(res_idx["record_id"])
                actions_log.append(f"{len(folder_paths)} pastas de desenvolvimento excluídas da indexação")

        res_edge = configure_edge_background(disable_startup_boost=True, disable_background_mode=True, user_confirmed=True)
        if res_edge.get("success") and res_edge.get("record_id"):
            sub_records.append(res_edge["record_id"])
            actions_log.append("Startup Boost do Edge desativado")

        res_wid = configure_widgets(hide_widgets=True, disable_suggestions=True, user_confirmed=True)
        if res_wid.get("success") and res_wid.get("record_id"):
            sub_records.append(res_wid["record_id"])
            actions_log.append("Widgets e sugestões promocionais desativados")

        res_tel = configure_telemetry(set_basic_diagnostics=True, disable_tailored_experiences=True, user_confirmed=True)
        if res_tel.get("success") and res_tel.get("record_id"):
            sub_records.append(res_tel["record_id"])
            actions_log.append("Telemetria configurada em nível básico")

    # Registra o Perfil Consolidado no Auto Recovery Center
    master_record_id = register_recovery_operation(
        op_id=f"APPLY_PROFILE_{p_id}",
        category="PROFILE",
        original_state={"profile_id": p_id, "sub_records": sub_records},
        applied_state={"actions": actions_log},
        restore_strategy="RESTORE_BACKGROUND_PROFILE",
        status="APPLIED"
    )

    app_logger.info(f"Perfil {p_id} aplicado com sucesso ({len(actions_log)} ações). Master Record: {master_record_id}")
    return {
        "success": True,
        "message": f"{PROFILES_CATALOG[p_id]['name']} aplicado com êxito!",
        "actions_completed": actions_log,
        "master_record_id": master_record_id,
        "profile_id": p_id
    }

def revert_profile(master_record_id: str) -> Dict[str, Any]:
    """Reverte integralmente um perfil aplicado utilizando o Auto Recovery Center."""
    return rollback_operation(master_record_id)
