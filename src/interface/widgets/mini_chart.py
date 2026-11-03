"""
Widget de Mini Gráfico Vetorial Leve - ALTUS PC OPTIMIZER.
Renderiza gráficos de barras e indicadores de proporção usando QPainter nativo (0 ms).
"""
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush
from PySide6.QtCore import Qt, QRectF

class MiniUsageBar(QWidget):
    """Barra vetorial estilizada com gradiente e bordas suaves."""
    def __init__(self, parent=None, percent: float = 0.0, bar_color: str = "#00d2ff"):
        super().__init__(parent)
        self.setFixedHeight(12)
        self._percent = max(0.0, min(100.0, percent))
        self._bar_color = bar_color

    def set_percent(self, val: float):
        self._percent = max(0.0, min(100.0, val))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Fundo do trilho
        track_rect = QRectF(0, 2, self.width(), 8)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#0a1324"))
        p.drawRoundedRect(track_rect, 4, 4)

        # Barra ativa com gradiente
        if self._percent > 0:
            fill_w = max(6.0, (self.width() * (self._percent / 100.0)))
            fill_rect = QRectF(0, 2, fill_w, 8)

            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0, QColor("#0070ba"))
            grad.setColorAt(1, QColor(self._bar_color))

            p.setBrush(grad)
            p.drawRoundedRect(fill_rect, 4, 4)
        p.end()
