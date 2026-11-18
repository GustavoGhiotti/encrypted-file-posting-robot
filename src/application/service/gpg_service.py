import subprocess
from pathlib import Path

from src.shared.utils.env_load import Settings


class GPGService:
    def __init__(self):
        self.gpg_exe = Settings.GPG_EXE
        self.recipient = Settings.GPG_RECIPIENT
        self.public_key_path = Path(Settings.GPG_PUBLIC_KEY_PATH)
        self.gpg_home = Settings.GPG_HOME

    def _build_command(self, args: list[str]) -> list[str]:
        cmd = [self.gpg_exe]
        if self.gpg_home:
            cmd.extend(["--homedir", self.gpg_home])
        cmd.extend(args)
        return cmd

    def _run(self, command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            command,
            capture_output=True,
            text=True
        )

    def _recipient_existe(self) -> bool:
        result = self._run(self._build_command([
            "--list-keys",
            self.recipient
        ]))
        return result.returncode == 0

    def _importar_chave_se_necessario(self) -> None:
        if self._recipient_existe():
            return

        if not self.public_key_path.exists():
            raise FileNotFoundError(
                f"Arquivo de chave publica nao encontrado: {self.public_key_path}"
            )

        result = self._run(self._build_command([
            "--import",
            str(self.public_key_path)
        ]))

        if result.returncode != 0:
            raise RuntimeError(
                f"Falha ao importar chave GPG:\n{result.stderr}"
            )

        if not self._recipient_existe():
            raise RuntimeError(
                "Chave GPG importada, mas o recipient ainda nao foi encontrado."
            )

    def criptografar_zip(self, zip_path: Path) -> Path:
        if not zip_path.exists():
            raise FileNotFoundError(f"Arquivo ZIP nao encontrado: {zip_path}")

        self._importar_chave_se_necessario()

        output_path = zip_path.with_suffix(zip_path.suffix + ".gpg")

        result = self._run(self._build_command([
            "--batch",
            "--yes",
            "--no-auto-key-locate",
            "--no-auto-key-retrieve",
            "--trust-model",
            "always",
            "--output",
            str(output_path),
            "--encrypt",
            "--recipient",
            self.recipient,
            str(zip_path)
        ]))

        if result.returncode != 0:
            raise RuntimeError(
                f"Erro ao criptografar arquivo:\n{result.stderr}"
            )

        return output_path
