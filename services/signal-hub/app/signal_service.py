"""Signal service (in-memory storage)."""

from threading import Lock
from typing import Dict, Optional

from libs.contracts import Signal


class SignalService:
    def __init__(self) -> None:
        self._store: Dict[str, Signal] = {}
        self._lock = Lock()

    def create_signal(self, signal: Signal) -> Signal:
        with self._lock:
            self._store[signal.signal_id] = signal
        return signal

    def get_signal(self, signal_id: str) -> Optional[Signal]:
        with self._lock:
            return self._store.get(signal_id)

    def update_signal(self, signal: Signal) -> Signal:
        with self._lock:
            self._store[signal.signal_id] = signal
        return signal
