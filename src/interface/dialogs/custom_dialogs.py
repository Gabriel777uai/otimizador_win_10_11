"""
Diálogos e Notificações Personalizados - ALTUS PC OPTIMIZER.
Substitui completamente os alertas genéricos e caixas de mensagem do Windows.
Mantém fidelidade visual à paleta Dark Navy / Ciano / Azul Elétrico.
"""
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QWidget, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont

from src.core.progress_manager import ProgressReporter, OperationState

class CustomMessageDialog(QDialog):
    """Diálogo modal moderno para mensagens informativas, avisos, erros e sucessos."""
    def __init__(
        self,
        parent=None,
        title: str = "Aviso do Sistema",
        message: str = "",
        details: Optional[List[str]] = None,
        dialog_type: str = "info"  # 'info', 'success', 'warning', 'error'
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(520)

        self._init_ui(title, message, details or [], dialog_type)

    def _init_ui(self, title: str, message: str, details: List[str], dialog_type: str):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        # Container principal com borda e fundo escuro
        box = QFrame()
        box.setStyleSheet("""
            QFrame {
                background-color: #0b1324;
                border: 1px solid #1e3a5f;
                border-radius: 12px;
            }
        """)
        bl = QVBoxLayout(box)
        bl.setContentsMargins(24, 24, 24, 24)
        bl.setSpacing(16)

        # Cabeçalho com ícone temático
        header = QHBoxLayout()
        icon_map = {
            "success": ("✓", "#10b981", "SUCESSO"),
            "warning": ("⚠", "#f59e0b", "ATENÇÃO"),
            "error": ("✕", "#ef4444", "ERRO"),
            "info": ("ℹ", "#00d2ff", "INFORMAÇÃO")
        }
        sym, col, def_tag = icon_map.get(dialog_type, ("ℹ", "#00d2ff", "INFORMAÇÃO"))

        lbl_icon = QLabel(sym)
        lbl_icon.setStyleSheet(f"""
            QLabel {{
                background-color: {col}22;
                color: {col};
                border: 1px solid {col}55;
                border-radius: 18px;
                font-size: 18px;
                font-weight: bold;
                qproperty-alignment: AlignCenter;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
            }}
        """)
        header.addWidget(lbl_icon)

        t_layout = QVBoxLayout()
        t_layout.setSpacing(2)
        lbl_t = QLabel(title)
        lbl_t.setWordWrap(True)
        lbl_t.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 700; border: none;")
        t_layout.addWidget(lbl_t)
        header.addLayout(t_layout)
        header.addStretch()
        bl.addLayout(header)

        # Mensagem principal
        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("color: #cbd5e1; font-size: 13px; line-height: 1.4; border: none;")
        bl.addWidget(lbl_msg)

        # Lista de detalhes se houver
        if details:
            det_box = QFrame()
            det_box.setStyleSheet("background-color: #070d19; border: 1px solid #162238; border-radius: 6px; padding: 10px;")
            dl = QVBoxLayout(det_box)
            dl.setSpacing(6)
            for d in details:
                lbl_d = QLabel(f"• {d}")
                lbl_d.setWordWrap(True)
                lbl_d.setStyleSheet("color: #94a3b8; font-size: 12px; border: none;")
                dl.addWidget(lbl_d)
            bl.addWidget(det_box)

        # Botão de Ação
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_ok = QPushButton("Entendido")
        btn_ok.setProperty("class", "PrimaryButton")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setFixedHeight(36)
        btn_ok.setFixedWidth(120)
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)
        bl.addLayout(btn_box)

        outer.addWidget(box)

class CustomConfirmDialog(QDialog):
    """Diálogo modal para confirmações de ações com opção Cancelar / Confirmar."""
    def __init__(
        self,
        parent=None,
        title: str = "Confirmação Obrigatória",
        message: str = "",
        confirm_text: str = "Confirmar",
        cancel_text: str = "Cancelar",
        is_dangerous: bool = False
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(520)

        self._init_ui(title, message, confirm_text, cancel_text, is_dangerous)

    def _init_ui(self, title: str, message: str, confirm_text: str, cancel_text: str, is_dangerous: bool):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        box = QFrame()
        box.setStyleSheet("""
            QFrame {
                background-color: #0b1324;
                border: 1px solid #1e3a5f;
                border-radius: 12px;
            }
        """)
        bl = QVBoxLayout(box)
        bl.setContentsMargins(24, 24, 24, 24)
        bl.setSpacing(16)

        # Cabeçalho
        header = QHBoxLayout()
        header.setSpacing(12)
        sym = "⚠️" if is_dangerous else "🛡️"
        col = "#ef4444" if is_dangerous else "#00d2ff"

        lbl_icon = QLabel(sym)
        lbl_icon.setStyleSheet(f"""
            QLabel {{
                background-color: {col}22;
                border: 1px solid {col}55;
                border-radius: 18px;
                font-size: 18px;
                qproperty-alignment: AlignCenter;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
            }}
        """)
        header.addWidget(lbl_icon)

        lbl_t = QLabel(title)
        lbl_t.setWordWrap(True)
        lbl_t.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 700; border: none;")
        header.addWidget(lbl_t)
        header.addStretch()
        bl.addLayout(header)

        # Mensagem
        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("color: #cbd5e1; font-size: 13px; line-height: 1.4; border: none;")
        bl.addWidget(lbl_msg)

        # Botões
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.addStretch()

        btn_cancel = QPushButton(cancel_text)
        btn_cancel.setProperty("class", "SecondaryButton")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_confirm = QPushButton(confirm_text)
        btn_confirm.setProperty("class", "DangerButton" if is_dangerous else "PrimaryButton")
        btn_confirm.setFixedHeight(36)
        btn_confirm.setCursor(Qt.PointingHandCursor)
        btn_confirm.clicked.connect(self.accept)
        btn_box.addWidget(btn_confirm)

        bl.addLayout(btn_box)
        outer.addWidget(box)

class OperationResultDialog(QDialog):
    """Diálogo modal com resumo executivo de métricas pós-operação em grid responsivo."""
    def __init__(self, parent=None, title: str = "Resultado da Manutenção", message: str = "", stats: Dict[str, Any] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(620)

        self._init_ui(title, message, stats or {})

    def _init_ui(self, title: str, message: str, stats: Dict[str, Any]):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        box = QFrame()
        box.setStyleSheet("""
            QFrame {
                background-color: #0b1324;
                border: 1px solid #10b981;
                border-radius: 12px;
            }
        """)
        bl = QVBoxLayout(box)
        bl.setContentsMargins(24, 24, 24, 24)
        bl.setSpacing(16)

        # Cabeçalho
        h = QHBoxLayout()
        h.setSpacing(12)
        lbl_icon = QLabel("✓")
        lbl_icon.setStyleSheet("""
            background-color: #10b98122;
            color: #10b981;
            border: 1px solid #10b981;
            border-radius: 18px;
            font-size: 18px;
            font-weight: bold;
            qproperty-alignment: AlignCenter;
            min-width: 36px;
            max-width: 36px;
            min-height: 36px;
            max-height: 36px;
        """)
        h.addWidget(lbl_icon)

        lbl_t = QLabel(title)
        lbl_t.setWordWrap(True)
        lbl_t.setStyleSheet("color: #ffffff; font-size: 17px; font-weight: 800; border: none;")
        h.addWidget(lbl_t)
        h.addStretch()
        bl.addLayout(h)

        if message:
            lbl_m = QLabel(message)
            lbl_m.setWordWrap(True)
            lbl_m.setStyleSheet("color: #cbd5e1; font-size: 13px; border: none; line-height: 1.4;")
            bl.addWidget(lbl_m)

        # Grid de Estatísticas em Cards Responsivos (2 colunas para até 4 itens, 3 para mais)
        if stats:
            grid_frame = QFrame()
            grid_frame.setObjectName("ResultGridFrame")
            grid_frame.setStyleSheet("""
                QFrame#ResultGridFrame {
                    background-color: #070e1c;
                    border: 1px solid #1a2f4c;
                    border-radius: 10px;
                }
            """)
            grid = QGridLayout(grid_frame)
            grid.setContentsMargins(12, 12, 12, 12)
            grid.setSpacing(10)

            items = list(stats.items())
            num_items = len(items)
            cols = 2 if num_items <= 4 else 3

            for idx, (key, val) in enumerate(items):
                r = idx // cols
                c = idx % cols

                card = QFrame()
                card.setObjectName(f"ResultCard_{idx}")
                card.setStyleSheet(f"""
                    QFrame#ResultCard_{idx} {{
                        background-color: #0c1527;
                        border: 1px solid #1e3a5f;
                        border-radius: 8px;
                    }}
                    QFrame#ResultCard_{idx}:hover {{
                        border: 1px solid #00d2ff;
                        background-color: #0e1a32;
                    }}
                """)
                card.setMinimumHeight(68)
                cl = QVBoxLayout(card)
                cl.setContentsMargins(14, 10, 14, 10)
                cl.setSpacing(3)

                l_k = QLabel(key.upper())
                l_k.setWordWrap(True)
                l_k.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700; border: none; letter-spacing: 0.5px;")

                l_v = QLabel(str(val))
                l_v.setWordWrap(True)
                l_v.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 800; border: none;")

                cl.addWidget(l_k)
                cl.addWidget(l_v)
                grid.addWidget(card, r, c)

            bl.addWidget(grid_frame)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_close = QPushButton("Entendido")
        btn_close.setProperty("class", "PrimaryButton")
        btn_close.setFixedHeight(36)
        btn_close.setFixedWidth(130)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)
        bl.addLayout(btn_box)

        outer.addWidget(box)

class CustomProgressDialog(QDialog):
    """Janela de progresso modal centralizada com etapas, porcentagem real e tempo."""
    def __init__(self, parent=None, reporter: ProgressReporter = None, title: str = "Executando Operação", can_cancel: bool = True):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(540)

        self.reporter = reporter
        self.can_cancel = can_cancel

        self._init_ui(title)
        self._connect_reporter()

        # Timer para atualizar o relógio decorrido
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(500)

    def _init_ui(self, title: str):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        box = QFrame()
        box.setStyleSheet("""
            QFrame {
                background-color: #0b1324;
                border: 1px solid #00d2ff;
                border-radius: 12px;
            }
        """)
        bl = QVBoxLayout(box)
        bl.setContentsMargins(24, 24, 24, 24)
        bl.setSpacing(14)

        # Cabeçalho
        h = QHBoxLayout()
        h.setSpacing(10)
        lbl_t = QLabel(title)
        lbl_t.setWordWrap(True)
        lbl_t.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 700; border: none;")
        h.addWidget(lbl_t)
        h.addStretch()

        self.lbl_clock = QLabel("00:00")
        self.lbl_clock.setStyleSheet("color: #38bdf8; font-family: monospace; font-size: 12px; font-weight: bold; border: none;")
        h.addWidget(self.lbl_clock)
        bl.addLayout(h)

        # Etapa Atual
        self.lbl_step = QLabel("Iniciando operação...")
        self.lbl_step.setWordWrap(True)
        self.lbl_step.setStyleSheet("color: #94a3b8; font-size: 13px; border: none;")
        bl.addWidget(self.lbl_step)

        # Barra de Progresso com Porcentagem
        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedHeight(12)
        self.prog_bar.setValue(0)
        self.prog_bar.setTextVisible(False)
        bl.addWidget(self.prog_bar)

        # Linha de Métricas (Itens / Porcentagem)
        info_row = QHBoxLayout()
        self.lbl_items = QLabel("Itens processados: 0 / 0")
        self.lbl_items.setWordWrap(True)
        self.lbl_items.setStyleSheet("color: #64748b; font-size: 11px; border: none;")
        info_row.addWidget(self.lbl_items)
        info_row.addStretch()

        self.lbl_pct = QLabel("0%")
        self.lbl_pct.setStyleSheet("color: #00d2ff; font-size: 13px; font-weight: bold; border: none;")
        info_row.addWidget(self.lbl_pct)
        bl.addLayout(info_row)

        # Botão Cancelar (se permitido)
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        if self.can_cancel:
            self.btn_cancel = QPushButton("Cancelar Operação")
            self.btn_cancel.setProperty("class", "SecondaryButton")
            self.btn_cancel.setFixedHeight(36)
            self.btn_cancel.setCursor(Qt.PointingHandCursor)
            self.btn_cancel.clicked.connect(self._handle_cancel)
            btn_box.addWidget(self.btn_cancel)
        bl.addLayout(btn_box)

        outer.addWidget(box)

    def _connect_reporter(self):
        if not self.reporter:
            return
        self.reporter.progress_changed.connect(self._on_progress_changed)
        self.reporter.state_changed.connect(self._on_state_changed)
        self.reporter.indeterminate_changed.connect(self._on_indeterminate_changed)
        self.reporter.finished.connect(self._on_finished)
        self.reporter.error_occurred.connect(self._on_error)

    def _on_indeterminate_changed(self, is_indeterminate: bool, step_desc: str):
        if is_indeterminate:
            self.prog_bar.setRange(0, 0)
            self.lbl_pct.setText("...")
            self.lbl_items.setText("Operação em andamento no Windows...")
        else:
            self.prog_bar.setRange(0, 100)
        if step_desc:
            self.lbl_step.setText(step_desc)

    def _on_progress_changed(self, current: int, total: int, step_desc: str, percent: float):
        if self.prog_bar.maximum() == 0:
            self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(int(percent))
        self.lbl_pct.setText(f"{percent:.0f}%")
        if step_desc:
            self.lbl_step.setText(step_desc)
        if total > 0:
            self.lbl_items.setText(f"Itens processados: {current} / {total}")
        else:
            self.lbl_items.setText(f"Itens processados: {current}")

    def _on_state_changed(self, state: OperationState, msg: str):
        if state == OperationState.COMPLETED:
            self.lbl_step.setText("Operação concluída.")
            self.prog_bar.setValue(100)
            self.lbl_pct.setText("100%")
        elif state == OperationState.CANCELLED:
            self.lbl_step.setText("Operação cancelada.")
        elif state == OperationState.ERROR:
            self.lbl_step.setText(f"Erro: {msg}")

    def _on_finished(self, results: dict):
        self.clock_timer.stop()
        self.accept()

    def _on_error(self, err_msg: str):
        self.clock_timer.stop()
        self.reject()

    def _update_clock(self):
        if self.reporter:
            self.lbl_clock.setText(self.reporter.elapsed_time_str)

    def _handle_cancel(self):
        if self.reporter:
            self.reporter.cancel()
            self.lbl_step.setText("Cancelando...")
            if hasattr(self, 'btn_cancel'):
                self.btn_cancel.setEnabled(False)

class CustomToast(QWidget):
    """Notificação flutuante temporizada não-bloqueante no canto inferior direito."""
    def __init__(self, parent=None, message: str = "", toast_type: str = "info", duration_ms: int = 3500):
        super().__init__(parent)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        cols = {
            "success": ("#10b981", "✓"),
            "warning": ("#f59e0b", "⚠"),
            "error": ("#ef4444", "✕"),
            "info": ("#00d2ff", "ℹ")
        }
        col, sym = cols.get(toast_type, ("#00d2ff", "ℹ"))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 16, 10)

        box = QFrame()
        box.setStyleSheet(f"""
            QFrame {{
                background-color: #0c1629;
                border: 1px solid {col};
                border-radius: 8px;
            }}
        """)
        bl = QHBoxLayout(box)
        bl.setContentsMargins(12, 8, 14, 8)
        bl.setSpacing(10)

        lbl_i = QLabel(sym)
        lbl_i.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 15px; border: none;")
        bl.addWidget(lbl_i)

        lbl_m = QLabel(message)
        lbl_m.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 600; border: none;")
        bl.addWidget(lbl_m)

        layout.addWidget(box)

        # Efeito de opacidade suave
        self.opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        self.opacity.setOpacity(0.0)

        self.anim = QPropertyAnimation(self.opacity, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

        # Timer para auto-fechamento
        QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_out(self):
        self.anim_out = QPropertyAnimation(self.opacity, b"opacity")
        self.anim_out.setDuration(300)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.close)
        self.anim_out.start()

def show_toast(parent: QWidget, message: str, toast_type: str = "info"):
    """Exibe um toast flutuante posicionado no canto inferior direito da janela principal."""
    if not parent:
        return
    win = parent.window() if hasattr(parent, 'window') and parent.window() else parent
    toast = CustomToast(win, message, toast_type)
    toast.adjustSize()
    x = win.width() - toast.width() - 25
    y = win.height() - toast.height() - 25
    toast.move(x, y)
    toast.show()
