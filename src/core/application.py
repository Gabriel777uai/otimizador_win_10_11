"""
Classe principal da aplicação ALTUS PC OPTIMIZER.
Configura QApplication, Splash Screen profissional e ciclo de vida do software.
"""
import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from src.interface.main_window import MainWindow
from src.interface.splash_screen import AltusSplashScreen
from src.utils.logger import app_logger

class AltusApplication:
    def __init__(self):
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self.app = QApplication(sys.argv)
        self.app.setApplicationName("ALTUS PC OPTIMIZER")
        self.app.setOrganizationName("AltusSoftware")

        # Inicializa Splash Screen
        self.splash = AltusSplashScreen()
        self.splash.show()
        self.app.processEvents()

        # Etapas de inicialização rápida
        self.splash.set_progress(30, "Carregando módulos de sistema...")
        self.app.processEvents()

        self.splash.set_progress(60, "Configurando mecanismos de segurança...")
        self.app.processEvents()

        # FASE 6: Auto Recovery Check no início da aplicação
        from src.core.recovery_manager import check_and_recover_interrupted_operations
        try:
            check_and_recover_interrupted_operations()
        except Exception as e:
            app_logger.warning(f"Aviso ao verificar operações de recuperação: {e}")

        self.splash.set_progress(80, "Inicializando interface profissional...")
        self.app.processEvents()

        self.main_window = MainWindow()

        self.splash.set_progress(95, "Pronto.")
        self.app.processEvents()

    def run(self) -> int:
        app_logger.info("Iniciando ALTUS PC OPTIMIZER GUI...")
        # Fecha splash e apresenta janela principal
        QTimer.singleShot(400, self._show_main_window)
        return self.app.exec()

    def _show_main_window(self):
        self.main_window.show()
        self.splash.finish(self.main_window)
