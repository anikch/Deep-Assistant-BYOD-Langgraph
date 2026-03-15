import os
import subprocess
import tempfile
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    output_files: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.exit_code == 0


def execute_python(code: str, timeout: Optional[int] = None) -> ExecutionResult:
    """
    Execute Python code in a subprocess with timeout.
    Returns ExecutionResult.
    """
    if not settings.enable_code_execution:
        return ExecutionResult(
            stdout="",
            stderr="Code execution is disabled",
            exit_code=1,
        )

    timeout = timeout or settings.max_code_exec_seconds

    with tempfile.TemporaryDirectory() as tmpdir:
        code_file = os.path.join(tmpdir, "script.py")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            result = subprocess.run(
                ["python3", code_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
                env={
                    **os.environ,
                    "PYTHONPATH": "",
                    "PATH": "/usr/local/bin:/usr/bin:/bin",
                },
            )

            # Collect any output files created in tmpdir
            output_files = []
            for fname in os.listdir(tmpdir):
                if fname != "script.py":
                    output_files.append(os.path.join(tmpdir, fname))

            return ExecutionResult(
                stdout=result.stdout[:10000],  # Cap output
                stderr=result.stderr[:5000],
                exit_code=result.returncode,
                output_files=output_files,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Python execution timed out after {timeout}s")
            return ExecutionResult(
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds",
                exit_code=124,
            )
        except Exception as e:
            logger.error(f"Python execution failed: {e}")
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
            )


def execute_javascript(code: str, timeout: Optional[int] = None) -> ExecutionResult:
    """
    Execute JavaScript code with Node.js in a subprocess.
    """
    if not settings.enable_code_execution:
        return ExecutionResult(
            stdout="",
            stderr="Code execution is disabled",
            exit_code=1,
        )

    timeout = timeout or settings.max_code_exec_seconds

    with tempfile.TemporaryDirectory() as tmpdir:
        code_file = os.path.join(tmpdir, "script.js")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            result = subprocess.run(
                ["node", code_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
            )
            return ExecutionResult(
                stdout=result.stdout[:10000],
                stderr=result.stderr[:5000],
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                stdout="",
                stderr=f"JavaScript execution timed out after {timeout} seconds",
                exit_code=124,
            )
        except FileNotFoundError:
            return ExecutionResult(
                stdout="",
                stderr="Node.js not found. Please install Node.js.",
                exit_code=1,
            )
        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
            )
