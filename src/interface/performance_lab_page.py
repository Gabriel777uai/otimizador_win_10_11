"""
Página PERFORMANCE LAB - ALTUS PC OPTIMIZER.
Laboratório de telemetria de alto nível, benchmark com PresentMon,
comparação de antes/depois da otimização e exportação de relatórios técnicos.
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt, QThread, QTimer

from src.modules.performance.presentmon_collector import is_presentmon_available, PresentMonSession
from src.modules.performance.benchmark_manager import (
    load_all_benchmarks, save_benchmark_run, compare_benchmarks
)
from src.modules.performance.report_exporter import export_benchmark_to_csv, export_benchmark_to_html
from src.modules.gaming.game_detection import find_running_game_process
from src.core.progress_manager import ProgressReporter
from src.interface.dialogs.custom_dialogs import (
    CustomMessageDialog, CustomProgressDialog, OperationResultDialog, show_toast
)

class BenchmarkCaptureWorker(QThread):
    def __init__(self, reporter: ProgressReporter, target_proc: str, duration_sec: int, tag: str, game_name: str):
        super().__init__()
        self.reporter = reporter
        self.target_proc = target_proc
        self.duration_sec = duration_sec
        self.tag = tag
        self.game_name = game_name
        self.result = {}

    def run(self):
        self.reporter.start("Performance Lab", f"Iniciando captura de telemetria para {self.target_proc}...", total_items=self.duration_sec)
        session = PresentMonSession(self.target_proc)
        started, msg = session.start_capture(duration_seconds=self.duration_sec)
        if not started:
            self.reporter.fail(msg)
            self.result = {"has_data": False, "error": msg}
            return

        # Acompanha o tempo de captura
        import time
        start_t = time.time()
        while time.time() - start_t < self.duration_sec:
            if self.reporter.is_cancelled:
                session.stop_capture()
                self.reporter.cancel()
                return
            elapsed = int(time.time() - start_t)
            self.reporter.update(elapsed, self.duration_sec, f"Capturando métricas de quadros ({elapsed}/{self.duration_sec}s)...")
            time.sleep(1)

        self.reporter.update(self.duration_sec, self.duration_sec, "Processando dados de frametime...")
        metrics = session.stop_capture()
        self.result = metrics

        if metrics.get("has_data"):
            run_data = {
                "title": f"{self.game_name} ({self.tag})",
                "game": self.game_name,
                "process": self.target_proc,
                "tag": self.tag,
                "resolution": "Nativa",
                "settings": "Detectado",
                "metrics": metrics
            }
            save_benchmark_run(run_data)
            self.reporter.complete(metrics)
        else:
            self.reporter.fail(metrics.get("error", "Nenhum quadro válido capturado."))

class PerformanceLabPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_comparison = None
        self._init_ui()
        self._refresh_history()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Cabeçalho
        lbl_title = QLabel("PERFORMANCE LAB — TELEMETRIA & BENCHMARKS REAIS")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Medições verificáveis de FPS Médio, 1% Low, consistência de quadros e comparação de perfis")
        lbl_sub.setProperty("class", "PageSubtitle")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # Card de Status do PresentMon
        has_pmon = is_presentmon_available()
        status_card = QFrame()
        status_card.setProperty("class", "CardFrame")
        sc_l = QHBoxLayout(status_card)
        sc_l.setContentsMargins(16, 12, 16, 12)

        lbl_pmon_icon = QLabel("📊" if has_pmon else "ℹ️")
        lbl_pmon_icon.setStyleSheet("font-size: 22px;")
        sc_l.addWidget(lbl_pmon_icon)

        sc_txt = QVBoxLayout()
        sc_txt.setSpacing(2)
        lbl_pmon_t = QLabel("MOTOR DE TELEMETRIA: INTEL PRESENTMON (ETW)")
        lbl_pmon_t.setProperty("class", "CardTitle")
        pmon_desc = (
            "PresentMon ativo e pronto para capturas de precisão em DirectX e Vulkan."
            if has_pmon else
            "Binário opcional PresentMon.exe não localizado em resources/bin. As sessões usarão telemetria de recursos do Windows."
        )
        lbl_pmon_d = QLabel(pmon_desc)
        lbl_pmon_d.setProperty("class", "CardSub")
        sc_txt.addWidget(lbl_pmon_t)
        sc_txt.addWidget(lbl_pmon_d)
        sc_l.addLayout(sc_txt)
        sc_l.addStretch()

        layout.addWidget(status_card)

        # Painel de Captura de Benchmark
        bench_frame = QFrame()
        bench_frame.setProperty("class", "CardFrame")
        bf_l = QVBoxLayout(bench_frame)
        lbl_cap_t = QLabel("NOVA CAPTURA DE BENCHMARK")
        lbl_cap_t.setProperty("class", "SectionTitle")
        bf_l.addWidget(lbl_cap_t)

        controls_row = QHBoxLayout()
        lbl_g = QLabel("Jogo / Processo:")
        lbl_g.setStyleSheet("color: #94a3b8;")
        controls_row.addWidget(lbl_g)

        self.txt_proc = QLineEdit("game.exe")
        self.txt_proc.setFixedWidth(160)
        controls_row.addWidget(self.txt_proc)

        lbl_dur = QLabel("Duração:")
        lbl_dur.setStyleSheet("color: #94a3b8;")
        controls_row.addWidget(lbl_dur)

        self.combo_dur = QComboBox()
        self.combo_dur.addItems(["15 segundos", "30 segundos", "60 segundos"])
        self.combo_dur.setCurrentIndex(1)
        self.combo_dur.setFixedWidth(130)
        controls_row.addWidget(self.combo_dur)

        lbl_type = QLabel("Tipo:")
        lbl_type.setStyleSheet("color: #94a3b8;")
        controls_row.addWidget(lbl_type)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["Linha de Base (Original)", "Com Otimização ALTUS"])
        self.combo_type.setFixedWidth(190)
        controls_row.addWidget(self.combo_type)

        btn_start_cap = QPushButton("▶ Iniciar Captura")
        btn_start_cap.setProperty("class", "PrimaryButton")
        btn_start_cap.clicked.connect(self._start_capture)
        controls_row.addWidget(btn_start_cap)
        controls_row.addStretch()

        bf_l.addLayout(controls_row)
        layout.addWidget(bench_frame)

        # Tabela de Histórico de Benchmarks
        lbl_hist_t = QLabel("HISTÓRICO DE BENCHMARKS SALVOS")
        lbl_hist_t.setProperty("class", "SectionTitle")
        layout.addWidget(lbl_hist_t)

        self.table_bench = QTableWidget()
        self.table_bench.setColumnCount(6)
        self.table_bench.setHorizontalHeaderLabels([
            "Identificação", "Jogo", "Data / Hora", "FPS Médio", "1% Low FPS", "Consistência"
        ])
        self.table_bench.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_bench.verticalHeader().setVisible(False)
        self.table_bench.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_bench.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_bench.setFixedHeight(170)
        layout.addWidget(self.table_bench)

        # Ações de Comparação e Exportação
        act_row = QHBoxLayout()
        btn_compare = QPushButton("⚖ Comparar 2 Sessões Selecionadas")
        btn_compare.setProperty("class", "SecondaryButton")
        btn_compare.clicked.connect(self._compare_selected)
        act_row.addWidget(btn_compare)

        btn_export_csv = QPushButton("📁 Exportar Comparativo (CSV)")
        btn_export_csv.setProperty("class", "SecondaryButton")
        btn_export_csv.clicked.connect(self._export_csv)
        act_row.addWidget(btn_export_csv)

        btn_export_html = QPushButton("🌐 Exportar Relatório Visual (HTML)")
        btn_export_html.setProperty("class", "PrimaryButton")
        btn_export_html.clicked.connect(self._export_html)
        act_row.addWidget(btn_export_html)
        act_row.addStretch()

        layout.addLayout(act_row)
        layout.addStretch()

    def _refresh_history(self):
        history = load_all_benchmarks()
        self.table_bench.setRowCount(len(history))
        for i, b in enumerate(history):
            m = b.get("metrics", {})
            self.table_bench.setItem(i, 0, QTableWidgetItem(str(b.get("title", "Run"))))
            self.table_bench.setItem(i, 1, QTableWidgetItem(str(b.get("game", "Desconhecido"))))
            self.table_bench.setItem(i, 2, QTableWidgetItem(str(b.get("timestamp", "-"))))
            self.table_bench.setItem(i, 3, QTableWidgetItem(f"{m.get('avg_fps', 0)} FPS"))
            self.table_bench.setItem(i, 4, QTableWidgetItem(f"{m.get('one_percent_low_fps', 0)} FPS"))
            self.table_bench.setItem(i, 5, QTableWidgetItem(f"{m.get('consistency_score_percent', 0)}%"))

    def _start_capture(self):
        proc = self.txt_proc.text().strip()
        if not proc:
            CustomMessageDialog(self, "Aviso", "Informe o nome do processo do jogo (ex: game.exe).", dialog_type="warning").exec()
            return

        dur_text = self.combo_dur.currentText()
        dur_sec = int(dur_text.split()[0])
        tag = self.combo_type.currentText()
        game_name = Path(proc).stem.capitalize()

        reporter = ProgressReporter()
        worker = BenchmarkCaptureWorker(reporter, proc, dur_sec, tag, game_name)
        dlg = CustomProgressDialog(self, reporter, f"Capturando Benchmark — {game_name}", can_cancel=True)
        worker.start()
        dlg.exec()
        worker.wait()

        self._refresh_history()
        res = worker.result
        if res.get("has_data"):
            OperationResultDialog(
                self,
                title="Captura de Benchmark Concluída",
                message=f"Telemetria registrada com sucesso para {game_name}.",
                stats={
                    "FPS Médio": f"{res.get('avg_fps')} FPS",
                    "1% Low FPS": f"{res.get('one_percent_low_fps')} FPS",
                    "0.1% Low": f"{res.get('zero_one_percent_low_fps')} FPS",
                    "Consistência": f"{res.get('consistency_score_percent')}%"
                }
            ).exec()
            show_toast(self, "Benchmark registrado com sucesso!", "success")
        else:
            CustomMessageDialog(self, "Falha na Captura", res.get("error", "Não foi possível coletar dados de telemetria."), dialog_type="error").exec()

    def _compare_selected(self):
        sel = self.table_bench.selectionModel().selectedRows()
        if len(sel) < 2:
            CustomMessageDialog(self, "Seleção Necessária", "Selecione pelo menos duas linhas na tabela de histórico para comparar.", dialog_type="info").exec()
            return

        history = load_all_benchmarks()
        idx1 = sel[0].row()
        idx2 = sel[1].row()
        if idx1 < len(history) and idx2 < len(history):
            b1 = history[idx1]
            b2 = history[idx2]
            comp = compare_benchmarks(b1, b2)
            self.current_comparison = comp

            fps_diff = comp["avg_fps"]["diff"]
            fps_pct = comp["avg_fps"]["pct_change"]
            one_pct = comp["one_percent_low_fps"]["pct_change"]
            c_pct = comp["consistency_score"]["pct_change"]

            OperationResultDialog(
                self,
                title="Resultado da Comparação de Desempenho",
                message=f"Comparação entre '{b1.get('title')}' e '{b2.get('title')}':",
                stats={
                    "Delta FPS Médio": f"{'+' if fps_diff > 0 else ''}{fps_diff} ({fps_pct}%)",
                    "Delta 1% Low": f"{'+' if one_pct > 0 else ''}{one_pct}%",
                    "Consistência": f"{'+' if c_pct > 0 else ''}{c_pct}%",
                    "Evolução": "Melhoria Comprovada" if comp["avg_fps"]["improved"] else "Inalterado/Regressão"
                }
            ).exec()

    def _export_csv(self):
        if not self.current_comparison:
            CustomMessageDialog(self, "Aviso", "Execute primeiro uma comparação entre dois benchmarks antes de exportar.", dialog_type="info").exec()
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Relatório CSV", "benchmark_comparativo.csv", "Arquivos CSV (*.csv)")
        if path:
            ok = export_benchmark_to_csv(self.current_comparison, Path(path))
            if ok:
                show_toast(self, "Relatório CSV exportado com sucesso!", "success")
            else:
                CustomMessageDialog(self, "Erro", "Falha ao gravar arquivo CSV.", dialog_type="error").exec()

    def _export_html(self):
        if not self.current_comparison:
            CustomMessageDialog(self, "Aviso", "Execute primeiro uma comparação entre dois benchmarks antes de exportar.", dialog_type="info").exec()
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Relatório HTML", "benchmark_comparativo.html", "Arquivos HTML (*.html)")
        if path:
            ok = export_benchmark_to_html(self.current_comparison, Path(path))
            if ok:
                show_toast(self, "Relatório HTML exportado com sucesso!", "success")
            else:
                CustomMessageDialog(self, "Erro", "Falha ao gravar arquivo HTML.", dialog_type="error").exec()
