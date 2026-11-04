"""
Módulo SAFETY MANAGER - Gerenciador Central de Segurança do ALTUS PC OPTIMIZER.
Classifica operações, impede rotinas perigosas e valida autorizações centralmente.
"""
from enum import IntEnum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from src.utils.logger import app_logger
from src.core.permissions import is_admin

Tuple_Result = Tuple[bool, str]

class RiskLevel(IntEnum):
    LEVEL_1_SAFE = 1        # Seguro: Não destrutivo, sem alteração de configurações críticas
    LEVEL_2_CONTROLLED = 2  # Controlado: Requer confirmação explícita do usuário
    LEVEL_3_ADVANCED = 3    # Avançado: Ferramentas de sistema (SFC, DISM, Winsock)
    FORBIDDEN = 99          # Estritamente proibido: Destrutivo ou sem base técnica

@dataclass(frozen=True)
class OperationMetadata:
    op_id: str
    risk_level: RiskLevel
    requires_admin: bool
    description: str
    reversible: bool
    category: str

# Lista negra categórica de operações proibidas
FORBIDDEN_OPERATIONS: Dict[str, str] = {
    "REGISTRY_CLEANER": "Limpadores de registro causam instabilidade no Windows e não trazem ganhos de desempenho.",
    "DISABLE_DEFENDER": "Desativação de antivírus ou componentes de segurança expõe a máquina a malwares.",
    "DISABLE_FIREWALL": "Desativação do Firewall do Windows viola os padrões de segurança de rede.",
    "DISABLE_UAC": "Desativação do UAC elimina a barreira contra execução involuntária de binários.",
    "DISABLE_WINDOWS_UPDATE": "Desativação permanente de atualizações impede correções de vulnerabilidades críticas.",
    "DELETE_PREFETCH": "Exclusão do diretório Prefetch degrada o tempo de inicialização dos aplicativos.",
    "DELETE_PAGEFILE": "Remoção de arquivo de paginação pode causar falhas graves de memória (BSOD).",
    "DELETE_WINSXS_MANUAL": "Exclusão manual da pasta WinSxS destrói o repositório de componentes do Windows.",
    "DISM_RESETBASE": "O parâmetro /ResetBase remove a possibilidade de rollback de atualizações anteriores.",
    "PROCESS_PRIORITY_REALTIME": "A prioridade Realtime pode causar travamento de threads de teclado, mouse e kernel.",
    "MASS_SERVICE_DISABLE": "Desativação em massa de serviços do Windows quebra recursos fundamentais do sistema."
}

# Registro Central de Operações Autorizadas e suas Políticas de Risco
CENTRAL_OPERATION_REGISTRY: Dict[str, OperationMetadata] = {
    # Limpeza
    "TEMP_CLEANUP": OperationMetadata("TEMP_CLEANUP", RiskLevel.LEVEL_1_SAFE, False, "Limpeza de arquivos temporários do usuário e do sistema", False, "cleaning"),
    "ANALYZE_TEMP": OperationMetadata("ANALYZE_TEMP", RiskLevel.LEVEL_1_SAFE, False, "Análise de arquivos temporários", True, "cleaning"),
    "THUMBNAIL_CLEANUP": OperationMetadata("THUMBNAIL_CLEANUP", RiskLevel.LEVEL_1_SAFE, False, "Limpeza de cache de miniaturas (thumbnails)", False, "cleaning"),
    "WINDOWS_UPDATE_CLEANUP": OperationMetadata("WINDOWS_UPDATE_CLEANUP", RiskLevel.LEVEL_2_CONTROLLED, True, "Limpeza do cache de downloads do Windows Update", False, "cleaning"),
    "STORAGE_ANALYSIS": OperationMetadata("STORAGE_ANALYSIS", RiskLevel.LEVEL_1_SAFE, False, "Análise de ocupação de armazenamento", True, "cleaning"),
    
    # Rede
    "DNS_CACHE_FLUSH": OperationMetadata("DNS_CACHE_FLUSH", RiskLevel.LEVEL_1_SAFE, False, "Limpeza de cache DNS local", True, "network"),
    "APPLY_CUSTOM_DNS": OperationMetadata("APPLY_CUSTOM_DNS", RiskLevel.LEVEL_2_CONTROLLED, True, "Configuração de servidores DNS personalizados", True, "network"),
    "RESTORE_DNS": OperationMetadata("RESTORE_DNS", RiskLevel.LEVEL_2_CONTROLLED, True, "Restauração de configuração anterior de DNS", True, "network"),
    "REPAIR_NETWORK_DHCP": OperationMetadata("REPAIR_NETWORK_DHCP", RiskLevel.LEVEL_2_CONTROLLED, True, "Renovação de concessão DHCP de rede", True, "network"),
    "RESET_WINSOCK": OperationMetadata("RESET_WINSOCK", RiskLevel.LEVEL_3_ADVANCED, True, "Redefinição da pilha TCP/IP e catálogo Winsock", False, "network"),
    
    # Sistema e Discos
    "OPTIMIZE_VOLUME": OperationMetadata("OPTIMIZE_VOLUME", RiskLevel.LEVEL_2_CONTROLLED, True, "Otimização inteligente de volume (TRIM/Defrag)", False, "system"),
    "CHKDSK_SCAN": OperationMetadata("CHKDSK_SCAN", RiskLevel.LEVEL_2_CONTROLLED, True, "Verificação de integridade do sistema de arquivos (/scan)", True, "system"),
    "SFC_SCAN": OperationMetadata("SFC_SCAN", RiskLevel.LEVEL_3_ADVANCED, True, "Verificação e reparo de integridade de arquivos do Windows (SFC)", True, "system"),
    "DISM_RESTORE": OperationMetadata("DISM_RESTORE", RiskLevel.LEVEL_3_ADVANCED, True, "Reparo de imagem de componentes do Windows via DISM", True, "system"),
    "POWER_PLAN_SET": OperationMetadata("POWER_PLAN_SET", RiskLevel.LEVEL_2_CONTROLLED, False, "Alteração de plano de energia ativo", True, "system"),
    "POWER_PLAN_RESTORE": OperationMetadata("POWER_PLAN_RESTORE", RiskLevel.LEVEL_1_SAFE, False, "Restauração de plano de energia original", True, "system"),
    
    # Jogos e Inicialização
    "DISABLE_STARTUP_ENTRY": OperationMetadata("DISABLE_STARTUP_ENTRY", RiskLevel.LEVEL_2_CONTROLLED, False, "Desativação de inicializador de aplicativo", True, "gaming"),
    "ENABLE_STARTUP_ENTRY": OperationMetadata("ENABLE_STARTUP_ENTRY", RiskLevel.LEVEL_2_CONTROLLED, False, "Reativação de inicializador de aplicativo", True, "gaming"),
    "GAME_MODE_ENABLE": OperationMetadata("GAME_MODE_ENABLE", RiskLevel.LEVEL_2_CONTROLLED, False, "Ativação do perfil de alto desempenho para jogos", True, "gaming"),
    "GAME_MODE_DISABLE": OperationMetadata("GAME_MODE_DISABLE", RiskLevel.LEVEL_1_SAFE, False, "Desativação do perfil de jogos e restauração de energia", True, "gaming"),
    "PROCESS_PRIORITY_SET": OperationMetadata("PROCESS_PRIORITY_SET", RiskLevel.LEVEL_2_CONTROLLED, False, "Ajuste controlado de prioridade de processo (Acima do Normal/Alta)", True, "gaming"),
    
    # Operações de Recuperação e Ações Genéricas
    "ROLLBACK_OPERATION": OperationMetadata("ROLLBACK_OPERATION", RiskLevel.LEVEL_2_CONTROLLED, True, "Reversão automática de alterações de sistema", True, "recovery"),
    "CUSTOM_ACTION": OperationMetadata("CUSTOM_ACTION", RiskLevel.LEVEL_2_CONTROLLED, False, "Ação controlada de teste e manutenção", False, "system"),

    # Windows Background Control (Etapa 4)
    "ANALYZE_BACKGROUND_RESOURCES": OperationMetadata("ANALYZE_BACKGROUND_RESOURCES", RiskLevel.LEVEL_1_SAFE, False, "Análise de processos e consumo em segundo plano", True, "background"),
    "DETECT_WINDOWS_FEATURES": OperationMetadata("DETECT_WINDOWS_FEATURES", RiskLevel.LEVEL_1_SAFE, False, "Detecção de recursos do Windows, IA e Edge", True, "background"),
    "BEFORE_AFTER_SNAPSHOT": OperationMetadata("BEFORE_AFTER_SNAPSHOT", RiskLevel.LEVEL_1_SAFE, False, "Instantâneo de recursos antes/depois da otimização", True, "background"),
    "TOGGLE_COPILOT": OperationMetadata("TOGGLE_COPILOT", RiskLevel.LEVEL_2_CONTROLLED, False, "Controle de visibilidade e políticas do Microsoft Copilot", True, "background"),
    "TOGGLE_RECALL": OperationMetadata("TOGGLE_RECALL", RiskLevel.LEVEL_3_ADVANCED, True, "Configuração de captura e recurso do Windows Recall", True, "background"),
    "CONFIGURE_EDGE_BACKGROUND": OperationMetadata("CONFIGURE_EDGE_BACKGROUND", RiskLevel.LEVEL_2_CONTROLLED, False, "Controle de Startup Boost e extensões em segundo plano do Edge", True, "background"),
    "CONFIGURE_TELEMETRY": OperationMetadata("CONFIGURE_TELEMETRY", RiskLevel.LEVEL_2_CONTROLLED, True, "Ajuste de nível de telemetria e coleta opcional de diagnóstico", True, "background"),
    "CONFIGURE_WIDGETS": OperationMetadata("CONFIGURE_WIDGETS", RiskLevel.LEVEL_2_CONTROLLED, False, "Controle de Widgets, notícias e sugestões promocionais do Windows", True, "background"),
    "CONFIGURE_GAME_DVR": OperationMetadata("CONFIGURE_GAME_DVR", RiskLevel.LEVEL_2_CONTROLLED, False, "Controle da captura contínua e gravação em segundo plano do Xbox", True, "background"),
    "CONFIGURE_SEARCH_INDEXING": OperationMetadata("CONFIGURE_SEARCH_INDEXING", RiskLevel.LEVEL_2_CONTROLLED, False, "Exclusão inteligente de pastas de desenvolvimento da indexação", True, "background"),
    "CONFIGURE_DELIVERY_OPTIMIZATION": OperationMetadata("CONFIGURE_DELIVERY_OPTIMIZATION", RiskLevel.LEVEL_2_CONTROLLED, True, "Controle do modo de entrega P2P do Delivery Optimization", True, "background"),
    "CONFIGURE_BACKGROUND_APPS": OperationMetadata("CONFIGURE_BACKGROUND_APPS", RiskLevel.LEVEL_2_CONTROLLED, False, "Gerenciamento de permissão de aplicativos em segundo plano", True, "background"),
    "CONFIGURE_OPTIONAL_SERVICE": OperationMetadata("CONFIGURE_OPTIONAL_SERVICE", RiskLevel.LEVEL_3_ADVANCED, True, "Configuração controlada de inicialização de serviço opcional documentado", True, "background"),
    "APPLY_OPTIMIZATION_PROFILE": OperationMetadata("APPLY_OPTIMIZATION_PROFILE", RiskLevel.LEVEL_2_CONTROLLED, False, "Aplicação de perfil de otimização de segundo plano com reversão", True, "background"),
    "ROLLBACK_BACKGROUND_SETTING": OperationMetadata("ROLLBACK_BACKGROUND_SETTING", RiskLevel.LEVEL_2_CONTROLLED, False, "Restauração de configuração de segundo plano pelo ledger", True, "background")
}

class SafetyManager:
    """Núcleo central de validação e controle de riscos."""

    def __init__(self):
        self._execution_history: List[Dict[str, Any]] = []

    def is_operation_forbidden(self, operation_id: str) -> Tuple_Result:
        """Verifica se uma operação pertence à lista negra irrevogável."""
        op_key = operation_id.upper().strip()
        if op_key in FORBIDDEN_OPERATIONS:
            reason = FORBIDDEN_OPERATIONS[op_key]
            app_logger.warning(f"Operação proibida bloqueada: {op_key} - Motivo: {reason}")
            return True, reason
        return False, ""

    def get_operation_metadata(self, operation_id: str) -> Optional[OperationMetadata]:
        """Obtém os metadados oficiais da operação do registro central."""
        return CENTRAL_OPERATION_REGISTRY.get(operation_id.upper().strip())

    def validate_and_authorize(
        self,
        op_id: str,
        risk_level: Optional[RiskLevel] = None,
        requires_admin: Optional[bool] = None,
        user_confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Valida se a operação é permitida pelas regras de segurança.
        Não confia exclusivamente no nível ou privilégio informado pelo chamador:
        consulta prioritariamente o registro central oficial.
        """
        op_key = op_id.upper().strip()

        # 1. Checagem de proibição absoluta
        forbidden, reason = self.is_operation_forbidden(op_key)
        if forbidden:
            return {
                "authorized": False,
                "reason": f"OPERAÇÃO BLOQUEADA PELO SAFETY MANAGER: {reason}",
                "level": RiskLevel.FORBIDDEN
            }

        # 2. Resolução das políticas centrais
        meta = self.get_operation_metadata(op_key)
        if meta:
            enforced_risk = meta.risk_level
            enforced_admin = meta.requires_admin
        else:
            app_logger.warning(f"Operação '{op_key}' não catalogada no registro central. Aplicando regras restritivas padrão.")
            enforced_risk = risk_level if risk_level is not None else RiskLevel.LEVEL_2_CONTROLLED
            enforced_admin = requires_admin if requires_admin is not None else False

        # 3. Avaliação simultânea de privilégio administrativo e confirmação
        needs_admin_elevation = enforced_admin and not is_admin()
        needs_user_conf = (
            enforced_risk in (RiskLevel.LEVEL_2_CONTROLLED, RiskLevel.LEVEL_3_ADVANCED)
            and not user_confirmed
        )

        if needs_admin_elevation or needs_user_conf:
            reasons = []
            if needs_admin_elevation:
                reasons.append(f"A operação '{op_key}' requer privilégios de Administrador (UAC).")
            if needs_user_conf:
                reasons.append(f"A operação '{op_key}' requer confirmação explícita do usuário antes da execução.")

            return {
                "authorized": False,
                "reason": " | ".join(reasons),
                "level": enforced_risk,
                "needs_elevation": needs_admin_elevation,
                "needs_confirmation": needs_user_conf
            }

        # 4. Operação autorizada
        app_logger.info(f"Operação autorizada pelo Safety Manager: {op_key} (Nível {enforced_risk.name}, Admin={enforced_admin})")
        return {
            "authorized": True,
            "reason": "Autorizado com sucesso pelas políticas de segurança.",
            "level": enforced_risk,
            "requires_admin": enforced_admin
        }

safety_manager = SafetyManager()
