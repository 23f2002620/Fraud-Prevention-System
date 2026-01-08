from __future__ import annotations
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional


@dataclass
class UserFeatures:
    window_end_epoch_ms: int
    txn_count_60s: int
    total_amount_60s: float
    avg_amount_60s: float


_lock = Lock()
_latest: Dict[str, UserFeatures] = {}


def upsert(user_id: str, feat: UserFeatures) -> None:
    with _lock:
        prev = _latest.get(user_id)
        # keep the newest window only
        if prev is None or feat.window_end_epoch_ms >= prev.window_end_epoch_ms:
            _latest[user_id] = feat


def get(user_id: str) -> Optional[UserFeatures]:
    with _lock:
        return _latest.get(user_id)
