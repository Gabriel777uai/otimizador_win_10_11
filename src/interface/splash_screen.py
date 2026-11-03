"""
Tela de Carregamento Inicial (Splash Screen) - ALTUS PC OPTIMIZER.
Exibe logotipo tecnológico, versão e barra de inicialização dos módulos essenciais.
"""
from pathlib import Path
from PySide6.QtWidgets import QSplashScreen, QWidget, QVBoxLayout, QLabel, QProgressBar, QFrame
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QColor, QPainter

class AltusSplashScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(480, 280)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #070d19;
                border: 1px solid #00d2ff;
                border-radius: 14px;
            }
        """)
        cl = QVBoxLayout(container)
        cl.setContentsMargins(32, 28, 32, 28)
        cl.setSpacing(12)

        # Logo e Título
        logo_path = Path(__file__).resolve().parent.parent / "resources" / "icons" / "logo_64.png"
        lbl_logo = QLabel()
        if logo_path.exists():
            lbl_logo.setPixmap(QPixmap(str(logo_path)).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lbl_logo.setAlignment(Qt.AlignCenter)
        lbl_logo.setStyleSheet("border: none;")
        cl.addWidget(lbl_logo)

        lbl_app = QLabel("ALTUS PC OPTIMIZER")
        lbl_app.setStyleSheet("color: #00d2ff; font-size: 20px; font-weight: 800; letter-spacing: 2px; border: none;")
        lbl_app.setAlignment(Qt.AlignCenter)
        cl.addWidget(lbl_app)

        lbl_sub = QLabel("SISTEMA PROFISSIONAL DE OTIMIZAÇÃO E MANUTENÇÃO")
        lbl_sub.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 600; letter-spacing: 1px; border: none;")
        lbl_sub.setAlignment(Qt.AlignCenter)
        cl.addWidget(lbl_sub)

        cl.addSpacing(10)

        # Barra de Progresso
        self.prog = QProgressBar()
        self.prog.setFixedHeight(6)
        self.prog.setValue(15)
        self.prog.setTextVisible(False)
        self.prog.setStyleSheet("""
            QProgressBar {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0070ba, stop:1 #00d2ff);
                border-radius: 3px;
            }
        """)
        cl.addWidget(self.prog)

        # Mensagem de Carregamento
        self.lbl_status = QLabel("Inicializando módulos de segurança...")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11px; border: none;")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.lbl_status)

        layout.addWidget(container)

    def set_progress(self, percent: int, message: str):
        self.prog.setValue(percent)
        self.lbl_status.setText(message)
