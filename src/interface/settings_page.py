"""
Página de Configurações, Preferências Visuais e Agendador do Windows - ALTUS PC OPTIMIZER.
Persistência real de preferências em settings.json e gerenciamento efetivo de agendamento via schtasks.exe.
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QCheckBox, QComboBox, QTimeEdit
)
from PySide6.QtCore import Qt, QTime
from PySide6.QtGui import QPixmap

from src.core.recovery_manager import create_system_restore_point
from src.core.config_manager import load_app_config, save_app_config
from src.modules.windows.task_scheduler import (
    get_scheduled_task_status, create_or_update_scheduled_task, delete_scheduled_task
)
from src.utils.logger import get_logs_dir, get_app_dir
from src.interface.dialogs.custom_dialogs import CustomConfirmDialog, CustomMessageDialog, show_toast

class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_app_config()
        self._init_ui()
        self._load_values()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Cabeçalho
        lbl_title = QLabel("CONFIGURAÇÕES E PREFERÊNCIAS DO SISTEMA")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Personalização de interface, agendamento no Windows Task Scheduler e parâmetros operacionais")
        lbl_sub.setProperty("class", "PageSubtitle")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # 1. Card Preferências Visuais e UI/UX
        f_visual = QFrame()
        f_visual.setProperty("class", "CardFrame")
        vl = QVBoxLayout(f_visual)
        vl.setSpacing(12)
        lbl_v_title = QLabel("PREFERÊNCIAS DE INTERFACE E EXPERIÊNCIA VISUAL")
        lbl_v_title.setProperty("class", "SectionTitle")
        vl.addWidget(lbl_v_title)

        v_sub = QLabel("Personalize o esquema de cores e o comportamento das transições visuais")
        v_sub.setProperty("class", "CardSub")
        vl.addWidget(v_sub)

        v_grid = QGridLayout()
        v_grid.setHorizontalSpacing(24)
        v_grid.setVerticalSpacing(8)

        # Coluna 1: Tema
        col_theme = QVBoxLayout()
        col_theme.setSpacing(6)
        lbl_theme = QLabel("Tema Visual:")
        lbl_theme.setStyleSheet("color: #e2e8f0; font-weight: 600;")
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Dark Navy (Padrão Altus)", "High Contrast Dark"])
        self.combo_theme.setFixedHeight(36)
        self.combo_theme.setMinimumWidth(240)
        col_theme.addWidget(lbl_theme)
        col_theme.addWidget(self.combo_theme)
        v_grid.addLayout(col_theme, 0, 0)

        # Coluna 2: Animações
        col_anim = QVBoxLayout()
        col_anim.setSpacing(6)
        lbl_anim = QLabel("Efeitos Visuais:")
        lbl_anim.setStyleSheet("color: #e2e8f0; font-weight: 600;")
        self.combo_anim = QComboBox()
        self.combo_anim.addItems(["Transições Suaves (Ativo)", "Desempenho Máximo (Sem Animações)"])
        self.combo_anim.setFixedHeight(36)
        self.combo_anim.setMinimumWidth(260)
        col_anim.addWidget(lbl_anim)
        col_anim.addWidget(self.combo_anim)
        v_grid.addLayout(col_anim, 0, 1)

        vl.addLayout(v_grid)

        self.chk_toasts = QCheckBox("Exibir notificações rápidas e discretas (Toasts) após ações")
        self.chk_toasts.setStyleSheet("color: #cbd5e1; font-weight: 500; margin-top: 6px;")
        vl.addWidget(self.chk_toasts)

        layout.addWidget(f_visual)

        # 2. Card Agendamento no Windows Task Scheduler
        f_sched = QFrame()
        f_sched.setProperty("class", "CardFrame")
        sl = QVBoxLayout(f_sched)
        sl.setSpacing(12)
        lbl_sched_t = QLabel("AGENDAMENTO DE MANUTENÇÃO AUTOMÁTICA (SCHTASKS)")
        lbl_sched_t.setProperty("class", "SectionTitle")
        sl.addWidget(lbl_sched_t)

        self.chk_sched = QCheckBox("Habilitar rotina periódica no Agendador de Tarefas do Windows")
        self.chk_sched.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: 600;")
        sl.addWidget(self.chk_sched)

        sched_grid = QGridLayout()
        sched_grid.setHorizontalSpacing(24)
        sched_grid.setVerticalSpacing(8)

        # Dia da semana
        col_dia = QVBoxLayout()
        col_dia.setSpacing(6)
        lbl_dia = QLabel("Dia da Semana:")
        lbl_dia.setStyleSheet("color: #e2e8f0; font-weight: 600;")
        self.combo_dia = QComboBox()
        self.combo_dia.addItems(["Domingo (SUN)", "Sábado (SAT)", "Segunda-feira (MON)", "Quarta-feira (WED)"])
        self.combo_dia.setFixedHeight(36)
        self.combo_dia.setMinimumWidth(200)
        col_dia.addWidget(lbl_dia)
        col_dia.addWidget(self.combo_dia)
        sched_grid.addLayout(col_dia, 0, 0)

        # Horário
        col_hora = QVBoxLayout()
        col_hora.setSpacing(6)
        lbl_hora = QLabel("Horário da Execução:")
        lbl_hora.setStyleSheet("color: #e2e8f0; font-weight: 600;")
        self.time_sched = QTimeEdit()
        self.time_sched.setTime(QTime(12, 0))
        self.time_sched.setFixedHeight(36)
        self.time_sched.setMinimumWidth(130)
        col_hora.addWidget(lbl_hora)
        col_hora.addWidget(self.time_sched)
        sched_grid.addLayout(col_hora, 0, 1)

        # Status do Agendador
        col_status = QVBoxLayout()
        col_status.setSpacing(6)
        lbl_st_h = QLabel("Status no Windows:")
        lbl_st_h.setStyleSheet("color: #e2e8f0; font-weight: 600;")
        self.lbl_sched_status = QLabel("Consultando Agendador...")
        self.lbl_sched_status.setStyleSheet("""
            color: #00d2ff;
            font-size: 12px;
            font-weight: bold;
            background-color: #070d19;
            border: 1px solid #1e3a5f;
            border-radius: 6px;
            padding: 8px 12px;
        """)
        self.lbl_sched_status.setFixedHeight(36)
        col_status.addWidget(lbl_st_h)
        col_status.addWidget(self.lbl_sched_status)
        sched_grid.addLayout(col_status, 0, 2)

        sl.addLayout(sched_grid)

        lbl_sched_note = QLabel("ℹ️ O agendamento executa exclusivamente operações seguras de Nível 1 (limpeza de temporários >= 7 dias e cache DNS). "
                                "Nunca agenda modificações críticas, reparos avançados ou reinicializações.")
        lbl_sched_note.setStyleSheet("color: #94a3b8; font-size: 12px; margin-top: 4px; line-height: 1.4;")
        lbl_sched_note.setWordWrap(True)
        sl.addWidget(lbl_sched_note)

        layout.addWidget(f_sched)

        # Botão Salvar Configurações
        save_box = QHBoxLayout()
        btn_save = QPushButton("💾 Salvar Configurações e Atualizar Agendador")
        btn_save.setProperty("class", "PrimaryButton")
        btn_save.setFixedHeight(38)
        btn_save.setFixedWidth(340)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._save_settings)
        save_box.addWidget(btn_save)
        save_box.addStretch()
        layout.addLayout(save_box)

        # 3. Card Ponto de Restauração
        f_rest = QFrame()
        f_rest.setProperty("class", "CardFrame")
        rl = QVBoxLayout(f_rest)
        lbl_rest_t = QLabel("PONTO DE RESTAURAÇÃO DO WINDOWS (SYSTEM RESTORE)")
        lbl_rest_t.setProperty("class", "SectionTitle")
        rl.addWidget(lbl_rest_t)
        r_sub = QLabel("Crie um instantâneo de segurança oficial do Windows antes de realizar manutenções.")
        r_sub.setProperty("class", "CardSub")
        rl.addWidget(r_sub)

        btn_create_restore = QPushButton("🛡️ Criar Ponto de Restauração Agora")
        btn_create_restore.setProperty("class", "SecondaryButton")
        btn_create_restore.setFixedHeight(38)
        btn_create_restore.setFixedWidth(280)
        btn_create_restore.setCursor(Qt.PointingHandCursor)
        btn_create_restore.clicked.connect(self._create_restore_point)
        rl.addWidget(btn_create_restore)

        layout.addWidget(f_rest)

        # 4. Card Sobre o ALTUS e Logotipo
        f_about = QFrame()
        f_about.setProperty("class", "CardFrame")
        al = QHBoxLayout(f_about)
        al.setSpacing(16)

        logo_path = Path(__file__).resolve().parent.parent / "resources" / "icons" / "logo_64.png"
        lbl_logo_about = QLabel()
        if logo_path.exists():
            lbl_logo_about.setPixmap(QPixmap(str(logo_path)).scaled(54, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lbl_logo_about.setStyleSheet("border: none;")
        al.addWidget(lbl_logo_about)

        about_text_box = QVBoxLayout()
        about_text_box.setSpacing(2)
        lbl_about_name = QLabel("ALTUS PC OPTIMIZER — Versão Profissional")
        lbl_about_name.setStyleSheet("color: #00d2ff; font-size: 15px; font-weight: 800; border: none;")
        lbl_about_desc = QLabel("Sistema Profissional de Otimização e Manutenção do Windows. Desenvolvido com Padrões de Segurança da Microsoft.")
        lbl_about_desc.setStyleSheet("color: #94a3b8; font-size: 12px; border: none;")
        lbl_about_paths = QLabel(f"Diretório de Dados: {get_app_dir()} | Logs: {get_logs_dir()}")
        lbl_about_paths.setStyleSheet("color: #64748b; font-size: 11px; border: none;")

        about_text_box.addWidget(lbl_about_name)
        about_text_box.addWidget(lbl_about_desc)
        about_text_box.addWidget(lbl_about_paths)
        al.addLayout(about_text_box)
        al.addStretch()

        layout.addWidget(f_about)
        layout.addStretch()

    def _load_values(self):
        # Carrega preferências salvas
        self.chk_toasts.setChecked(self.config.get("enable_toasts", True))
        self.chk_sched.setChecked(self.config.get("scheduled_maintenance_enabled", False))

        t_idx = self.combo_theme.findText(self.config.get("theme", ""))
        if t_idx >= 0:
            self.combo_theme.setCurrentIndex(t_idx)

        # Carrega dia e horário salvos
        s_day = self.config.get("scheduled_day", "SUN")
        for i in range(self.combo_dia.count()):
            if s_day in self.combo_dia.itemText(i):
                self.combo_dia.setCurrentIndex(i)
                break

        s_time = self.config.get("scheduled_time", "12:00")
        qt_time = QTime.fromString(s_time, "HH:mm")
        if qt_time.isValid():
            self.time_sched.setTime(qt_time)

        # Atualiza status da tarefa no Windows
        task_st = get_scheduled_task_status()
        if task_st["exists"]:
            self.lbl_sched_status.setText(f"Ativa | Próxima: {task_st['next_run']}")
        else:
            self.lbl_sched_status.setText("Nenhuma tarefa ativa")

    def _save_settings(self):
        self.config["theme"] = self.combo_theme.currentText()
        self.config["enable_animations"] = (self.combo_anim.currentIndex() == 0)
        self.config["enable_toasts"] = self.chk_toasts.isChecked()
        sched_enabled = self.chk_sched.isChecked()
        self.config["scheduled_maintenance_enabled"] = sched_enabled

        # Extrai dia e horário
        dia_raw = self.combo_dia.currentText()
        day_code = "SUN"
        if "SAT" in dia_raw: day_code = "SAT"
        elif "MON" in dia_raw: day_code = "MON"
        elif "WED" in dia_raw: day_code = "WED"

        time_str = self.time_sched.time().toString("HH:mm")
        self.config["scheduled_day"] = day_code
        self.config["scheduled_time"] = time_str

        save_app_config(self.config)

        # Aplica no Agendador do Windows
        if sched_enabled:
            res = create_or_update_scheduled_task(day_code, time_str)
            if res.get("success"):
                show_toast(self, "Configurações salvas e tarefa agendada no Windows!", "success")
            else:
                CustomMessageDialog(self, "Aviso do Agendador", res.get("message"), dialog_type="warning").exec()
        else:
            delete_scheduled_task()
            show_toast(self, "Configurações salvas e agendamento desativado.", "info")

        self._load_values()

    def _create_restore_point(self):
        confirm = CustomConfirmDialog(
            parent=self,
            title="Criar Ponto de Restauração",
            message="Deseja criar um Ponto de Restauração oficial no Windows agora?\n\n"
                    "Esta operação criará uma cópia dos arquivos do sistema e chaves essenciais para recuperação.",
            confirm_text="Criar Ponto",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            res = create_system_restore_point("Ponto Manual - Altus PC Optimizer")
            if res.get("success"):
                CustomMessageDialog(
                    self,
                    title="Ponto de Restauração Criado",
                    message="O ponto de restauração foi registrado com êxito no Windows.",
                    dialog_type="success"
                ).exec()
                show_toast(self, "Ponto de restauração criado!", "success")
            else:
                CustomMessageDialog(
                    self,
                    title="Aviso de Restauração",
                    message=res.get("message", "A proteção de sistema na unidade C: pode estar desativada nas configurações do Windows."),
                    dialog_type="warning"
                ).exec()
