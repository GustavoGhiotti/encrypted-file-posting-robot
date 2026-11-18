import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))


from datetime import date, datetime, time
import re

from src.shared.utils.env_load import Settings
from src.infrastructure.logging.logger_config import get_logger
from src.infrastructure.database.conexao_sftp import SFTPClient

from src.application.service.zip_service import ZipService
from src.application.service.gpg_service import GPGService
from src.application.service.upload_service import SiriusUploadService
from src.application.service.cleanup_service import CleanupService
from src.shared.utils.env_load import conexao_71
from src.infrastructure.database.conexao_servidor import Servidor
import shutil
import smbclient
from src.infrastructure.services.notifier import enviar_alerta_erro, enviar_alerta_arquivo_movido


logger = get_logger("Sirius - VCOM")

HORARIO_INICIO_EXECUCAO = time(21, 0)
HORARIO_FIM_EXECUCAO = time(23, 0)


def esta_no_horario_permitido() -> bool:
    horario_atual = datetime.now().time()
    return HORARIO_INICIO_EXECUCAO <= horario_atual < HORARIO_FIM_EXECUCAO


def arquivo_existe_no_servidor(caminho: Path) -> bool:
    try:
        return smbclient.path.exists(str(caminho))
    except OSError:
        return False


def garantir_pasta_remota(caminho: Path) -> None:
    if arquivo_existe_no_servidor(caminho):
        return
    parent = caminho.parent
    if parent and str(parent) != str(caminho):
        garantir_pasta_remota(parent)
    try:
        smbclient.mkdir(str(caminho))
    except OSError:
        if not arquivo_existe_no_servidor(caminho):
            raise


def copiar_para_servidor(origem: Path, destino: Path) -> None:
    garantir_pasta_remota(destino.parent)
    with open(origem, "rb") as src, smbclient.open_file(str(destino), mode="wb") as out:
        shutil.copyfileobj(src, out, length=1024 * 1024 * 8)
        out.flush()


def listar_arquivos_data(data_dir: Path, extensoes: set[str]) -> list[Path]:
    if not data_dir.exists():
        return []

    arquivos: list[Path] = []
    for path in data_dir.rglob("*"):
        if not path.is_file():
            continue

        sufixos = [s.lower() for s in path.suffixes]
        if not sufixos:
            continue

        if sufixos[-1] in extensoes:
            arquivos.append(path)

    return sorted(arquivos)


def limpar_pasta_temporaria(cleanup: CleanupService, caminho: Path) -> None:
    try:
        cleanup.remover_pasta(caminho)
    except Exception as exc:
        logger.warning(
            "Falha nao critica ao remover pasta temporaria (%s): %s",
            caminho,
            exc,
        )
    else:
        logger.info("Pasta temporaria da carteira removida com sucesso")


def main() -> None:


    logger.info("=== Iniciando automação Sirius ===")

    if not esta_no_horario_permitido():
        logger.info(
            "Execucao fora do horario permitido (%s ate %s). Processo encerrado.",
            HORARIO_INICIO_EXECUCAO.strftime("%H:%M"),
            HORARIO_FIM_EXECUCAO.strftime("%H:%M"),
        )
        return

    Settings.validate()
    logger.info("Configurações validadas")

    config_sv = conexao_71()
    base_data_dir = Settings.BASE_DIR / "data" / "sirius"
    download_dir = base_data_dir / "downloads"
    processed_dir = base_data_dir / "processed"

    sftp = SFTPClient(
        hostname=Settings.SFTP_HOST_SIRIUS,
        user=Settings.SFTP_USER_SIRIUS,
        password=Settings.SFTP_PASSWORD_SIRIUS,
        port=Settings.SFTP_PORT_SIRIUS,
    )


    data_ref = (date.today()).strftime("%Y%m%d")

    nome_esperado = [
        re.compile(rf"^{data_ref}_\d{{6}}_\d+_PHONE_IN\.txt$", re.IGNORECASE),
        re.compile(rf"^{data_ref}_\d{{6}}_\d+_PROMESSA_IN\.txt$", re.IGNORECASE),
        re.compile(rf"^{data_ref}_\d{{6}}_\d+_ADDRESS_IN\.txt$", re.IGNORECASE),
        re.compile(rf"^{data_ref}_\d{{6}}_\d+_ACIONAMENTOS_IN\.txt$", re.IGNORECASE),
    ]

    logger.info(f"Buscando arquivos com padrão do dia {data_ref}")

    arquivos_remotos = sftp.listar_arquivos(
        caminho=Settings.SFTP_REMOTE_DIR_SIRIUS,
        extensao_arquivo=".txt",
        nome_esperado=nome_esperado,
    )

    if not arquivos_remotos:
        logger.warning("Nenhum arquivo encontrado no SFTP")
        return

    logger.info(f"{len(arquivos_remotos)} arquivo(s) encontrado(s) no SFTP")

    servidor = Servidor(config_sv["ipServidor"], config_sv["usuario"], config_sv["senha"])
    servidor.conectar()

    destino_base = Settings.SERVIDOR_SIRIUS_PATH or Settings.LOCAL_SERVIDOR
    if not destino_base:
        raise RuntimeError("Destino de servidor nao configurado (SERVIDOR_SIRIUS/LOCAL_SERVIDOR)")

    pasta_envio_txt = destino_base / "SIRIUS_TXT"
    pasta_envio_zip = destino_base / "SIRIUS_ZIP"
    pasta_envio_gpg = destino_base / "SIRIUS_GPG"

    arquivos_existentes_servidor: set[str] = set()
    arquivos_remotos_filtrados: list[str] = []
    for nome in arquivos_remotos:
        stem = Path(nome).stem
        gpg_nome = f"{stem}.zip.gpg"
        destino_gpg = destino_base / gpg_nome
        if arquivo_existe_no_servidor(destino_gpg):
            arquivos_existentes_servidor.add(gpg_nome)
            logger.info(f"Arquivo ja existe no servidor, ignorado: {gpg_nome}")
            continue
        arquivos_remotos_filtrados.append(nome)

    if not arquivos_remotos_filtrados:
        logger.info("Todos os arquivos do SFTP ja existem no servidor")
        return

    arquivos_locais: list[Path] = []
    download_dir.mkdir(parents=True, exist_ok=True)

    for nome in arquivos_remotos_filtrados:
        remote_path = f"{Settings.SFTP_REMOTE_DIR_SIRIUS}/{nome}"
        local_path = download_dir / nome

        if not sftp.validar_arquivo_pronto(remote_path):
            logger.warning(f"Arquivo ainda em escrita, ignorado: {nome}")
            continue

        with sftp.abrir_arquivo(remote_path, "rb") as remoto:
            with open(local_path, "wb") as local:
                while True:
                    data = remoto.read(1024 * 1024)
                    if not data:
                        break
                    local.write(data)

        arquivos_locais.append(local_path)
        logger.info(f"Arquivo baixado: {local_path}")

    if not arquivos_locais:
        logger.warning("Nenhum arquivo foi baixado")
        return

    zip_service = ZipService()
    gpg_service = GPGService()

    arquivos_criptografados: list[Path] = []

    for arquivo in arquivos_locais:
        zip_path = zip_service.compactar(
            arquivo=arquivo,
            destino=processed_dir,
        )
        logger.info(f"ZIP gerado: {zip_path}")

        gpg_path = gpg_service.criptografar_zip(zip_path)
        logger.info(f"Arquivo criptografado: {gpg_path}")

        arquivos_criptografados.append(gpg_path)

    if not arquivos_criptografados:
        logger.warning("Nenhum arquivo foi criptografado")

    cleanup = CleanupService()

    houve_movimento_para_servidor = False
    arquivos_data_servidor = listar_arquivos_data(base_data_dir, {".txt", ".zip", ".gpg"})
    if not arquivos_data_servidor:
        logger.warning("Nenhum arquivo encontrado na pasta data para copiar ao servidor")
    else:
        arquivos_copiados = 0
        for arquivo in arquivos_data_servidor:
            if arquivo.suffix.lower() == ".txt":
                destino = pasta_envio_txt / arquivo.name
            elif arquivo.suffix.lower() == ".zip":
                destino = pasta_envio_zip / arquivo.name
            elif arquivo.suffix.lower() == ".gpg":
                destino = pasta_envio_gpg / arquivo.name
            else:
                logger.warning(f"Extensao nao suportada: {arquivo.name}")
                continue
            if arquivo_existe_no_servidor(destino):
                arquivos_existentes_servidor.add(arquivo.name)
                logger.warning(f"Arquivo ja existe no servidor: {arquivo.name}")
                continue
            copiar_para_servidor(arquivo, destino)
            arquivos_copiados += 1
            logger.info(f"Arquivo copiado para servidor: {destino}")

        if arquivos_copiados == 0:
            logger.info("Nenhum arquivo novo para copiar ao servidor")
        else:
            houve_movimento_para_servidor = True

    arquivos_para_upload = [
        arquivo for arquivo in arquivos_criptografados
        if arquivo.name not in arquivos_existentes_servidor
    ]

    if not arquivos_para_upload:
        logger.info("Nenhum arquivo novo para upload")
        limpar_pasta_temporaria(cleanup, base_data_dir)
        return

    uploader = SiriusUploadService()

    try:
        uploader.upload_arquivos(arquivos_para_upload)
        logger.info("Uploads realizados com sucesso")
    except Exception:
        logger.exception("Falha durante o upload - arquivos locais mantidos")
        raise
    else:
        if houve_movimento_para_servidor:
            enviar_alerta_arquivo_movido("Sirius - VCOM", logger)
        limpar_pasta_temporaria(cleanup, base_data_dir)

    logger.info("=== Automação Sirius finalizada com SUCESSO ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        #enviar_alerta_erro("Sirius - VCOM", exc, logger)
        raise
