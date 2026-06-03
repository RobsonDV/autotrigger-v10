"""
Motor de sequências — gerencia múltiplas sequências em paralelo.

- Registra triggers de keyword no FileMonitor para cada sequência habilitada
- Instancia SequenceRunner quando keyword é detectada
- Expõe callbacks de estado/tick para a UI
"""
import threading
from typing import Callable, Dict, Optional

from step_runner import StepRunner
from sequence_runner import SequenceRunner, RunnerState
from file_monitor import FileMonitor


class SequenceEngine:
    def __init__(self, config, player, file_monitor: FileMonitor):
        self._config = config
        self._file_monitor = file_monitor
        self._step_runner = StepRunner(player)
        self._player = player

        self._runners: Dict[str, SequenceRunner] = {}
        self._temp_kw_lock = threading.Lock()
        self._temp_kw_events: Dict[str, list] = {}

        self._log_fn: Callable = lambda msg, level="info": print(f"[Engine][{level}] {msg}")
        self._on_runner_update: Optional[Callable] = None  # (seq_id, state_name, step_idx)
        self._on_tick: Optional[Callable] = None           # (seq_id, step_idx, elapsed, total)

    # ── configuration ─────────────────────────────────────────────────────────

    def set_log(self, fn: Callable):
        self._log_fn = fn
        self._step_runner.set_log(fn)

    def set_on_runner_update(self, fn: Callable):
        """Callback: (seq_id: str, state_name: str, step_idx: int)"""
        self._on_runner_update = fn

    def set_on_tick(self, fn: Callable):
        """Callback: (seq_id: str, step_idx: int, elapsed: float, total: float)"""
        self._on_tick = fn

    def is_vlc_available(self) -> bool:
        return self._player.is_vlc_available()

    # ── monitor control ───────────────────────────────────────────────────────

    def start_monitor(self) -> bool:
        txt = self._config.get_global().get("txt_file_path", "")
        if not txt:
            self._log_fn("Caminho do arquivo TXT não configurado.", "error")
            return False
        ok = self._file_monitor.start(txt, log_callback=self._log_fn)
        if ok:
            self._register_all_triggers()
        return ok

    def stop_monitor(self):
        self._file_monitor.stop()

    def is_monitor_running(self) -> bool:
        return self._file_monitor.is_running()

    def reload_sequences(self):
        """Recarrega triggers após mudança na config. Chama após salvar configurações."""
        for seq in self._config.get_sequences():
            kw = seq.get("keyword_trigger", "").strip()
            if kw:
                self._file_monitor.unregister_keyword(kw)
        if self._file_monitor.is_running():
            self._register_all_triggers()

    # ── triggers ──────────────────────────────────────────────────────────────

    def _register_all_triggers(self):
        for seq in self._config.get_sequences():
            if seq.get("enabled", True) and seq.get("keyword_trigger", "").strip():
                self._register_trigger(seq)

    def _register_trigger(self, seq: dict):
        kw = seq["keyword_trigger"].strip()
        sid = seq["id"]
        self._file_monitor.register_keyword(
            kw, lambda _sid=sid: self._on_trigger(_sid)
        )

    # ── execution ─────────────────────────────────────────────────────────────

    def _on_trigger(self, seq_id: str):
        runner = self._runners.get(seq_id)
        if runner and runner.state == RunnerState.RUNNING:
            seq = self._config.get_sequence_by_id(seq_id)
            name = seq.get("name", seq_id) if seq else seq_id
            self._log_fn(f"'{name}' já em execução — gatilho ignorado.", "warn")
            return

        seq = self._config.get_sequence_by_id(seq_id)
        if not seq:
            return

        name = seq.get("name", seq_id)
        self._log_fn(f"🚀 Iniciando: '{name}'", "success")

        runner = SequenceRunner(seq, self._step_runner, self._log_fn)
        runner.set_keyword_waiter(self._make_keyword_waiter())
        runner.set_callbacks(
            on_state_change=lambda s, i, _id=seq_id: self._on_state(_id, s, i),
            on_tick=lambda i, e, t, _id=seq_id: self._on_runner_tick(_id, i, e, t),
        )
        self._runners[seq_id] = runner
        runner.start()

    def _make_keyword_waiter(self) -> Callable:
        """Retorna função que registra keyword temporária e retorna threading.Event."""
        def _waiter(keyword: str) -> threading.Event:
            kw = keyword.strip().upper()
            ev = threading.Event()
            with self._temp_kw_lock:
                if kw not in self._temp_kw_events:
                    self._temp_kw_events[kw] = []
                self._temp_kw_events[kw].append(ev)

            def _fire():
                with self._temp_kw_lock:
                    for e in self._temp_kw_events.pop(kw, []):
                        e.set()
                self._file_monitor.unregister_keyword(kw)

            self._file_monitor.register_keyword(kw, _fire)
            return ev

        return _waiter

    def _on_state(self, seq_id: str, state: RunnerState, step_idx: int):
        if self._on_runner_update:
            self._on_runner_update(seq_id, state.value, step_idx)

    def _on_runner_tick(self, seq_id: str, step_idx: int, elapsed: float, total: float):
        if self._on_tick:
            self._on_tick(seq_id, step_idx, elapsed, total)

    # ── control ───────────────────────────────────────────────────────────────

    def cancel(self, seq_id: str):
        runner = self._runners.get(seq_id)
        if runner:
            runner.cancel()

    def cancel_all(self):
        for runner in self._runners.values():
            runner.cancel()

    def get_runner(self, seq_id: str) -> Optional[SequenceRunner]:
        return self._runners.get(seq_id)
