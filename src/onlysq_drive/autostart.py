
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from .paths import ensure_base_dirs, logs_dir

DEFAULT_TASK_NAME = "OnlySQ Drive"


def _pythonw_path() -> str:
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe":
        candidate = exe.with_name("pythonw.exe")
        if candidate.exists():
            return str(candidate)
    return str(exe)


def _launcher_args() -> str:
    return "-m onlysq_drive.launcher mount-hidden"


def _current_user() -> str:
    domain = os.environ.get("USERDOMAIN")
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    if domain and user:
        return f"{domain}\\{user}"
    return user


def install_autostart_task(task_name: str = DEFAULT_TASK_NAME) -> None:
    user_id = _current_user()
    if not user_id:
        raise RuntimeError("Could not determine current user")
    pyw = _pythonw_path().replace("'", "''")
    args = _launcher_args().replace("'", "''")
    task_name_escaped = task_name.replace("'", "''")
    user_id_escaped = user_id.replace("'", "''")
    ps_script = textwrap.dedent(f"""
        $ErrorActionPreference = 'Stop'
        $action = New-ScheduledTaskAction -Execute '{pyw}' -Argument '{args}'
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User '{user_id_escaped}'
        $principal = New-ScheduledTaskPrincipal -UserId '{user_id_escaped}' -LogonType Interactive
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable
        Register-ScheduledTask -TaskName '{task_name_escaped}' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
    """)
    subprocess.run([
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        ps_script,
    ], check=True)


def uninstall_autostart_task(task_name: str = DEFAULT_TASK_NAME) -> None:
    task_name_escaped = task_name.replace("'", "''")
    ps_script = (
        "$ErrorActionPreference='Stop'; "
        f"if (Get-ScheduledTask -TaskName '{task_name_escaped}' -ErrorAction SilentlyContinue) "
        f"{{ Unregister-ScheduledTask -TaskName '{task_name_escaped}' -Confirm:$false }}"
    )
    subprocess.run([
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        ps_script,
    ], check=True)


def is_autostart_task_installed(task_name: str = DEFAULT_TASK_NAME) -> bool:
    task_name_escaped = task_name.replace("'", "''")
    ps_script = f"if (Get-ScheduledTask -TaskName '{task_name_escaped}' -ErrorAction SilentlyContinue) {{ exit 0 }} else {{ exit 1 }}"
    result = subprocess.run([
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        ps_script,
    ])
    return result.returncode == 0


def autostart_log_path() -> Path:
    ensure_base_dirs()
    return logs_dir() / "autostart.log"


def write_launch_log(message: str) -> None:
    ensure_base_dirs()
    path = autostart_log_path()
    with path.open("a", encoding="utf-8") as f:
        f.write(message)
        if not message.endswith("\n"):
            f.write("\n")
