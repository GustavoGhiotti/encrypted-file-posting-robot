from pathlib import Path
import os
import shutil
import stat
import time


class CleanupService:
    def _onerror(self, func, path, exc_info):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            # Deixa o tratamento principal decidir se tenta novamente.
            pass

    def remover_pasta(self, caminho: Path) -> None:
        if not caminho.exists():
            return

        if not caminho.is_dir():
            raise RuntimeError(f"Caminho nao e diretorio: {caminho}")

        tentativas = 5
        ultimo_erro: Exception | None = None
        for tentativa in range(1, tentativas + 1):
            try:
                shutil.rmtree(caminho, onerror=self._onerror)
                return
            except FileNotFoundError:
                return
            except OSError as exc:
                ultimo_erro = exc
                # WinError comuns em concorrencia/trava temporaria no Windows.
                if getattr(exc, "winerror", None) in {5, 32, 145} and tentativa < tentativas:
                    time.sleep(0.5 * tentativa)
                    continue
                raise

        if ultimo_erro:
            raise ultimo_erro

    def remover_pasta_data(self, base_dir: Path) -> None:
        self.remover_pasta(base_dir / "data")
