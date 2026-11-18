import os
import subprocess
from pathlib import Path

from src.shared.utils.env_load import Settings


class GPGDecryptService:
    def __init__(self) -> None:
        self.gpg_exe = Settings.GPG_EXE
        self.gpg_home = Settings.GPG_HOME
        self.passphrase = os.getenv("GPG_PASSPHRASE")

    def _build_command(self, args: list[str]) -> list[str]:
        cmd = [self.gpg_exe]
        if self.gpg_home:
            cmd.extend(["--homedir", self.gpg_home])
        if self.passphrase:
            cmd.extend(["--pinentry-mode", "loopback", "--passphrase", self.passphrase])
        cmd.extend(args)
        return cmd

    def _run(self, command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(command, capture_output=True, text=True)

    def descriptografar(self, arquivo_gpg: Path, destino: Path) -> Path:
        if not arquivo_gpg.exists():
            raise FileNotFoundError(f"Arquivo GPG nao encontrado: {arquivo_gpg}")

        destino.mkdir(parents=True, exist_ok=True)
        output_path = destino / arquivo_gpg.stem

        result = self._run(self._build_command([
            "--batch",
            "--yes",
            "--output",
            str(output_path),
            "--decrypt",
            str(arquivo_gpg),
        ]))

        if result.returncode != 0:
            raise RuntimeError(
                f"Erro ao descriptografar arquivo:\n{result.stderr}"
            )

        return output_path
