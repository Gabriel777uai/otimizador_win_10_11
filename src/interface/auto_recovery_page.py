"""
Página AUTO RECOVERY CENTER - ALTUS PC OPTIMIZER.
Interface centralizada para auditoria e reversão de modificações no sistema Windows
com proteção contra falhas e histórico formal de recuperação.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit
)
from PySide6.QtCore import Qt

from src.core.recovery_manager import (
    load_ledger, rollback_operation, check_and_recover_interrupted_operations
)
from src.interface.dialogs.custom_dialogs import (
    CustomConfirmDialog, CustomMessageDialog, OperationResultDialog, show_toast
)

class AutoRecoveryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_records()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Cabeçalho
        top = QHBoxLayout()
        t_box = QVBoxLayout()
        lbl_title = QLabel("AUTO RECOVERY CENTER — CENTRAL DE RESTAURAÇÃO")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Rastreamento formal de modificações no Windows com rollback automatizado e seguro")
        lbl_sub.setProperty("class", "PageSubtitle")
        t_box.addWidget(lbl_title)
        t_box.addWidget(lbl_sub)
        top.addLayout(t_box)
        top.addStretch()

        btn_chk_interrupted = QPushButton("🛡️ Verificar Operações Interrompidas")
        btn_chk_interrupted.setProperty("class", "SecondaryButton")
        btn_chk_interrupted.clicked.connect(self._check_interrupted)
        top.addWidget(btn_chk_interrupted)

        layout.addLayout(top)

        # Tabela de Modificações no Ledger
        lbl_tbl_t = QLabel("LIVRO-RAZÃO DE ALTERAÇÕES REVERSÍVEIS")
        lbl_tbl_t.setProperty("class", "SectionTitle")
        layout.addWidget(lbl_tbl_t)

        self.table_ledger = QTableWidget()
        self.table_ledger.setColumnCount(5)
        self.table_ledger.setHorizontalHeaderLabels([
            "ID Registro", "Categoria", "Data / Hora", "Estratégia de Rollback", "Status Atual"
        ])
        self.table_ledger.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_ledger.verticalHeader().setVisible(False)
        self.table_ledger.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_ledger.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_ledger.itemSelectionChanged.connect(self._on_row_selected)
        self.table_ledger.setFixedHeight(220)
        layout.addWidget(self.table_ledger)

        # Ações de Rollback
        btn_row = QHBoxLayout()
        self.btn_rollback = QPushButton("⏪ Reverter / Rollback da Operação Selecionada")
        self.btn_rollback.setProperty("class", "PrimaryButton")
        self.btn_rollback.setEnabled(False)
        self.btn_rollback.clicked.connect(self._do_rollback)
        btn_row.addWidget(self.btn_rollback)

        btn_refresh = QPushButton("🔄 Atualizar Lista")
        btn_refresh.setProperty("class", "SecondaryButton")
        btn_refresh.clicked.connect(self.refresh_records)
        btn_row.addWidget(btn_refresh)
        btn_row.addStretch()

        layout.addLayout(btn_row)

        # Painel de Detalhes da Alteração
        det_frame = QFrame()
        det_frame.setProperty("class", "CardFrame")
        df_l = QVBoxLayout(det_frame)
        lbl_det_t = QLabel("DETALHES DO ESTADO ORIGINAL & APLICADO")
        lbl_det_t.setProperty("class", "SectionTitle")
        df_l.addWidget(lbl_det_t)

        self.txt_details = QTextEdit()
        self.txt_details.setReadOnly(True)
        self.txt_details.setStyleSheet("""
            background-color: #050b14;
            color: #00d2ff;
            font-family: Consolas, monospace;
            font-size: 12px;
            border: 1px solid #162238;
            border-radius: 6px;
            padding: 8px;
        """)
        self.txt_details.setPlaceholderText("Selecione uma linha na tabela acima para visualizar os dados técnicos gravados antes da alteração...")
        df_l.addWidget(self.txt_details)
        layout.addWidget(det_frame)

        layout.addStretch()

    def refresh_records(self):
        records = load_ledger()
        self.table_ledger.setRowCount(len(records))
        for i, r in enumerate(records):
            self.table_ledger.setItem(i, 0, QTableWidgetItem(str(r.get("record_id"))))
            self.table_ledger.setItem(i, 1, QTableWidgetItem(str(r.get("category")).upper()))
            self.table_ledger.setItem(i, 2, QTableWidgetItem(str(r.get("timestamp"))))
            self.table_ledger.setItem(i, 3, QTableWidgetItem(str(r.get("restore_strategy"))))
            status = str(r.get("status"))
            item_st = QTableWidgetItem(status)
            if "ROLL" in status:
                item_st.setForeground(Qt.cyan)
            elif "APPLIED" in status:
                item_st.setForeground(Qt.green)
            elif "FAIL" in status:
                item_st.setForeground(Qt.red)
            self.table_ledger.setItem(i, 4, item_st)

    def _on_row_selected(self):
        sel = self.table_ledger.selectionModel().selectedRows()
        if not sel:
            self.btn_rollback.setEnabled(False)
            self.txt_details.clear()
            return

        row = sel[0].row()
        records = load_ledger()
        if row < len(records):
            r = records[row]
            import json
            details_str = (
                f"=== REGISTRO: {r.get('record_id')} ===\n"
                f"Data/Hora: {r.get('timestamp')}\n"
                f"Status: {r.get('status')}\n"
                f"Estratégia: {r.get('restore_strategy')}\n\n"
                f"[CONFIGURAÇÃO ORIGINAL GRAVADA]:\n"
                f"{json.dumps(r.get('original_state'), indent=2, ensure_ascii=False)}\n\n"
                f"[CONFIGURAÇÃO APLICADA]:\n"
                f"{json.dumps(r.get('applied_state'), indent=2, ensure_ascii=False)}"
            )
            self.txt_details.setPlainText(details_str)
            self.btn_rollback.setEnabled(r.get("status") != "ROLLED_BACK")

    def _do_rollback(self):
        sel = self.table_ledger.selectionModel().selectedRows()
        if not sel:
            return

        row = sel[0].row()
        records = load_ledger()
        if row < len(records):
            r = records[row]
            rec_id = r["record_id"]
            strategy = r.get("restore_strategy")

            confirm = CustomConfirmDialog(
                parent=self,
                title="Confirmar Rollback de Configuração",
                message=f"Deseja reverter a operação '{rec_id}' ({r.get('category')})?\n\n"
                        f"Estratégia: {strategy}\n"
                        "O ALTUS recuperará o estado original prévio registrado com segurança.",
                confirm_text="Executar Rollback",
                cancel_text="Cancelar"
            )
            if confirm.exec():
                res = rollback_operation(rec_id)
                if res.get("success"):
                    OperationResultDialog(
                        self,
                        title="Rollback Concluído",
                        message=res.get("message", "Configurações originais restauradas com sucesso."),
                        stats={
                            "Registro": rec_id,
                            "Status": "Revertido (Original)",
                            "Estratégia": strategy
                        }
                    ).exec()
                    self.refresh_records()
                    self._on_row_selected()
                    show_toast(self, "Rollback executado com sucesso!", "success")
                else:
                    CustomMessageDialog(self, "Falha no Rollback", res.get("message", "Erro ao executar rollback."), dialog_type="error").exec()

    def _check_interrupted(self):
        recovered = check_and_recover_interrupted_operations()
        if recovered:
            CustomMessageDialog(
                self,
                title="Recuperação Automática",
                message=f"Foram identificadas e recuperadas com sucesso {len(recovered)} operações que haviam sido interrompidas.",
                dialog_type="success"
            ).exec()
        else:
            CustomMessageDialog(
                self,
                title="Integridade Confirmada",
                message="Nenhuma operação interrompida foi encontrada no livro-razão de recuperação.",
                dialog_type="info"
            ).exec()
        self.refresh_records()
