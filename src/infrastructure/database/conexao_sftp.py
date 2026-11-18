import time
import stat
import re
from typing import Iterable, List
from urllib.parse import urlparse
import paramiko


class SFTPClient:
    def __init__(
        self,
        hostname: str,
        user: str,
        password: str,
        port: int = 22,
        timeout: int = 10
    ):
        host = (hostname or "").strip()
        if "://" in host:
            parsed = urlparse(host)
            if parsed.hostname:
                host = parsed.hostname

        self.hostname = host
        self.user = user
        self.password = password
        self.port = port
        self.timeout = timeout

        self._transport: paramiko.Transport | None = None
        self._sftp: paramiko.SFTPClient | None = None

        self._connect()

    def _connect(self) -> None:
        transport = paramiko.Transport((self.hostname, self.port))
        transport.sock.settimeout(self.timeout)
        transport.connect(
            username=self.user,
            password=self.password
        )

        self._transport = transport
        self._sftp = paramiko.SFTPClient.from_transport(transport)

    def close(self) -> None:
        if self._sftp:
            self._sftp.close()
        if self._transport:
            self._transport.close()

    def __del__(self):
        self.close()


    def listar_arquivos(
        self,
        caminho: str,
        extensao_arquivo: str | None = None,
        nome_esperado: Iterable[re.Pattern] | None = None
    ) -> List[str]:
        arquivos = []

        for entry in self._sftp.listdir_attr(caminho):
            if not stat.S_ISREG(entry.st_mode):
                continue

            nome = entry.filename

            if extensao_arquivo and not nome.lower().endswith(extensao_arquivo.lower()):
                continue

            if nome_esperado:
                if not any(regex.match(nome) for regex in nome_esperado):
                    continue

            arquivos.append(nome)

        return arquivos


    def validar_arquivo_pronto(
        self,
        caminho_remoto: str,
        tentativas: int = 3,
        intervalo: int = 2
    ) -> bool:
        try:
            size_anterior = self._sftp.stat(caminho_remoto).st_size

            for _ in range(tentativas):
                time.sleep(intervalo)
                size_atual = self._sftp.stat(caminho_remoto).st_size

                if size_atual == size_anterior:
                    return True

                size_anterior = size_atual

        except Exception:
            return False

        return False


    def abrir_arquivo(self, caminho_remoto: str, modo: str = "rb"):

        return self._sftp.open(caminho_remoto, modo)
