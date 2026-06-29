import json
import os
from datetime import datetime
from typing import Any, Dict, List

class AgentMemory:
    def __init__(self, memory_path: str = "./knowledge_base/memory.json"):
        self.memory_path = memory_path
        self.sessions: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r") as f:
                    self.sessions = json.load(f)
            except Exception:
                self.sessions = []

    def save(self, project_id: str, summary: Dict[str, Any]):
        entry = {
            "project_id": project_id,
            "timestamp": datetime.now().isoformat(),
            "summary": summary
        }
        self.sessions.append(entry)
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        with open(self.memory_path, "w") as f:
            json.dump(self.sessions, f, indent=2, default=str)

    def get_past_sessions(self) -> List[Dict]:
        return self.sessions

    def get_last_session(self) -> Dict:
        if self.sessions:
            return self.sessions[-1]
        return {}