"""
Página de Relatórios e Histórico - ALTUS PC OPTIMIZER.
Permite auditar manutenções anteriores e exportar relatórios técnicos em HTML e TXT
com diálogos estilizados sem dependência do QMessageBox nativo.
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt

from src.modules.reports.history_manager import get_operation_history, clear_operation_history
from src.modules.reports.report_generator import generate_html_report, generate_txt_report
from src.interface.dialogs.custom_dialogs import CustomConfirmDialog, CustomMessageDialog, show_toast

class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_history()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Cabeçalho
        top = QHBoxLayout()
        t_box = QVBoxLayout()
        lbl_title = QLabel("RELATÓRIOS E HISTÓRICO DE MANUTENÇÃO")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Trilha completa de auditoria com data, hora, arquivos processados e espaço recuperado")
        lbl_sub.setProperty("class", "PageSubtitle")
        t_box.addWidget(lbl_title)
        t_box.addWidget(lbl_sub)
        top.addLayout(t_box)
        top.addStretch()

        # Botões de Exportação
        btn_export_html = QPushButton("🌐 Exportar Relatório HTML")
        btn_export_html.setProperty("class", "PrimaryButton")
        btn_export_html.clicked.connect(self._export_html)
        top.addWidget(btn_export_html)

        btn_export_txt = QPushButton("📄 Exportar TXT")
        btn_export_txt.setProperty("class", "SecondaryButton")
        btn_export_txt.clicked.connect(self._export_txt)
        top.addWidget(btn_export_txt)

        layout.addLayout(top)

        # Cards com Totais
        cards_row = QHBoxLayout()
        self.card_total_freed = self._create_metric_card("TOTAL DE ESPAÇO LIBERADO", "0.0 MB")
        self.card_total_ops = self._create_metric_card("OPERAÇÕES REALIZADAS", "0")
        cards_row.addWidget(self.card_total_freed)
        cards_row.addWidget(self.card_total_ops)
        cards_row.addStretch()
        layout.addLayout(cards_row)

        # Tabela de Histórico
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Data / Hora", "Operação", "Status", "Espaço Liberado", "Detalhes"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.table)

        # Barra inferior
        bottom_bar = QHBoxLayout()
        btn_clear_hist = QPushButton("🗑️ Limpar Histórico")
        btn_clear_hist.setProperty("class", "SecondaryButton")
        btn_clear_hist.clicked.connect(self._clear_history)
        bottom_bar.addWidget(btn_clear_hist)

        btn_refresh = QPushButton("🔄 Atualizar")
        btn_refresh.setProperty("class", "SecondaryButton")
        btn_refresh.clicked.connect(self.refresh_history)
        bottom_bar.addWidget(btn_refresh)
        bottom_bar.addStretch()

        layout.addLayout(bottom_bar)

    def _create_metric_card(self, title: str, val: str) -> QFrame:
        c = QFrame()
        c.setProperty("class", "CardFrame")
        cl = QVBoxLayout(c)
        l1 = QLabel(title)
        l1.setProperty("class", "CardTitle")
        l2 = QLabel(val)
        l2.setProperty("class", "CardValue")
        cl.addWidget(l1)
        cl.addWidget(l2)
        c.lbl_val = l2
        return c

    def refresh_history(self):
        history = get_operation_history()
        self.table.setRowCount(len(history))

        total_freed_mb = 0.0

        for i, h in enumerate(history):
            self.table.setItem(i, 0, QTableWidgetItem(h.get("timestamp", "")))
            self.table.setItem(i, 1, QTableWidgetItem(h.get("operation", "")))

            st_item = QTableWidgetItem(h.get("status", ""))
            if h.get("status") in ("Concluído", "OK"):
                st_item.setForeground(Qt.green)
            else:
                st_item.setForeground(Qt.yellow)
            self.table.setItem(i, 2, st_item)

            freed = h.get("freed_mb", 0.0)
            total_freed_mb += freed
            self.table.setItem(i, 3, QTableWidgetItem(f"{freed} MB"))
            self.table.setItem(i, 4, QTableWidgetItem(h.get("details", "")))

        self.card_total_freed.lbl_val.setText(f"{round(total_freed_mb, 1)} MB")
        self.card_total_ops.lbl_val.setText(str(len(history)))

    def _export_html(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Relatório HTML", "Relatorio_Altus.html", "Documento HTML (*.html)")
        if path:
            if generate_html_report(Path(path)):
                CustomMessageDialog(
                    self,
                    title="Relatório HTML Exportado",
                    message=f"O relatório técnico executivo foi gerado com sucesso em:\n{path}",
                    dialog_type="success"
                ).exec()
                show_toast(self, "Relatório HTML salvo!", "success")
            else:
                CustomMessageDialog(self, "Erro", "Não foi possível gerar o arquivo de relatório.", dialog_type="error").exec()

    def _export_txt(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Relatório TXT", "Relatorio_Altus.txt", "Documento de Texto (*.txt)")
        if path:
            if generate_txt_report(Path(path)):
                CustomMessageDialog(
                    self,
                    title="Relatório TXT Exportado",
                    message=f"O relatório técnico de auditoria foi gravado em:\n{path}",
                    dialog_type="success"
                ).exec()
                show_toast(self, "Relatório TXT salvo!", "success")
            else:
                CustomMessageDialog(self, "Erro", "Não foi possível gerar o arquivo de texto.", dialog_type="error").exec()

    def _clear_history(self):
        confirm = CustomConfirmDialog(
            parent=self,
            title="Limpar Histórico de Manutenção",
            message="Deseja apagar permanentemente todo o histórico de operações gravadas?",
            confirm_text="Apagar Histórico",
            cancel_text="Cancelar",
            is_dangerous=True
        )
        if confirm.exec():
            clear_operation_history()
            self.refresh_history()
            show_toast(self, "Histórico limpo com sucesso!", "info")
