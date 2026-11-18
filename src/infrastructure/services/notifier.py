import os
from logging import Logger

from src.infrastructure.services.telegram import enviar_telegram
from src.shared.utils.env_load import Settings


def _carregar_config_telegram() -> tuple[str | None, str | None]:
    token = Settings.TELEGRAM_TOKEN or os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN")
    chat_id = (
        Settings.TELEGRAM_CHAT_ID
        or os.getenv("TELEGRAM_CHAT_ID")
        or os.getenv("ID_CHAT")
    )
    return token, chat_id


def enviar_alerta_erro(robot_nome: str, erro: Exception, logger: Logger | None = None) -> bool:
    token, chat_id = _carregar_config_telegram()
    if not token or not chat_id:
        if logger:
            logger.warning(
                "Telegram nao configurado (TELEGRAM_TOKEN/TELEGRAM_CHAT_ID); alerta ignorado."
            )
        return False

    mensagem = f"ERRO NA EXECUCAO - PROCESSO: {robot_nome}"

    enviado = enviar_telegram(token, chat_id, mensagem)
    if logger:
        if enviado:
            logger.info("Alerta de erro enviado via Telegram.")
        else:
            logger.warning("Falha ao enviar alerta de erro via Telegram.")
    return enviado


def enviar_alerta_monitoramento(
    robot_nome: str,
    mensagem: str,
    logger: Logger | None = None,
    mensagem_exata: bool = False,
) -> bool:
    token, chat_id = _carregar_config_telegram()
    if not token or not chat_id:
        if logger:
            logger.warning(
                "Telegram nao configurado (TELEGRAM_TOKEN/TELEGRAM_CHAT_ID); alerta ignorado."
            )
        return False

    texto = mensagem if mensagem_exata else f"[{robot_nome}] alerta de monitoramento.\n{mensagem}"
    enviado = enviar_telegram(token, chat_id, texto)
    if logger:
        if enviado:
            logger.info("Alerta de monitoramento enviado via Telegram.")
        else:
            logger.warning("Falha ao enviar alerta de monitoramento via Telegram.")
    return enviado


def enviar_alerta_arquivo_movido(robot_nome: str, logger: Logger | None = None) -> bool:
    token, chat_id = _carregar_config_telegram()
    if not token or not chat_id:
        if logger:
            logger.warning(
                "Telegram nao configurado (TELEGRAM_TOKEN/TELEGRAM_CHAT_ID); alerta ignorado."
            )
        return False

    mensagem = f"ARQUIVO MOVIDO - PROCESSO: {robot_nome}"
    enviado = enviar_telegram(token, chat_id, mensagem)
    if logger:
        if enviado:
            logger.info("Alerta de arquivo movido enviado via Telegram.")
        else:
            logger.warning("Falha ao enviar alerta de arquivo movido via Telegram.")
    return enviado
