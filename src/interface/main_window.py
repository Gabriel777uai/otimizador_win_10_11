"""
Janela Principal da Aplicação - ALTUS PC OPTIMIZER.
Gerencia a navegação lateral com 12 seções profissionais e a área de visualização central.
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

from src.core.permissions import is_admin
from src.interface.dashboard import DashboardPage
from src.interface.cleaning_page import CleaningPage
from src.interface.gaming_page import GamingPage
from src.interface.performance_lab_page import PerformanceLabPage
from src.interface.thermal_guard_page import ThermalGuardPage
from src.interface.windows_background_page import WindowsBackgroundPage
from src.interface.network_page import NetworkPage
from src.interface.system_page import SystemPage
from src.interface.startup_page import StartupPage
from src.interface.auto_recovery_page import AutoRecoveryPage
from src.interface.reliability_page import ReliabilityPage
from src.interface.reports_page import ReportsPage
from src.interface.settings_page import SettingsPage
from src.resources.styles.theme import DARK_THEME_QSS

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALTUS PC OPTIMIZER — Sistema Profissional de Manutenção do Windows")
        self.resize(1240, 780)
        self.setMinimumSize(1000, 660)

        self._load_stylesheet()
        self._init_ui()

    def _load_stylesheet(self):
        # Aplica o tema garantido
        self.setStyleSheet(DARK_THEME_QSS)

        # Se houver arquivo externo, permite sobreposição
        try:
            qss_path = Path(__file__).resolve().parent.parent / "resources" / "styles" / "dark_theme.qss"
            if qss_path.exists():
                with open(qss_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip():
                        self.setStyleSheet(content)
        except Exception:
            pass

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. MENU LATERAL (SIDEBAR)
        sidebar = QWidget()
        sidebar.setObjectName("SidebarWidget")
        sidebar.setFixedWidth(250)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 14, 12, 12)
        side_layout.setSpacing(6)

        # Header da Sidebar com Logotipo
        logo_box = QHBoxLayout()
        logo_box.setSpacing(10)

        logo_path = Path(__file__).resolve().parent.parent / "resources" / "icons" / "logo_64.png"
        lbl_logo = QLabel()
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            self.setWindowIcon(QIcon(str(logo_path)))
        lbl_logo.setStyleSheet("border: none;")
        logo_box.addWidget(lbl_logo)

        brand_text_box = QVBoxLayout()
        brand_text_box.setSpacing(1)
        lbl_app = QLabel("ALTUS PC")
        lbl_app.setObjectName("AppTitleLabel")
        lbl_sub = QLabel("OPTIMIZER PRO")
        lbl_sub.setObjectName("AppSubtitleLabel")
        brand_text_box.addWidget(lbl_app)
        brand_text_box.addWidget(lbl_sub)
        logo_box.addLayout(brand_text_box)
        logo_box.addStretch()

        side_layout.addLayout(logo_box)
        side_layout.addSpacing(6)

        # Container com ScrollArea para os Botões de Navegação (impede quebras e transbordamentos)
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        nav_scroll.setStyleSheet("background: transparent; border: none;")

        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(3)

        self.nav_buttons = []
        nav_items = [
            ("📊 Dashboard", 0),
            ("🧹 Limpeza Inteligente", 1),
            ("🎮 Otimização para Jogos", 2),
            ("📈 Performance Lab", 3),
            ("🔥 Thermal Guard", 4),
            ("💻 Background Control", 5),
            ("🌐 Otimização de Rede", 6),
            ("⚙️ Desempenho do Sistema", 7),
            ("🚀 Inicialização do Windows", 8),
            ("🛡️ Auto Recovery Center", 9),
            ("🩺 Confiabilidade do SO", 10),
            ("📋 Relatórios e Histórico", 11),
            ("🔧 Configurações", 12)
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setProperty("class", "SidebarButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(34)
            btn.clicked.connect(lambda checked, idx=index: self._switch_page(idx))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        nav_layout.addStretch()
        nav_scroll.setWidget(nav_container)
        side_layout.addWidget(nav_scroll)

        # Status de Privilégio no rodapé da Sidebar
        admin_status = "Administrador Ativo" if is_admin() else "Modo Padrão (Sem Admin)"
        admin_color = "#00e676" if is_admin() else "#8da4c4"
        lbl_admin = QLabel(f"• {admin_status}")
        lbl_admin.setStyleSheet(f"color: {admin_color}; font-size: 11px; font-weight: 600; padding: 6px 4px 2px 4px;")
        side_layout.addWidget(lbl_admin)

        main_layout.addWidget(sidebar)

        # 2. ÁREA CENTRAL (STACKED WIDGET COM AS 13 PÁGINAS ROLÁVEIS)
        self.pages_stack = QStackedWidget()

        self.page_dashboard = DashboardPage()
        self.page_cleaning = CleaningPage()
        self.page_gaming = GamingPage()
        self.page_performance_lab = PerformanceLabPage()
        self.page_thermal = ThermalGuardPage()
        self.page_background = WindowsBackgroundPage()
        self.page_network = NetworkPage()
        self.page_system = SystemPage()
        self.page_startup = StartupPage()
        self.page_recovery = AutoRecoveryPage()
        self.page_reliability = ReliabilityPage()
        self.page_reports = ReportsPage()
        self.page_settings = SettingsPage()

        self.pages_stack.addWidget(self._create_scrollable_page(self.page_dashboard))
        self.pages_stack.addWidget(self._create_scrollable_page(self.page_cleaning))
        self.pages_stack.addWidget(self._create_scrollable_page(self.page_gaming))
        self.pages_stack.addWidget(self._create_scrollable_page(self.page_performance_lab))
        self.pages_stack.addWidget(self._create_scrollable_page(self.page_thermal))
        self.pages_stack.addWidget(self._create_scrollable_page(self.page_background))
        self.pages_stack.addWidget(self._create_scrollable_page(self.page_network))
        self.pages_stack.addWidget(self._create_scrollable_page(self.page_system))
        self.pages_stack.addWidget(self._create_scrollable_page(self.page_startup))
        self.pages_stack.addWidget(self._create_scrollable_page(self.page_recovery))
        self.pages_stack.addWidget(self._create_scrollable_page(self.page_reliability))
        self.pages_stack.addWidget(self._create_scrollable_page(self.page_reports))
        self.pages_stack.addWidget(self._create_scrollable_page(self.page_settings))

        main_layout.addWidget(self.pages_stack)

        # Define página inicial (Dashboard)
        self._switch_page(0)

    def _create_scrollable_page(self, page_widget: QWidget) -> QScrollArea:
        """Envolve uma página em uma QScrollArea sem borda, garantindo responsividade total."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        scroll.setWidget(page_widget)
        return scroll

    def _switch_page(self, index: int):
        self.pages_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
