import json
import shlex
from pathlib import Path

import paramiko


REMOTE_SCRIPT = "/opt/vpn-bot/add_vless_user.sh"


def provision_user(server, client_uuid: str, email: str, timeout: int = 20):
    key_path = Path(server["ssh_key"]).expanduser()

    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.RejectPolicy())

    ssh.connect(
        hostname=server["host"],
        username=server["ssh_user"],
        key_filename=str(key_path),
        timeout=timeout,
        banner_timeout=timeout,
        auth_timeout=timeout,
    )

    try:
        command = (
            f"{shlex.quote(REMOTE_SCRIPT)} "
            f"{shlex.quote(client_uuid)} "
            f"{shlex.quote(email)}"
        )

        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()

        if stdout.channel.recv_exit_status() != 0:
            raise RuntimeError(err or out or "remote provisioning failed")

        result = json.loads(out)

        if not result.get("vless_url"):
            raise RuntimeError("server did not return vless_url")

        return result
    finally:
        ssh.close()
