"""Persistent filament history for quick selection (macOS: ~/Library/Application Support)."""
from __future__ import annotations
import json, os, sys, time
from typing import List, Dict, Optional


def default_path() -> str:
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/AMSPlanner")
    else:
        base = os.path.expanduser("~/.amsplanner")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "filament_history.json")


class FilamentHistory:
    def __init__(self, path: Optional[str] = None):
        self.path = path or default_path()
        self.items: Dict[str, Dict] = {}
        if os.path.exists(self.path):
            with open(self.path) as f:
                self.items = json.load(f)

    def save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self.items, f, indent=2)

    def record(self, ftype: str, color: str, label: str = "") -> str:
        key = f"{ftype}:{color}"
        it = self.items.setdefault(key, {"type": ftype, "color": color, "label": label, "uses": 0})
        it["uses"] += 1
        it["last_used"] = time.strftime("%Y-%m-%d %H:%M")
        if label:
            it["label"] = label
        self.save()
        return key

    def quick_select(self, limit: int = 12) -> List[Dict]:
        """Most-used first, then most recent."""
        return sorted(({"key": k, **v} for k, v in self.items.items()),
                      key=lambda d: (-d["uses"], d.get("last_used", "")), reverse=False)[:limit]
