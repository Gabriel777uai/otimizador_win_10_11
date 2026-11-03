"""
Página THERMAL GUARD - ALTUS PC OPTIMIZER.
Monitoramento térmico, frequências reais de CPU/GPU, consumo e diagnóstico de throttling.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTextEdit
)
from PySide6.QtCore import Qt

from src.modules.thermal.thermal_manager import thermal_guard
from src.interface.dialogs.custom_dialogs import show_toast

class ThermalGuardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_telemetry()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Cabeçalho
        top = QHBoxLayout()
        t_box = QVBoxLayout()
        lbl_title = QLabel("THERMAL GUARD — TELEMETRIA TÉRMICA & ENERGIA")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Monitoramento de temperatura, clock de operação, ventoinhas e análise de thermal throttling")
        lbl_sub.setProperty("class", "PageSubtitle")
        t_box.addWidget(lbl_title)
        t_box.addWidget(lbl_sub)
        top.addLayout(t_box)
        top.addStretch()

        btn_refresh = QPushButton("🔄 Atualizar Sensores")
        btn_refresh.setProperty("class", "SecondaryButton")
        btn_refresh.clicked.connect(self.refresh_telemetry)
        top.addWidget(btn_refresh)
        layout.addLayout(top)

        # Cards Principais de CPU e GPU
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        # Card CPU
        self.card_cpu = QFrame()
        self.card_cpu.setProperty("class", "CardFrame")
        c_cpu = QVBoxLayout(self.card_cpu)
        lbl_c_t = QLabel("PROCESSADOR (CPU)")
        lbl_c_t.setProperty("class", "CardTitle")
        c_cpu.addWidget(lbl_c_t)
        self.lbl_cpu_temp = QLabel("-- °C")
        self.lbl_cpu_temp.setStyleSheet("font-size: 26px; font-weight: 800; color: #00d2ff;")
        c_cpu.addWidget(self.lbl_cpu_temp)
        self.lbl_cpu_freq = QLabel("Clock: -- MHz")
        self.lbl_cpu_freq.setStyleSheet("color: #94a3b8; font-size: 13px;")
        c_cpu.addWidget(self.lbl_cpu_freq)
        cards_layout.addWidget(self.card_cpu)

        # Card GPU
        self.card_gpu = QFrame()
        self.card_gpu.setProperty("class", "CardFrame")
        c_gpu = QVBoxLayout(self.card_gpu)
        lbl_g_t = QLabel("PLACA DE VÍDEO (GPU)")
        lbl_g_t.setProperty("class", "CardTitle")
        c_gpu.addWidget(lbl_g_t)
        self.lbl_gpu_temp = QLabel("-- °C")
        self.lbl_gpu_temp.setStyleSheet("font-size: 26px; font-weight: 800; color: #38bdf8;")
        c_gpu.addWidget(self.lbl_gpu_temp)
        self.lbl_gpu_sub = QLabel("Clock: -- MHz | Consumo: -- W | Fan: --%")
        self.lbl_gpu_sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        c_gpu.addWidget(self.lbl_gpu_sub)
        cards_layout.addWidget(self.card_gpu)

        layout.addLayout(cards_layout)

        # Painel de Diagnóstico de Throttling
        self.diag_frame = QFrame()
        self.diag_frame.setProperty("class", "CardFrame")
        df_l = QVBoxLayout(self.diag_frame)
        lbl_df_t = QLabel("ESTADO TÉRMICO E ANÁLISE DE LIMITAÇÃO (THROTTLING)")
        lbl_df_t.setProperty("class", "SectionTitle")
        df_l.addWidget(lbl_df_t)

        self.lbl_status = QLabel("Analisando parâmetros térmicos...")
        self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #10b981;")
        df_l.addWidget(self.lbl_status)

        self.txt_evidence = QTextEdit()
        self.txt_evidence.setReadOnly(True)
        self.txt_evidence.setFixedHeight(120)
        self.txt_evidence.setStyleSheet("""
            background-color: #050b14;
            color: #cbd5e1;
            font-size: 12px;
            border: 1px solid #162238;
            border-radius: 6px;
            padding: 8px;
        """)
        df_l.addWidget(self.txt_evidence)
        layout.addWidget(self.diag_frame)

        layout.addStretch()

    def refresh_telemetry(self):
        snap = thermal_guard.get_full_thermal_snapshot()
        cpu = snap.get("cpu", {})
        gpu = snap.get("gpu", {})
        analysis = snap.get("analysis", {})

        # Atualiza CPU
        cpu_t = cpu.get("temperature_c")
        self.lbl_cpu_temp.setText(f"{cpu_t} °C" if cpu_t is not None else "Sensor BIOS não exposto")
        cpu_f = cpu.get("frequency", {})
        curr_f = cpu_f.get("current_mhz", "N/A")
        max_f = cpu_f.get("max_mhz", "N/A")
        self.lbl_cpu_freq.setText(f"Clock Atual: {curr_f} MHz (Base/Max: {max_f} MHz)")

        # Atualiza GPU
        if gpu.get("available"):
            g_temp = gpu.get("temperature_c", "N/A")
            g_clk = gpu.get("clock_mhz", "N/A")
            g_pwr = gpu.get("power_watts", "N/A")
            g_fan = gpu.get("fan_speed_percent", "N/A")
            self.lbl_gpu_temp.setText(f"{g_temp} °C")
            self.lbl_gpu_sub.setText(f"Clock: {g_clk} MHz | Consumo: {g_pwr} W | Fan: {g_fan}%")
        else:
            self.lbl_gpu_temp.setText("Indisponível")
            self.lbl_gpu_sub.setText(gpu.get("reason", "Sensor de GPU não acessível."))

        # Atualiza Throttling
        status_text = analysis.get("status", "Normal")
        self.lbl_status.setText(status_text)
        if "Crítico" in status_text:
            self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #ef4444;")
        elif "Atenção" in status_text:
            self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #f59e0b;")
        else:
            self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #10b981;")

        ev_lines = "\n".join(f"• {e}" for e in analysis.get("evidence", []))
        self.txt_evidence.setPlainText(ev_lines)
        show_toast(self, "Telemetria térmica atualizada!", "info")
