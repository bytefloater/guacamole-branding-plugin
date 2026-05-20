#!/usr/bin/env python3
"""Compress the branding folder and deploy it to the Guacamole server."""

import json
import logging
import os
import shlex
import sys
import zipfile
from typing import Optional

import paramiko

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

EXCLUDED_NAMES = {".DS_Store", "__MACOSX", "Thumbs.db"}
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "deploy.json")


def load_config(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        log.error("Config file not found: %s", path)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        log.error("Invalid JSON in config file: %s", exc)
        sys.exit(1)


def compress_folder(folder_path: str, output_name: str) -> str:
    """Zip folder contents (no wrapper directory, no macOS detritus) and return the archive path."""
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        log.error("'%s' is not a directory.", folder_path)
        sys.exit(1)

    final_path = os.path.join(os.path.dirname(folder_path), output_name)
    with zipfile.ZipFile(final_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_NAMES]
            for filename in filenames:
                if filename in EXCLUDED_NAMES:
                    continue
                abs_path = os.path.join(dirpath, filename)
                arcname = os.path.relpath(abs_path, folder_path)
                zf.write(abs_path, arcname)
    return final_path


class RemoteServerSession:
    """Manages a persistent SSH + SFTP connection to a remote server."""

    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    def __enter__(self) -> "RemoteServerSession":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def connect(self) -> None:
        log.info("Connecting to %s:%d ...", self.host, self.port)
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(self.host, port=self.port, username=self.username, password=self.password)
        self._sftp = self._client.open_sftp()
        log.info("Connected.")

    def close(self) -> None:
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._client:
            self._client.close()
            self._client = None

    def run_command(self, *args: str) -> None:
        """Run a command on the remote host; args are shell-quoted via shlex.join."""
        assert self._client is not None, "Not connected"
        command = shlex.join(args)
        # Command is built via shlex.join; args are caller-controlled, not user-supplied.
        _, stdout, stderr = self._client.exec_command(command)  # nosec B601
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            log.info("Remote stdout: %s", out)
        if err:
            log.warning("Remote stderr: %s", err)
        if exit_code != 0:
            log.error("Remote command failed (exit %d): %s", exit_code, command)
            sys.exit(1)
        log.info("Remote command succeeded: %s", command)

    def file_exists(self, remote_path: str) -> bool:
        assert self._sftp is not None, "Not connected"
        try:
            self._sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def ensure_dir(self, remote_dir: str) -> None:
        assert self._sftp is not None, "Not connected"
        try:
            self._sftp.stat(remote_dir)
        except FileNotFoundError:
            log.info("Creating remote directory: %s", remote_dir)
            self._sftp.mkdir(remote_dir)

    def upload(self, local_path: str, remote_path: str, force_overwrite: bool = False) -> bool:
        """
        Upload local_path to remote_path.

        If the remote file already exists and force_overwrite is False, the user
        is prompted to confirm before proceeding. Returns True if the file was
        uploaded, False if the upload was skipped.
        """
        filename = os.path.basename(local_path)

        if self.file_exists(remote_path):
            if force_overwrite:
                log.info("Overwriting existing remote file: %s", remote_path)
            else:
                answer = input(
                    f"  '{remote_path}' already exists on {self.host}. Overwrite? [y/N] "
                ).strip().lower()
                if answer not in ("y", "yes"):
                    log.info("Upload of '%s' skipped by user.", filename)
                    return False

        assert self._sftp is not None, "Not connected"
        self.ensure_dir(remote_path.rsplit("/", 1)[0])
        self._sftp.put(local_path, remote_path)
        log.info("Uploaded '%s' -> %s:%s", filename, self.host, remote_path)
        return True


def main() -> None:
    cfg = load_config(CONFIG_PATH)
    srv = cfg["server"]

    folder          = cfg.get("folder", "./branding")
    output_name     = cfg.get("output_name", "branding.jar")
    keep_archive    = cfg.get("keep_archive", False)
    force_overwrite = cfg.get("force_overwrite", False)
    remote_dir      = srv["remote_dir"].rstrip("/")

    log.info("Compressing '%s' -> '%s' ...", folder, output_name)
    archive_path = compress_folder(folder, output_name)
    log.info("Archive created: %s", archive_path)

    remote_path = f"{remote_dir}/{os.path.basename(archive_path)}"

    with RemoteServerSession(srv["host"], srv["port"], srv["username"], srv["password"]) as session:
        uploaded = session.upload(archive_path, remote_path, force_overwrite=force_overwrite)
        if uploaded:
            log.info("Restarting services ...")
            session.run_command("systemctl", "restart", "guacd", "tomcat9")
        else:
            log.info("No upload performed; skipping service restart.")

    if not keep_archive:
        os.remove(archive_path)
        log.info("Local archive '%s' removed.", archive_path)


if __name__ == "__main__":
    main()
