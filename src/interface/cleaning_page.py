"""
Página de Limpeza Inteligente - ALTUS PC OPTIMIZER.
Executa varreduras e limpezas assíncronas com relatórios de progresso reais e tratamento fino de exceções.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QThread

from src.modules.cleaning.temp_cleaner import analyze_temp_files, execute_temp_cleanup
from src.modules.cleaning.thumbnail_cleaner import analyze_thumbnail_cache, clean_thumbnail_cache
from src.modules.cleaning.storage_analyzer import get_recycle_bin_info, empty_recycle_bin, get_storage_overview
from src.modules.cleaning.windows_update_cleaner import analyze_update_cache, clean_update_cache
from src.modules.reports.history_manager import log_operation_event
from src.core.progress_manager import ProgressReporter
from src.interface.dialogs.custom_dialogs import (
    CustomConfirmDialog, CustomMessageDialog, OperationResultDialog, CustomProgressDialog, show_toast
)

class CleaningTaskWorker(QThread):
    """Worker assíncrono genérico com propagação de callback de progresso real e tratamento de erros."""
    def __init__(self, reporter: ProgressReporter, task_func, kwargs=None, op_title: str = "Limpeza do Sistema"):
        super().__init__()
        self.reporter = reporter
        self.task_func = task_func
        self.kwargs = kwargs or {}
        self.op_title = op_title
        self.result = {}

    def run(self):
        self.reporter.start(self.op_title, "Iniciando processamento...", total_items=100)
        # Injeta callback se a função suportar
        if "progress_callback" not in self.kwargs:
            self.kwargs["progress_callback"] = self.reporter.as_callback()

        try:
            res = self.task_func(**self.kwargs)
            self.result = res if isinstance(res, dict) else {"success": True, "result": res}
            
            if self.reporter.is_cancelled:
                self.reporter.cancel()
                return

            if isinstance(res, dict) and not res.get("success", True):
                self.reporter.fail(res.get("message", "A operação falhou."))
            else:
                self.reporter.complete(self.result)
        except Exception as e:
            self.result = {"success": False, "message": str(e)}
            self.reporter.fail(f"Erro durante a execução: {e}")

class CleaningPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_storage_disks_only()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Cabeçalho
        lbl_title = QLabel("LIMPEZA INTELIGENTE E ARMAZENAMENTO")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Remoção controlada de arquivos temporários e gerenciamento de espaço sob demanda")
        lbl_sub.setProperty("class", "PageSubtitle")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # Seção de Cards de Limpeza
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        self.card_temp = self._create_clean_card(
            "Arquivos Temporários",
            "Pronto para análise",
            "Filtro: >= 7 dias",
            "Analisar e Limpar",
            self._handle_temp_clean
        )
        cards_layout.addWidget(self.card_temp)

        self.card_thumb = self._create_clean_card(
            "Cache de Miniaturas",
            "Pronto para limpeza",
            "Thumbnails Explorer",
            "Limpar Miniaturas",
            self._handle_thumb_clean
        )
        cards_layout.addWidget(self.card_thumb)

        self.card_bin = self._create_clean_card(
            "Lixeira do Sistema",
            "Pronto para consulta",
            "Itens descartados",
            "Verificar e Esvaziar",
            self._handle_recycle_bin
        )
        cards_layout.addWidget(self.card_bin)

        self.card_wu = self._create_clean_card(
            "Cache Windows Update",
            "Manutenção controlada",
            "SoftwareDistribution",
            "Limpeza Segura",
            self._handle_wu_clean
        )
        cards_layout.addWidget(self.card_wu)

        layout.addLayout(cards_layout)

        # Tabela de Visão Geral do Armazenamento
        lbl_disks_title = QLabel("UNIDADES DE DISCO DETECTADAS")
        lbl_disks_title.setProperty("class", "SectionTitle")
        layout.addWidget(lbl_disks_title)

        self.table_disks = QTableWidget()
        self.table_disks.setColumnCount(5)
        self.table_disks.setHorizontalHeaderLabels([
            "Ponto de Montagem", "Dispositivo", "Tamanho Total", "Espaço Livre", "Sistema de Arquivos"
        ])
        self.table_disks.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_disks.verticalHeader().setVisible(False)
        self.table_disks.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_disks.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_disks.setFixedHeight(210)
        layout.addWidget(self.table_disks)

        layout.addStretch()

    def _create_clean_card(self, title: str, val_text: str, sub_text: str, btn_text: str, on_click) -> QFrame:
        card = QFrame()
        card.setProperty("class", "CardFrame")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(18, 18, 18, 18)
        c_layout.setSpacing(10)

        lbl_t = QLabel(title)
        lbl_t.setProperty("class", "CardTitle")
        c_layout.addWidget(lbl_t)

        card.lbl_v = QLabel(val_text)
        card.lbl_v.setStyleSheet("font-size: 19px; font-weight: 800; color: #00d2ff;")
        c_layout.addWidget(card.lbl_v)

        card.lbl_s = QLabel(sub_text)
        card.lbl_s.setStyleSheet("font-size: 12px; color: #64748b;")
        c_layout.addWidget(card.lbl_s)

        btn = QPushButton(btn_text)
        btn.setProperty("class", "PrimaryButton")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(on_click)
        c_layout.addWidget(btn)

        return card

    def _load_storage_disks_only(self):
        """Carrega e popula a tabela de unidades de armazenamento montadas."""
        try:
            disks = get_storage_overview()
            self.table_disks.setRowCount(len(disks))
            for i, d in enumerate(disks):
                self.table_disks.setItem(i, 0, QTableWidgetItem(str(d["mountpoint"])))
                self.table_disks.setItem(i, 1, QTableWidgetItem(str(d["device"])))
                self.table_disks.setItem(i, 2, QTableWidgetItem(f"{d['total_gb']} GB"))
                self.table_disks.setItem(i, 3, QTableWidgetItem(f"{d['free_gb']} GB ({100 - d['percent_used']:.0f}% livre)"))
                self.table_disks.setItem(i, 4, QTableWidgetItem(str(d["fstype"])))
        except Exception:
            pass

    def _handle_temp_clean(self):
        self.card_temp.lbl_v.setText("Analisando...")
        temp_info = analyze_temp_files(min_age_days=7)
        rec_mb = temp_info["reclaimable_mb"]
        count = temp_info["eligible_files_count"]
        self.card_temp.lbl_v.setText(f"~{rec_mb} MB")
        self.card_temp.lbl_s.setText(f"{count} arquivos (>= 7 dias)")

        confirm = CustomConfirmDialog(
            parent=self,
            title="Limpeza de Arquivos Temporários",
            message=f"Foram identificados {count} arquivos antigos sem modificação há pelo menos 7 dias.\n"
                    f"Espaço total a ser recuperado: ~{rec_mb} MB.\n\n"
                    "Deseja prosseguir com a remoção segura?",
            confirm_text="Limpar Agora",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            reporter = ProgressReporter()
            worker = CleaningTaskWorker(
                reporter,
                execute_temp_cleanup,
                {"min_age_days": 7, "dry_run": False},
                op_title="Limpeza de Arquivos Temporários"
            )
            dlg = CustomProgressDialog(self, reporter, "Removendo Arquivos Temporários", can_cancel=True)
            worker.start()
            dlg.exec()
            worker.wait()

            res = worker.result
            if res.get("success"):
                freed = res.get("deleted_mb", 0)
                files = res.get("deleted_files_count", 0)
                log_operation_event("Limpeza de Temporários", "Concluído", f"{files} arquivos removidos", freed, files)

                OperationResultDialog(
                    self,
                    title="Limpeza de Temporários Concluída",
                    message="Os arquivos obsoletos foram removidos com sucesso.",
                    stats={
                        "Arquivos Excluídos": files,
                        "Espaço Liberado": f"{freed} MB",
                        "Em Uso Ignorados": res.get("skipped_locked_count", 0)
                    }
                ).exec()

                self._load_storage_disks_only()
                show_toast(self, f"{freed} MB liberados com sucesso!", "success")
            else:
                CustomMessageDialog(self, "Falha na Limpeza", res.get("message", "A operação não foi concluída."), dialog_type="error").exec()

    def _handle_thumb_clean(self):
        thumb_info = analyze_thumbnail_cache()
        rec_mb = thumb_info["reclaimable_mb"]
        count = thumb_info["count"]

        confirm = CustomConfirmDialog(
            parent=self,
            title="Limpeza de Cache de Miniaturas",
            message=f"Foram encontrados {count} arquivos de cache de miniaturas (~{rec_mb} MB).\n\n"
                    "O Windows recriará as miniaturas automaticamente sob demanda.\n"
                    "Deseja limpar os arquivos desbloqueados?",
            confirm_text="Limpar Miniaturas",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            reporter = ProgressReporter()
            worker = CleaningTaskWorker(
                reporter,
                clean_thumbnail_cache,
                {"dry_run": False},
                op_title="Limpeza de Miniaturas"
            )
            dlg = CustomProgressDialog(self, reporter, "Limpando Miniaturas", can_cancel=True)
            worker.start()
            dlg.exec()
            worker.wait()

            res = worker.result
            if res.get("success"):
                freed = res.get("freed_mb", 0)
                c = res.get("deleted_count", 0)
                log_operation_event("Limpeza de Miniaturas", "Concluído", f"{c} arquivos removidos", freed, c)

                OperationResultDialog(
                    self,
                    title="Miniaturas Limpas",
                    message="O cache de miniaturas foi redefinido.",
                    stats={
                        "Miniaturas Excluídas": c,
                        "Espaço Liberado": f"{freed} MB"
                    }
                ).exec()

                self._load_storage_disks_only()
                show_toast(self, "Cache de miniaturas limpo!", "success")
            else:
                CustomMessageDialog(self, "Falha na Limpeza", res.get("message", "Erro ao limpar miniaturas."), dialog_type="error").exec()

    def _handle_recycle_bin(self):
        bin_info = get_recycle_bin_info()
        self.card_bin.lbl_v.setText(f"{bin_info['size_mb']} MB")
        self.card_bin.lbl_s.setText(f"{bin_info['num_items']} itens")

        confirm = CustomConfirmDialog(
            parent=self,
            title="Esvaziar Lixeira do Windows",
            message=f"A Lixeira contém {bin_info['num_items']} itens ocupando ~{bin_info['size_mb']} MB.\n\n"
                    "Atenção: Os arquivos descartados serão removidos permanentemente. Esta ação não pode ser desfeita.",
            confirm_text="Esvaziar Permanentemente",
            cancel_text="Cancelar",
            is_dangerous=True
        )
        if confirm.exec():
            res = empty_recycle_bin(user_confirmed=True)
            if res.get("success"):
                freed = res.get("freed_mb", 0)
                items = res.get("items_cleared", 0)
                log_operation_event("Esvaziamento da Lixeira", "Concluído", f"{items} itens removidos", freed, items)

                OperationResultDialog(
                    self,
                    title="Lixeira Esvaziada",
                    message="Todos os itens descartados foram removidos do disco.",
                    stats={
                        "Itens Excluídos": items,
                        "Espaço Liberado": f"{freed} MB"
                    }
                ).exec()

                self.card_bin.lbl_v.setText("0.0 MB")
                self.card_bin.lbl_s.setText("0 itens")
                show_toast(self, "Lixeira esvaziada com sucesso!", "success")
            else:
                CustomMessageDialog(self, "Aviso", res.get("message", "Falha ao esvaziar lixeira."), dialog_type="error").exec()
            self._load_storage_disks_only()

    def _handle_wu_clean(self):
        stat = analyze_update_cache()
        if stat.get("reboot_pending"):
            CustomMessageDialog(
                self,
                "Reinicialização Pendente",
                "Existe uma reinicialização pendente pelo Windows Update.\nReinicie o computador antes de realizar a manutenção do cache.",
                dialog_type="warning"
            ).exec()
            return

        if stat.get("update_in_progress"):
            CustomMessageDialog(
                self,
                "Atualização em Andamento",
                f"A manutenção foi bloqueada com segurança:\n{stat.get('update_block_reason')}",
                dialog_type="warning"
            ).exec()
            return

        confirm = CustomConfirmDialog(
            parent=self,
            title="Limpeza de Cache do Windows Update (Nível 2)",
            message=f"Cache identificado: ~{stat.get('total_mb')} MB ({stat.get('file_count')} arquivos em {stat.get('dir_count')} pastas).\n\n"
                    "Os serviços de atualização serão pausados com verificação de integridade, o diretório de downloads temporários será limpo "
                    "e os serviços serão restabelecidos imediatamente.\n\nDeseja prosseguir?",
            confirm_text="Executar Manutenção",
            cancel_text="Cancelar",
            is_dangerous=False
        )
        if confirm.exec():
            reporter = ProgressReporter()
            worker = CleaningTaskWorker(
                reporter,
                clean_update_cache,
                {"user_confirmed": True},
                op_title="Limpeza do Cache Windows Update"
            )
            dlg = CustomProgressDialog(self, reporter, "Limpando Cache do Windows Update", can_cancel=False)
            worker.start()
            dlg.exec()
            worker.wait()

            res = worker.result
            if res.get("success"):
                freed = res.get("freed_mb", 0)
                log_operation_event("Limpeza Windows Update", "Concluído", res.get("message", ""), freed)

                OperationResultDialog(
                    self,
                    title="Cache do Windows Update Limpo",
                    message="Os arquivos residuais de download foram excluídos e os serviços restabelecidos.",
                    stats={
                        "Espaço Liberado": f"{freed} MB",
                        "Arquivos Removidos": res.get("deleted_files", 0),
                        "Pastas Removidas": res.get("deleted_dirs", 0)
                    }
                ).exec()
                show_toast(self, "Cache do Windows Update limpo!", "success")
            else:
                CustomMessageDialog(self, "Falha na Limpeza", res.get("message", "Falha ao limpar cache."), dialog_type="error").exec()
            self._load_storage_disks_only()
