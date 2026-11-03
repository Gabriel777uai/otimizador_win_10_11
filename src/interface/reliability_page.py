"""
Página WINDOWS RELIABILITY ANALYZER - ALTUS PC OPTIMIZER.
Linha do tempo de incidentes do Windows, classificação de falhas de aplicativos,
drivers e kernel, com recomendações técnicas e exportação.
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QFileDialog
)
from PySide6.QtCore import Qt

from src.modules.windows.reliability_analyzer import get_system_reliability_events
from src.interface.dialogs.custom_dialogs import CustomMessageDialog, show_toast

class ReliabilityPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cached_events = []
        self._init_ui()
        self.refresh_events()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Cabeçalho
        top = QHBoxLayout()
        t_box = QVBoxLayout()
        lbl_title = QLabel("WINDOWS RELIABILITY ANALYZER — ESTABILIDADE DO SO")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Auditoria de falhas do sistema, aplicativos, drivers gráficos e reinicializações inesperadas")
        lbl_sub.setProperty("class", "PageSubtitle")
        t_box.addWidget(lbl_title)
        t_box.addWidget(lbl_sub)
        top.addLayout(t_box)
        top.addStretch()

        btn_refresh = QPushButton("🔄 Atualizar Eventos")
        btn_refresh.setProperty("class", "SecondaryButton")
        btn_refresh.clicked.connect(self.refresh_events)
        top.addWidget(btn_refresh)
        layout.addLayout(top)

        # Tabela da Linha do Tempo
        lbl_t_tbl = QLabel("LINHA DO TEMPO DE INCIDENTES RECENTES (ÚLTIMOS 7 DIAS)")
        lbl_t_tbl.setProperty("class", "SectionTitle")
        layout.addWidget(lbl_t_tbl)

        self.table_events = QTableWidget()
        self.table_events.setColumnCount(5)
        self.table_events.setHorizontalHeaderLabels([
            "Data / Hora", "Gravidade", "Categoria", "Origem / ID", "Resumo do Evento"
        ])
        self.table_events.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_events.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_events.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_events.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_events.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table_events.verticalHeader().setVisible(False)
        self.table_events.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_events.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_events.itemSelectionChanged.connect(self._on_event_selected)
        self.table_events.setFixedHeight(230)
        layout.addWidget(self.table_events)

        # Painel de Detalhes Técnicos e Recomendações
        det_frame = QFrame()
        det_frame.setProperty("class", "CardFrame")
        df_l = QVBoxLayout(det_frame)
        df_l.setSpacing(6)

        lbl_det_title = QLabel("ANÁLISE DE IMPACTO & RECOMENDAÇÃO TÉCNICA")
        lbl_det_title.setProperty("class", "SectionTitle")
        df_l.addWidget(lbl_det_title)

        self.lbl_impact = QLabel("Selecione um evento na linha do tempo para inspecionar os detalhes técnicos.")
        self.lbl_impact.setStyleSheet("color: #cbd5e1; font-size: 13px; font-weight: bold;")
        df_l.addWidget(self.lbl_impact)

        self.lbl_recom = QLabel("Recomendação: Aguardando seleção.")
        self.lbl_recom.setStyleSheet("color: #00d2ff; font-size: 12px;")
        df_l.addWidget(self.lbl_recom)

        self.txt_raw = QTextEdit()
        self.txt_raw.setReadOnly(True)
        self.txt_raw.setFixedHeight(85)
        self.txt_raw.setStyleSheet("""
            background-color: #050b14;
            color: #94a3b8;
            font-family: Consolas, monospace;
            font-size: 11px;
            border: 1px solid #162238;
            border-radius: 6px;
            padding: 6px;
        """)
        df_l.addWidget(self.txt_raw)
        layout.addWidget(det_frame)

        layout.addStretch()

    def refresh_events(self):
        events = get_system_reliability_events(days_back=7, max_events=40)
        self.cached_events = events
        self.table_events.setRowCount(len(events))

        for i, ev in enumerate(events):
            self.table_events.setItem(i, 0, QTableWidgetItem(ev.get("timestamp", "-")))
            
            sev = ev.get("severity", "Erro")
            item_sev = QTableWidgetItem(sev)
            if "Crítico" in sev or "Critical" in sev:
                item_sev.setForeground(Qt.red)
            else:
                item_sev.setForeground(Qt.yellow)
            self.table_events.setItem(i, 1, item_sev)

            self.table_events.setItem(i, 2, QTableWidgetItem(ev.get("category", "Geral")))
            self.table_events.setItem(i, 3, QTableWidgetItem(f"{ev.get('provider')} ({ev.get('event_id')})"))
            self.table_events.setItem(i, 4, QTableWidgetItem(ev.get("summary", "")))

        show_toast(self, "Eventos de confiabilidade atualizados!", "info")

    def _on_event_selected(self):
        sel = self.table_events.selectionModel().selectedRows()
        if not sel:
            return

        row = sel[0].row()
        if row < len(self.cached_events):
            ev = self.cached_events[row]
            self.lbl_impact.setText(f"Possível Impacto: {ev.get('impact')}")
            self.lbl_recom.setText(f"Recomendação Técnica: {ev.get('recommendation')}")
            self.txt_raw.setPlainText(ev.get("full_message") or ev.get("summary"))
