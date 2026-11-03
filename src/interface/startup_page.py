"""
Página de Gerenciamento da Inicialização do Windows - ALTUS PC OPTIMIZER.
Audita e gerencia entradas que iniciam automaticamente com o sistema
utilizando diálogos e notificações nativos do ALTUS.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt

from src.modules.gaming.startup_optimizer import get_startup_entries, disable_startup_entry
from src.modules.reports.history_manager import log_operation_event
from src.interface.dialogs.custom_dialogs import CustomConfirmDialog, CustomMessageDialog, show_toast

class StartupPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries = []
        self._init_ui()
        self.refresh_entries()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Cabeçalho
        top = QHBoxLayout()
        t_box = QVBoxLayout()
        lbl_title = QLabel("GERENCIADOR DE INICIALIZAÇÃO DO WINDOWS")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Identifique e desative com segurança programas que iniciam com o sistema para reduzir o tempo de boot")
        lbl_sub.setProperty("class", "PageSubtitle")
        t_box.addWidget(lbl_title)
        t_box.addWidget(lbl_sub)
        top.addLayout(t_box)
        top.addStretch()

        btn_refresh = QPushButton("🔄 Atualizar Lista")
        btn_refresh.setProperty("class", "SecondaryButton")
        btn_refresh.clicked.connect(self.refresh_entries)
        top.addWidget(btn_refresh)

        layout.addLayout(top)

        # Tabela de Aplicativos na Inicialização
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Nome do Programa", "Origem", "Impacto", "Comando / Executável", "Permite Desativação"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        # Botão de Ação
        bottom_bar = QHBoxLayout()
        btn_disable = QPushButton("⛔ Desativar Programa Selecionado (com Backup)")
        btn_disable.setProperty("class", "WarningButton")
        btn_disable.setCursor(Qt.PointingHandCursor)
        btn_disable.clicked.connect(self._disable_selected)
        bottom_bar.addWidget(btn_disable)

        lbl_sec = QLabel("🛡️ Proteção ativa: Componentes essenciais e drivers de sistema não podem ser desativados.")
        lbl_sec.setStyleSheet("color: #94a3b8; font-size: 12px;")
        bottom_bar.addWidget(lbl_sec)
        bottom_bar.addStretch()

        layout.addLayout(bottom_bar)

    def refresh_entries(self):
        self.entries = get_startup_entries()
        self.table.setRowCount(len(self.entries))

        for i, item in enumerate(self.entries):
            self.table.setItem(i, 0, QTableWidgetItem(item.get("name", "")))
            self.table.setItem(i, 1, QTableWidgetItem(item.get("location", "")))
            self.table.setItem(i, 2, QTableWidgetItem(item.get("impact", "")))
            self.table.setItem(i, 3, QTableWidgetItem(item.get("command", "")))
            can_dis = "Sim" if item.get("can_disable") else "Protegido (Segurança)"
            self.table.setItem(i, 4, QTableWidgetItem(can_dis))

    def _disable_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.entries):
            CustomMessageDialog(self, "Seleção Necessária", "Por favor, selecione um programa da tabela.", dialog_type="info").exec()
            return

        entry = self.entries[row]
        if not entry.get("can_disable"):
            CustomMessageDialog(
                self,
                "Ação Bloqueada",
                "Este aplicativo pertence aos drivers essenciais ou mecanismos de proteção do Windows e não pode ser desativado.",
                dialog_type="warning"
            ).exec()
            return

        confirm = CustomConfirmDialog(
            parent=self,
            title="Confirmar Desativação",
            message=f"Deseja desativar '{entry.get('name')}' da inicialização automática do Windows?\n\n"
                    "O valor original será copiado para uma chave de backup permitindo reativação futura.",
            confirm_text="Desativar",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            res = disable_startup_entry(entry, user_confirmed=True)
            if res.get("success"):
                log_operation_event("Desativação de Inicialização", "Concluído", f"Desativado: {entry.get('name')}")
                CustomMessageDialog(self, "Programa Desativado", res.get("message"), dialog_type="success").exec()
                self.refresh_entries()
                show_toast(self, f"'{entry.get('name')}' desativado com sucesso!", "success")
            else:
                CustomMessageDialog(self, "Erro", res.get("message"), dialog_type="error").exec()
