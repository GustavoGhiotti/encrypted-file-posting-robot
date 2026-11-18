from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.infrastructure.logging.logger_config import get_logger
from src.infrastructure.services.notifier import enviar_alerta_monitoramento
from src.shared.utils.env_load import Settings


MONITOR_LOGGER = get_logger("Sirius - Monitor")
MENSAGEM_ALERTA_MONITOR = "ERRO NA EXECUCAO DO ROBO DE ENVIO PARA O SITE, VERIFICAR E RODAR MANUALMENTE"


def _log_do_dia_existe(robot_nome: str) -> tuple[bool, Path | None]:
    data_ref = datetime.now().strftime("%Y%m%d")
    log_dir = Settings.BASE_DIR / "logs"
    esperado = log_dir / f"{robot_nome}_{data_ref}.log"
    return esperado.exists(), esperado


def _processo_rodando(marcadores: list[str]) -> bool | None:
    comandos = [
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process | Select-Object -ExpandProperty CommandLine",
        ],
        [
            "wmic",
            "process",
            "get",
            "CommandLine",
        ],
    ]

    for comando in comandos:
        try:
            result = subprocess.run(comando, capture_output=True, text=True, check=False)
        except OSError:
            continue
        if result.returncode != 0:
            continue
        saida = (result.stdout or "").lower()
        if any(marcador.lower() in saida for marcador in marcadores):
            return True

    fallback = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-Process python,pythonw -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName",
    ]
    try:
        result = subprocess.run(fallback, capture_output=True, text=True, check=False)
    except OSError:
        result = None
    if result and result.returncode == 0 and (result.stdout or "").strip():
        MONITOR_LOGGER.warning(
            "Nao foi possivel confirmar command line do processo; fallback detectou processo python ativo."
        )
        return True

    MONITOR_LOGGER.warning("Nao foi possivel listar processos para monitoramento.")
    return None


def monitorar(robot_nome: str, marcadores_processo: list[str]) -> int:
    log_existe, caminho_log = _log_do_dia_existe(robot_nome)
    rodando = _processo_rodando(marcadores_processo)

    # Regra operacional: se nao existe log do dia, deve alertar quando processo
    # nao estiver rodando OU quando o estado do processo for desconhecido.
    if log_existe:
        MONITOR_LOGGER.info(
            "Monitoramento ok para %s. Log do dia encontrado em %s.",
            robot_nome,
            caminho_log,
        )
        return 0

    if rodando is None:
        texto = (
            f"log do dia nao encontrado ({caminho_log}); "
            f"estado do processo desconhecido para marcadores: {', '.join(marcadores_processo)}"
        )
        MONITOR_LOGGER.error("Falha de monitoramento em %s: %s", robot_nome, texto)
        enviar_alerta_monitoramento(
            robot_nome,
            MENSAGEM_ALERTA_MONITOR,
            MONITOR_LOGGER,
            mensagem_exata=True,
        )
        return 1

    if rodando:
        MONITOR_LOGGER.info(
            "Log do dia ainda nao encontrado (%s), mas processo esta rodando. Sem alerta.",
            caminho_log,
        )
        return 0

    texto = (
        f"log do dia nao encontrado ({caminho_log}); "
        f"processo nao encontrado para marcadores: {', '.join(marcadores_processo)}"
    )

    MONITOR_LOGGER.error("Falha de monitoramento em %s: %s", robot_nome, texto)
    enviar_alerta_monitoramento(
        robot_nome,
        MENSAGEM_ALERTA_MONITOR,
        MONITOR_LOGGER,
        mensagem_exata=True,
    )
    return 1


def main() -> int:
    Settings.load_env()

    parser = argparse.ArgumentParser(description="Monitor de execucao do robo Sirius.")
    parser.add_argument(
        "--robot",
        choices=("vcom", "carga"),
        required=True,
        help="Robo a monitorar.",
    )
    args = parser.parse_args()

    if args.robot == "vcom":
        return monitorar("Sirius - VCOM", ["scripts\\sirius.py", "scripts/sirius.py"])
    return monitorar(
        "Sirius - Carga",
        ["scripts\\sirius_carga.py", "scripts/sirius_carga.py"],
    )


if __name__ == "__main__":
    raise SystemExit(main())
