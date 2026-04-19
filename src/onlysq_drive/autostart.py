from __future__ import annotations

import platform
import subprocess
import sys
import textwrap
from pathlib import Path

from .paths import ensure_base_dirs, logs_dir

IS_WINDOWS = platform.system() == "Windows"
DEFAULT_TASK_NAME = "OnlySQ Drive"

if IS_WINDOWS:
    import os

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
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps_script,
            ],
            check=True,
        )


    def uninstall_autostart_task(task_name: str = DEFAULT_TASK_NAME) -> None:
        task_name_escaped = task_name.replace("'", "''")
        ps_script = (
            "$ErrorActionPreference='Stop'; "
            f"if (Get-ScheduledTask -TaskName '{task_name_escaped}' -ErrorAction SilentlyContinue) "
            f"{{ Unregister-ScheduledTask -TaskName '{task_name_escaped}' -Confirm:$false }}"
        )
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps_script,
            ],
            check=True,
        )


    def is_autostart_task_installed(task_name: str = DEFAULT_TASK_NAME) -> bool:
        task_name_escaped = task_name.replace("'", "''")
        ps_script = (
            f"if (Get-ScheduledTask -TaskName '{task_name_escaped}' -ErrorAction SilentlyContinue) "
            "{ exit 0 } else { exit 1 }"
        )
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps_script,
            ]
        )
        return result.returncode == 0

else:
    SERVICE_NAME = "onlysq-drive"
    SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"
    SERVICE_FILE = SYSTEMD_USER_DIR / f"{SERVICE_NAME}.service"
    _DEVNULL = subprocess.DEVNULL


    def _python_executable() -> str:
        return sys.executable


    def _service_unit_content() -> str:
        python = _python_executable()
        return textwrap.dedent(
            f"""\
            [Unit]
            Description=OnlySQ Cloud Drive (FUSE mount)
            After=network-online.target
            Wants=network-online.target

            [Service]
            Type=simple
            ExecStart={python} -m onlysq_drive.launcher mount-hidden
            Restart=on-failure
            RestartSec=5

            [Install]
            WantedBy=default.target
            """
        )


    def _systemctl(*args: str, quiet: bool = False, must_succeed: bool = False) -> int:
        cmd = ["systemctl", "--user", *args]
        stdout = _DEVNULL if quiet else None
        stderr = _DEVNULL if quiet else None
        result = subprocess.run(cmd, stdout=stdout, stderr=stderr)
        if must_succeed and result.returncode != 0:
            raise RuntimeError(f"Command failed (exit {result.returncode}): {' '.join(cmd)}")
        return result.returncode


    def install_autostart_task(task_name: str = DEFAULT_TASK_NAME) -> None:
        SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
        SERVICE_FILE.write_text(_service_unit_content(), encoding="utf-8")
        _systemctl("daemon-reload", must_succeed=True)
        _systemctl("enable", SERVICE_NAME, must_succeed=True)
        _systemctl("start", SERVICE_NAME, quiet=True)


    def uninstall_autostart_task(task_name: str = DEFAULT_TASK_NAME) -> None:
        _systemctl("stop", SERVICE_NAME, quiet=True)
        _systemctl("disable", SERVICE_NAME, quiet=True)
        if SERVICE_FILE.exists():
            SERVICE_FILE.unlink()
        _systemctl("daemon-reload", quiet=True)


    def is_autostart_task_installed(task_name: str = DEFAULT_TASK_NAME) -> bool:
        result = subprocess.run(
            ["systemctl", "--user", "is-enabled", SERVICE_NAME],
            capture_output=True,
        )
        return result.returncode == 0


def autostart_log_path() -> Path:
    ensure_base_dirs()
    return logs_dir() / "autostart.log"
