"""
Testes unitários do sistema de progresso e diálogos personalizados.
"""
from src.core.progress_manager import ProgressReporter, OperationState, OperationProgressManager

def test_progress_reporter_lifecycle():
    reporter = ProgressReporter()
    assert not reporter.is_cancelled

    started_events = []
    reporter.started.connect(lambda op, step, tot: started_events.append((op, step, tot)))
    reporter.start("Operação Teste", "Iniciando...", total_items=50)

    assert len(started_events) == 1
    assert started_events[0][0] == "Operação Teste"
    assert started_events[0][2] == 50

    progress_events = []
    reporter.progress_changed.connect(lambda cur, tot, desc, pct: progress_events.append((cur, tot, pct)))
    reporter.update(current=25, total=50, step_desc="Passo intermediário")

    assert len(progress_events) == 1
    assert progress_events[0][0] == 25
    assert progress_events[0][2] == 50.0  # 25/50 = 50%

    completed_events = []
    reporter.finished.connect(lambda res: completed_events.append(res))
    reporter.complete({"itens": 50})

    assert len(completed_events) == 1
    assert completed_events[0]["itens"] == 50
    assert "elapsed_seconds" in completed_events[0]

def test_progress_cancellation():
    reporter = ProgressReporter()
    reporter.start("Teste Cancelamento")
    assert not reporter.is_cancelled
    reporter.cancel()
    assert reporter.is_cancelled
