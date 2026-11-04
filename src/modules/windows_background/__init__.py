"""
Módulo WINDOWS BACKGROUND CONTROL - ALTUS PC OPTIMIZER.
Controle inteligente de processos, recursos de IA, serviços e otimização avançada do Windows 10/11.
"""
from .feature_detector import detect_all_windows_features, WindowsFeatureStatus
from .background_analyzer import analyze_background_processes, BackgroundProcessInfo
from .copilot_manager import get_copilot_status, configure_copilot
from .recall_manager import get_recall_status, configure_recall
from .edge_manager import get_edge_status, configure_edge_background
from .telemetry_manager import get_telemetry_status, configure_telemetry
from .widget_manager import get_widget_status, configure_widgets
from .gaming_services_manager import get_gaming_dvr_status, configure_gaming_dvr
from .search_index_manager import get_search_index_status, scan_common_dev_folders, configure_index_exclusions
from .delivery_optimizer import get_delivery_optimization_status, configure_delivery_optimization
from .app_background_manager import get_background_apps_status, configure_background_apps
from .service_analyzer import analyze_windows_services, ServiceCategory, configure_optional_service
from .optimization_profiles import get_available_profiles, apply_profile, revert_profile
from .before_after_analyzer import take_system_snapshot, compare_snapshots
from .background_recovery import get_background_recovery_history, restore_background_operation
