"""
Local Workstation Code Sandbox for Shakil's Assistant (J.A.R.V.I.S.)
====================================================================
Safely executes Python, PowerShell, and Shell code snippets locally.
Features:
- Configurable subprocess execution timeout (default: 15s).
- Captures stdout, stderr, execution duration, and exit codes.
- Syntax validation before execution.
- Optional persistent artifact export to Desktop/Jarvis_Created_Files/.
"""

import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

DESKTOP_DIR = Path.home() / "Desktop" / "Jarvis_Created_Files"
DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TIMEOUT = 15  # seconds

def validate_syntax(code: str, language: str = "python") -> Dict[str, Any]:
    """Validates script syntax before execution."""
    lang = language.lower().strip()
    if lang in ["python", "py"]:
        try:
            compile(code, "<sandbox>", "exec")
            return {"valid": True, "error": None}
        except SyntaxError as e:
            return {"valid": False, "error": f"SyntaxError at line {e.lineno}: {e.msg}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    # For powershell and cmd, defer to execution engine
    return {"valid": True, "error": None}

def run_code(
    code: str,
    language: str = "python",
    timeout: int = DEFAULT_TIMEOUT,
    save_to_desktop: bool = False,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes a script snippet locally in an isolated subprocess.
    Returns:
        dict: {
            "success": bool,
            "stdout": str,
            "stderr": str,
            "exit_code": int,
            "duration_ms": float,
            "saved_file": Optional[str],
            "error": Optional[str]
        }
    """
    lang = language.lower().strip()
    if not code or not code.strip():
        return {
            "success": False,
            "stdout": "",
            "stderr": "No code provided for execution.",
            "exit_code": -1,
            "duration_ms": 0.0,
            "saved_file": None,
            "error": "Empty code payload"
        }

    # 1. Syntax check
    syntax_check = validate_syntax(code, lang)
    if not syntax_check["valid"]:
        return {
            "success": False,
            "stdout": "",
            "stderr": syntax_check["error"] or "Syntax validation failed.",
            "exit_code": 1,
            "duration_ms": 0.0,
            "saved_file": None,
            "error": syntax_check["error"]
        }

    # 2. Prepare file on disk
    ext = ".py" if lang in ["python", "py"] else ".ps1" if lang in ["powershell", "ps1"] else ".bat"
    saved_path_str = None

    if save_to_desktop:
        fname = filename or f"sandbox_script_{int(time.time())}{ext}"
        target_path = DESKTOP_DIR / fname
        target_path.write_text(code, encoding="utf-8")
        saved_path_str = str(target_path)
        script_file_path = target_path
        cleanup_needed = False
    else:
        temp_fd, temp_file_path = tempfile.mkstemp(suffix=ext, prefix="jarvis_sandbox_")
        os.close(temp_fd)
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write(code)
        script_file_path = Path(temp_file_path)
        cleanup_needed = True

    start_time = time.perf_counter()

    try:
        # Determine execution command
        if lang in ["python", "py"]:
            cmd = [sys.executable, str(script_file_path)]
        elif lang in ["powershell", "ps1"]:
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_file_path)]
        elif lang in ["bat", "cmd"]:
            cmd = ["cmd.exe", "/c", str(script_file_path)]
        else:
            cmd = [sys.executable, str(script_file_path)]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(DESKTOP_DIR)
        )

        duration = (time.perf_counter() - start_time) * 1000.0

        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "exit_code": proc.returncode,
            "duration_ms": round(duration, 2),
            "saved_file": saved_path_str,
            "error": None if proc.returncode == 0 else proc.stderr.strip() or f"Process exited with code {proc.returncode}"
        }

    except subprocess.TimeoutExpired:
        duration = (time.perf_counter() - start_time) * 1000.0
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds.",
            "exit_code": -1,
            "duration_ms": round(duration, 2),
            "saved_file": saved_path_str,
            "error": f"Timeout ({timeout}s exceeded)"
        }
    except Exception as e:
        duration = (time.perf_counter() - start_time) * 1000.0
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "duration_ms": round(duration, 2),
            "saved_file": saved_path_str,
            "error": str(e)
        }
    finally:
        if cleanup_needed and script_file_path.exists():
            try:
                script_file_path.unlink(missing_ok=True)
            except Exception:
                pass

def get_installed_packages() -> list:
    """Returns top installed python packages in the active environment."""
    try:
        import pkg_resources
        return sorted([f"{d.project_name}=={d.version}" for d in pkg_resources.working_set])
    except Exception:
        try:
            import importlib.metadata
            return sorted([f"{dist.metadata['Name']}=={dist.version}" for dist in importlib.metadata.distributions()])
        except Exception:
            return []
