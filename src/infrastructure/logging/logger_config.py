import logging
from pathlib import Path
from datetime import datetime, timedelta
import re


LOG_LEVEL_PADRAO = logging.INFO


def get_logger(
    nome: str,
    level: int = LOG_LEVEL_PADRAO,
    log_dir: Path | None = None
) -> logging.Logger:

    logger = logging.getLogger(nome)

    if logger.handlers:
        return logger

    logger.setLevel(level)

    if not log_dir:
        BASE_DIR = Path(__file__).resolve().parents[3] 
        log_dir = BASE_DIR / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    # Remove logs older than 2 days based on filename date.
    limite = datetime.now().date() - timedelta(days=6)
    padrao = re.compile(r"^(?P<nome>.+)_(?P<data>\d{8})\.log$")
    for arquivo in log_dir.iterdir():
        if not arquivo.is_file():
            continue
        match = padrao.match(arquivo.name)
        if not match:
            continue
        try:
            data_arquivo = datetime.strptime(match.group("data"), "%Y%m%d").date()
        except ValueError:
            continue
        if data_arquivo < limite:
            try:
                arquivo.unlink()
            except OSError:
                pass

    data_atual = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"{nome}_{data_atual}.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.propagate = False

    return logger
