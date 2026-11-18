from pathlib import Path
import zipfile


class ZipService:
    def compactar(self, arquivo: Path, destino: Path) -> Path:
        
        if not arquivo.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {arquivo}")

        if not arquivo.is_file():
            raise ValueError(f"Não é um arquivo válido: {arquivo}")

        destino.mkdir(parents=True, exist_ok=True)

        zip_path = destino / f"{arquivo.stem}.zip"

        with zipfile.ZipFile(
            zip_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED
        ) as zipf:
            zipf.write(
                arquivo,
                arcname=arquivo.name
            )

        return zip_path
