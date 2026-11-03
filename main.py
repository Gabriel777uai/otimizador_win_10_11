"""
ALTUS PC OPTIMIZER — Sistema Profissional de Otimização e Manutenção do Windows.
Ponto de entrada da aplicação desktop e empacotamento PyInstaller.
"""
import sys
import os
import traceback

# Garante que o diretório do projeto esteja no sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.utils.logger import app_logger

def main():
    try:
        if "--auto-maintenance" in sys.argv:
            app_logger.info("Executando rotina de manutenção agendada de Nível 1 (silenciosa)...")
            from src.modules.cleaning.dns_cache_cleaner import flush_dns_cache
            from src.modules.cleaning.temp_cleaner import execute_temp_cleanup
            flush_dns_cache()
            execute_temp_cleanup(min_age_days=7, dry_run=False)
            app_logger.info("Manutenção agendada concluída com sucesso.")
            sys.exit(0)

        from src.core.application import AltusApplication
        app = AltusApplication()
        sys.exit(app.run())
    except Exception as e:
        err_msg = f"Erro fatal não tratado na inicialização: {e}\n{traceback.format_exc()}"
        try:
            app_logger.critical(err_msg)
        except Exception:
            pass
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Falha na inicialização do ALTUS PC OPTIMIZER:\n\n{e}\n\nConsulte os arquivos de log para mais detalhes.",
                "ALTUS PC OPTIMIZER — Erro de Inicialização",
                0x10  # MB_ICONERROR
            )
        except Exception:
            pass
        print(err_msg, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
