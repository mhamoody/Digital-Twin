from __future__ import annotations
import os,time
from dataclasses import dataclass
@dataclass(frozen=True)
class ResearchRuntime:
    endpoint:str|None
    model_name:str|None
    generation:dict
class ResearchModelAdapter:
    def __init__(self, endpoint=None, model_name=None, generation=None):
        self.runtime=ResearchRuntime(endpoint or os.getenv("DIGITAL_TWIN_RESEARCH_MODEL_URL"),model_name or os.getenv("DIGITAL_TWIN_RESEARCH_MODEL_NAME"),generation or {"temperature":0.0,"seed":42})
    def generate(self, case):
        if not self.runtime.endpoint or not self.runtime.model_name:
            raise RuntimeError("BLOCKED BY MODEL ACCESS")
        raise RuntimeError("BLOCKED BY MODEL ACCESS: no approved research client configured")
