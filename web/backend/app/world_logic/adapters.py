"""Versioned adapter contract. Third-party code is never auto-loaded from YAML."""
from typing import Protocol,Callable
from .models import Experiment
class SolverAdapter(Protocol):
    extension_id:str
    version:str
    def run(self,definition:Experiment,timeout_seconds:int,cancelled:Callable[[],bool])->dict: ...
# Registration requires an audited source change plus a disposable worker, not an imported package name.
