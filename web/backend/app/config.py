from dataclasses import dataclass
from pathlib import Path
import os

WORKSPACE = Path(os.environ.get('NOVEL_WORKSPACE', Path(__file__).resolve().parents[3])).resolve()


@dataclass(frozen=True)
class Settings:
    workspace: Path = WORKSPACE
    port: int = int(os.environ.get('NOVEL_PORT', '8765'))
    max_file_bytes: int = 2 * 1024 * 1024
    task_timeout: int = 600
    static_dir: Path | None = None

    @property
    def origins(self) -> list[str]:
        return [f'http://{host}:{port}' for host in ['localhost', '127.0.0.1'] for port in [self.port, 5173]]
