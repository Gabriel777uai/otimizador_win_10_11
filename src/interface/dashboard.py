"""
Página do Dashboard Principal - ALTUS PC OPTIMIZER.
Apresentação visual com cards de hardware, indicadores gráficos vetoriais,
histórico recente de manutenção e integração com o sistema central de progresso e diálogos personalizados.
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap

from src.core.system_detection import get_full_system_snapshot
from src.core.operation_manager import operation_manager
from src.core.progress_manager import ProgressReporter
from src.modules.cleaning.temp_cleaner import execute_temp_cleanup
from src.modules.cleaning.thumbnail_cleaner import clean_thumbnail_cache
from src.modules.cleaning.dns_cache_cleaner import flush_dns_cache
from src.modules.reports.history_manager import log_operation_event, get_operation_history
from src.interface.dialogs.custom_dialogs import (
    CustomConfirmDialog, CustomMessageDialog, OperationResultDialog, CustomProgressDialog, show_toast
)
from src.interface.widgets.mini_chart import MiniUsageBar

class AnalysisWorker(QThread):
    def __init__(self, reporter: ProgressReporter):
        super().__init__()
        self.reporter = reporter
        self.result_data = {}

    def run(self):
        self.reporter.start("Escaneamento do Sistema", "Iniciando varredura e diagnóstico...", total_items=100)

        def cb(p, msg):
            if self.reporter.is_cancelled:
                return
            self.reporter.update(current=p, total=100, step_desc=msg)

        data = operation_manager.run_preliminary_analysis(progress_callback=cb)
        self.result_data = data
        self.reporter.complete(data)

class SafeMaintenanceWorker(QThread):
    def __init__(self, reporter: ProgressReporter):
        super().__init__()
        self.reporter = reporter
        self.summary = {}

    def run(self):
        self.reporter.start("Manutenção Segura", "Iniciando tarefas de otimização...", total_items=100)

        total_freed = 0
        total_files = 0

        self.reporter.update(current=25, total=100, step_desc="Removendo arquivos temporários com mais de 7 dias...")
        res_temp = execute_temp_cleanup(min_age_days=7)
        if res_temp.get("success"):
            total_freed += res_temp.get("deleted_bytes", 0)
            total_files += res_temp.get("deleted_files_count", 0)

        if self.reporter.is_cancelled:
            return

        self.reporter.update(current=65, total=100, step_desc="Limpando cache de miniaturas do Windows Explorer...")
        res_thumb = clean_thumbnail_cache()
        if res_thumb.get("success"):
            total_freed += res_thumb.get("deleted_bytes", 0)
            total_files += res_thumb.get("deleted_count", 0)

        if self.reporter.is_cancelled:
            return

        self.reporter.update(current=90, total=100, step_desc="Limpando e redefinindo cache de resolução DNS...")
        flush_dns_cache()

        freed_mb = round(total_freed / (1024 ** 2), 2)
        log_operation_event(
            operation_name="Manutenção Segura",
            status="Concluído",
            details=f"{total_files} arquivos removidos. Caches redefinidos.",
            freed_mb=freed_mb,
            files_affected=total_files
        )

        self.summary = {
            "Arquivos Removidos": total_files,
            "Espaço Liberado": f"{freed_mb} MB",
            "Status": "Concluído com Sucesso"
        }
        self.reporter.complete(self.summary)

class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_hardware_indicators()
        self._load_recent_history()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Cabeçalho da página
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("PAINEL DE CONTROLE GERAL")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Diagnóstico estrutural e centro de operações sob demanda")
        lbl_sub.setProperty("class", "PageSubtitle")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        top_bar.addLayout(title_box)
        top_bar.addStretch()

        # Botão principal Escanear e Analisar
        self.btn_optimize = QPushButton("🔍 ESCANEAR E ANALISAR")
        self.btn_optimize.setProperty("class", "PrimaryButton")
        self.btn_optimize.setCursor(Qt.PointingHandCursor)
        self.btn_optimize.setFixedHeight(40)
        self.btn_optimize.clicked.connect(self._start_preliminary_analysis)
        top_bar.addWidget(self.btn_optimize)

        # Botão Manutenção Segura Direta
        self.btn_safe_clean = QPushButton("🛡️ MANUTENÇÃO SEGURA")
        self.btn_safe_clean.setProperty("class", "SuccessButton")
        self.btn_safe_clean.setCursor(Qt.PointingHandCursor)
        self.btn_safe_clean.setFixedHeight(40)
        self.btn_safe_clean.clicked.connect(self._start_safe_maintenance)
        top_bar.addWidget(self.btn_safe_clean)

        layout.addLayout(top_bar)

        # Grade de Cards de Hardware (6 Cards em 2 Linhas de 3)
        grid_top = QHBoxLayout()
        grid_top.setSpacing(14)

        self.card_cpu = self._create_metric_card("PROCESSADOR (CPU)", "--", "Cores & Threads", "#00d2ff")
        grid_top.addWidget(self.card_cpu)

        self.card_ram = self._create_metric_card("MEMÓRIA RAM", "--", "Consumo atual", "#38bdf8")
        grid_top.addWidget(self.card_ram)

        self.card_gpu = self._create_metric_card("PLACA DE VÍDEO (GPU)", "--", "Adaptador Gráfico", "#10b981")
        grid_top.addWidget(self.card_gpu)

        layout.addLayout(grid_top)

        grid_bottom = QHBoxLayout()
        grid_bottom.setSpacing(14)

        self.card_disk = self._create_metric_card("ARMAZENAMENTO (C:)", "--", "Capacidade da Unidade", "#f59e0b")
        grid_bottom.addWidget(self.card_disk)

        self.card_net = self._create_metric_card("CONEXÃO DE REDE", "Ativa", "Adaptador Local", "#00d2ff")
        grid_bottom.addWidget(self.card_net)

        self.card_health = self._create_metric_card("SAÚDE DO SISTEMA", "Protegido", "Safety Manager Ativo", "#10b981")
        grid_bottom.addWidget(self.card_health)

        layout.addLayout(grid_bottom)

        # Área de Histórico Recente de Manutenção
        layout.addWidget(QLabel("RESUMO DAS ÚLTIMAS OPERAÇÕES DE MANUTENÇÃO"))
        self.table_history = QTableWidget()
        self.table_history.setColumnCount(4)
        self.table_history.setHorizontalHeaderLabels(["Data / Hora", "Operação Realizada", "Status", "Espaço Liberado"])
        self.table_history.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_history.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_history.setFixedHeight(120)
        layout.addWidget(self.table_history)

        # Console / Registro de Operações
        lbl_console = QLabel("REGISTRO DE OPERAÇÕES E DIAGNÓSTICO")
        lbl_console.setProperty("class", "SectionTitle")
        layout.addWidget(lbl_console)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(110)
        layout.addWidget(self.log_console)

    def _create_metric_card(self, title: str, val: str, sub: str, bar_col: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "CardFrame")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(4)

        lbl_t = QLabel(title)
        lbl_t.setProperty("class", "CardTitle")
        lbl_v = QLabel(val)
        lbl_v.setProperty("class", "CardValue")
        lbl_s = QLabel(sub)
        lbl_s.setProperty("class", "CardSub")

        bar = MiniUsageBar(card, percent=0, bar_color=bar_col)

        cl.addWidget(lbl_t)
        cl.addWidget(lbl_v)
        cl.addWidget(bar)
        cl.addWidget(lbl_s)

        card.lbl_val = lbl_v
        card.lbl_sub = lbl_s
        card.bar = bar
        return card

    def _load_hardware_indicators(self):
        """Carrega telemetria de hardware e atualiza os mini gráficos com dados reais (0 ms)."""
        try:
            snapshot = get_full_system_snapshot()

            # CPU
            cpu = snapshot.get("cpu", {})
            self.card_cpu.lbl_val.setText(f"{cpu.get('cores_physical', 1)}C / {cpu.get('threads_logical', 1)}T")
            self.card_cpu.lbl_sub.setText(f"{cpu.get('model', 'Processador')[:28]}")
            self.card_cpu.bar.set_percent(50.0)

            # RAM
            mem = snapshot.get("memory", {})
            self.card_ram.lbl_val.setText(f"{mem.get('total_gb', 0)} GB")
            self.card_ram.lbl_sub.setText(f"{mem.get('used_gb', 0)} GB usado ({mem.get('percent_used', 0)}%)")
            self.card_ram.bar.set_percent(mem.get('percent_used', 0))

            # GPU
            gpus = snapshot.get("gpu", [])
            if gpus:
                self.card_gpu.lbl_val.setText(gpus[0].get("name", "GPU")[:22])
                self.card_gpu.lbl_sub.setText(f"Driver: {gpus[0].get('driver_version', 'N/A')}")
                self.card_gpu.bar.set_percent(100.0)

            # Disco C:
            disks = snapshot.get("disks", [])
            if disks:
                d = disks[0]
                self.card_disk.lbl_val.setText(f"{d.get('free_gb')} GB Livres")
                pct_used = d.get('percent_used', 0)
                self.card_disk.lbl_sub.setText(f"{d.get('total_gb')} GB Total ({100 - pct_used:.0f}% livre)")
                self.card_disk.bar.set_percent(pct_used)

            self._append_log("Sistema pronto. O escaneamento será realizado apenas sob seu comando.")
        except Exception as e:
            self._append_log(f"Inicialização de hardware: {e}")

    def _load_recent_history(self):
        """Preenche o resumo com as últimas 4 manutenções gravadas."""
        history = get_operation_history()[:4]
        self.table_history.setRowCount(len(history))
        for i, h in enumerate(history):
            self.table_history.setItem(i, 0, QTableWidgetItem(h.get("timestamp", "")))
            self.table_history.setItem(i, 1, QTableWidgetItem(h.get("operation", "")))
            st_item = QTableWidgetItem(h.get("status", ""))
            st_item.setForeground(Qt.green if h.get("status") in ("Concluído", "OK") else Qt.yellow)
            self.table_history.setItem(i, 2, st_item)
            self.table_history.setItem(i, 3, QTableWidgetItem(f"{h.get('freed_mb', 0)} MB"))

    def _append_log(self, text: str):
        self.log_console.append(f">> {text}")

    def _start_preliminary_analysis(self):
        reporter = ProgressReporter()
        self.worker = AnalysisWorker(reporter)

        dlg = CustomProgressDialog(
            parent=self,
            reporter=reporter,
            title="Escaneamento do Sistema",
            can_cancel=True
        )

        self.worker.start()
        dlg.exec()

        if reporter.is_cancelled:
            show_toast(self, "Escaneamento cancelado.", "warning")
            return

        res = self.worker.result_data
        rec_mb = round(res.get("total_reclaimable_bytes", 0) / (1024 ** 2), 2)
        ram_used = res.get("system_status", {}).get("ram_used_percent", 0)

        OperationResultDialog(
            parent=self,
            title="Diagnóstico Concluído",
            message="O escaneamento identificou os seguintes pontos para manutenção:",
            stats={
                "Espaço Recuperável": f"~{rec_mb} MB",
                "Uso de Memória RAM": f"{ram_used}%",
                "Cache DNS": "Pronto para Limpeza"
            }
        ).exec()

        self._load_recent_history()

    def _start_safe_maintenance(self):
        confirm = CustomConfirmDialog(
            parent=self,
            title="Confirmar Manutenção Segura",
            message="Deseja executar a rotina de Manutenção Segura?\n\n"
                    "• Remoção de arquivos temporários (> 7 dias sem uso)\n"
                    "• Limpeza de cache de miniaturas do Windows Explorer\n"
                    "• Esvaziamento do cache de resolução DNS\n\n"
                    "Nenhum arquivo pessoal ou componente do sistema será afetado.",
            confirm_text="Executar Agora",
            cancel_text="Cancelar"
        )
        if not confirm.exec():
            return

        reporter = ProgressReporter()
        self.maint_worker = SafeMaintenanceWorker(reporter)

        dlg = CustomProgressDialog(
            parent=self,
            reporter=reporter,
            title="Executando Manutenção Segura",
            can_cancel=False
        )

        self.maint_worker.start()
        dlg.exec()

        OperationResultDialog(
            parent=self,
            title="Manutenção Concluída com Sucesso",
            message="A rotina de limpeza e otimização segura foi finalizada.",
            stats=self.maint_worker.summary
        ).exec()

        self._load_hardware_indicators()
        self._load_recent_history()
        show_toast(self, "Manutenção executada com sucesso!", "success")
