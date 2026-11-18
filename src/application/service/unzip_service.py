from pathlib import Path
import shutil
import zipfile


class UnzipService:
    def descompactar(self, arquivo_zip: Path, destino: Path) -> list[Path]:
        if not arquivo_zip.exists():
            raise FileNotFoundError(f"Arquivo ZIP nao encontrado: {arquivo_zip}")

        if not arquivo_zip.is_file():
            raise ValueError(f"Nao e um arquivo valido: {arquivo_zip}")

        destino.mkdir(parents=True, exist_ok=True)
        extraidos: list[Path] = []

        with zipfile.ZipFile(arquivo_zip, mode="r") as zipf:
            for info in zipf.infolist():
                if info.is_dir():
                    continue
                nome = Path(info.filename).name
                destino_arquivo = destino / nome
                with zipf.open(info, "r") as origem, open(destino_arquivo, "wb") as saida:
                    shutil.copyfileobj(origem, saida)
                extraidos.append(destino_arquivo)

        return extraidos
