from pathlib import Path
import shutil
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

import smbclient
from datetime import date
from src.shared.utils.env_load import Settings, conexao_71, conexao_66
from src.infrastructure.logging.logger_config import get_logger
from src.infrastructure.database.conexao_sftp import SFTPClient
from src.infrastructure.database.conexao_servidor import Servidor
from src.application.service.download_service import SiriusDownloadService
from src.application.service.gpg_decrypt_service import GPGDecryptService
from src.application.service.unzip_service import UnzipService
from src.application.service.cleanup_service import CleanupService
from src.infrastructure.services.notifier import enviar_alerta_erro, enviar_alerta_arquivo_movido


logger = get_logger("Sirius - Carga")
PASTAS_SFTP = {
    "Sirius": Settings.SFTP_ENVIO_SUBPASTA_SIRIUS or "Sirius",
}
ID_CEDENTE_ENVIO = 1000


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


def criar_cliente_sftp_envio() -> tuple[SFTPClient, str]:
    config_db = conexao_66("DB_DESENVOLVIMENTO")
    if all(config_db.values()):
        from src.infrastructure.database.database_carga import Carga

        credencial_envio = Carga(config_db).obter_credencial(ID_CEDENTE_ENVIO)
        if credencial_envio:
            return (
                SFTPClient(
                    hostname=credencial_envio["HOSTNAME"],
                    user=credencial_envio["USUARIO"],
                    password=credencial_envio["SENHA"],
                    port=credencial_envio["PORTA_HOST"],
                ),
                credencial_envio["ORIGEM_CARGA"],
            )

    host = Settings.SFTP_ENVIO_HOST_SIRIUS
    user = Settings.SFTP_ENVIO_USER_SIRIUS
    password = Settings.SFTP_ENVIO_PASSWORD_SIRIUS
    port = Settings.SFTP_ENVIO_PORT_SIRIUS
    destino = Settings.SFTP_ENVIO_REMOTE_DIR_SIRIUS

    if not all([host, user, password, destino]):
        raise RuntimeError("Configuracao de envio SFTP da Sirius incompleta")

    return (
        SFTPClient(
            hostname=host,
            user=user,
            password=password,
            port=port,
        ),
        destino,
    )


def enviar_arquivo_sftp(
    obj_sftp_envio: SFTPClient,
    destino_sftp_envio: str,
    pasta_destino: str,
    nome_arquivo: str,
    conteudo_arquivo: bytes,
) -> None:
    subpasta_destino = PASTAS_SFTP[pasta_destino]
    caminho_destino = f"{destino_sftp_envio.rstrip('/')}/{subpasta_destino}/{nome_arquivo}"
    with obj_sftp_envio.abrir_arquivo(caminho_destino, "wb") as arquivo_destino:
        arquivo_destino.write(conteudo_arquivo)


def main() -> None:
    logger.info("=== Iniciando automacao Sirius Carga ===")

    Settings.validate()
    logger.info("Configuracoes validadas")

    config_sv = conexao_71()
    servidor = Servidor(config_sv["ipServidor"], config_sv["usuario"], config_sv["senha"])
    servidor.conectar()

    destino_servidor = Settings.CARGA_SIRIUS_PATH or Settings.LOCAL_SERVIDOR
    
    if not destino_servidor:
        raise RuntimeError("LOCAL_SERVIDOR nao configurado")

    obj_sftp_envio, destino_sftp_envio = criar_cliente_sftp_envio()

    pasta_carga_txt = destino_servidor / "SIRIUS_TXT"
    pasta_carga_zip = destino_servidor / "SIRIUS_ZIP"
    pasta_carga_gpg = destino_servidor / "SIRIUS_GPG"

    base_dir = Settings.BASE_DIR
    download_dir = base_dir / "data" / "saida" / "downloads"
    decrypt_dir = base_dir / "data" / "saida" / "decrypted"
    extract_dir = base_dir / "data" / "saida" / "extracted"

    downloader = SiriusDownloadService()
    arquivos_baixados = downloader.download_arquivos(download_dir, extensoes=(".gpg", ".zip"))

    if not arquivos_baixados:
        logger.warning("Nenhum arquivo encontrado para download")
        return

    gpg_service = GPGDecryptService()
    unzip_service = UnzipService()

    arquivos_existentes_servidor: set[str] = set()
    arquivos_copiados = 0
    arquivos_enviados_sftp = 0

    today_str = date.today().strftime("%Y%m%d")

    for arquivo in arquivos_baixados:
        if today_str in arquivo.name.lower():

            if arquivo.suffix.lower() == ".gpg":
                logger.info(f"Descriptografando: {arquivo.name}")
                zip_path = gpg_service.descriptografar(arquivo, decrypt_dir)
                destino_gpg = pasta_carga_gpg / arquivo.name
                if not arquivo_existe_no_servidor(destino_gpg):
                    copiar_para_servidor(arquivo, destino_gpg)
                    logger.info(f"GPG copiado para servidor: {destino_gpg}")
                destino_zip = pasta_carga_zip / zip_path.name
                if not arquivo_existe_no_servidor(destino_zip):
                    copiar_para_servidor(zip_path, destino_zip)
                    logger.info(f"ZIP copiado para servidor: {destino_zip}")
            elif arquivo.suffix.lower() == ".zip":
                zip_path = arquivo
                destino_zip = pasta_carga_zip / arquivo.name
                if not arquivo_existe_no_servidor(destino_zip):
                    copiar_para_servidor(arquivo, destino_zip)
                    logger.info(f"ZIP copiado para servidor: {destino_zip}")
            else:
                logger.warning(f"Extensao nao suportada: {arquivo.name}")
                continue

            logger.info(f"Descompactando: {zip_path.name}")
            extraidos = unzip_service.descompactar(zip_path, extract_dir)
            if not extraidos:
                logger.warning(f"Nenhum arquivo extraido: {zip_path.name}")
                continue

            for extraido in extraidos:
                destino = pasta_carga_txt / extraido.name
                if extraido.name in arquivos_existentes_servidor or arquivo_existe_no_servidor(destino):
                    arquivos_existentes_servidor.add(extraido.name)
                    logger.info(f"Arquivo ja existe no servidor: {extraido.name}")
                    continue

                copiar_para_servidor(extraido, destino)
                arquivos_copiados += 1
                logger.info(f"Arquivo copiado para servidor: {destino}")
                enviar_arquivo_sftp(
                    obj_sftp_envio,
                    destino_sftp_envio,
                    "Sirius",
                    extraido.name,
                    extraido.read_bytes(),
                )
                arquivos_enviados_sftp += 1
                logger.info(
                    "Arquivo enviado para SFTP: %s/%s/%s",
                    destino_sftp_envio.rstrip("/"),
                    PASTAS_SFTP["Sirius"],
                    extraido.name,
                )
        else:
             continue

    if arquivos_copiados == 0:
        logger.info("Nenhum arquivo novo copiado para o servidor")
    else:
        logger.info(f"Total de arquivos copiados: {arquivos_copiados}")

    if arquivos_enviados_sftp == 0:
        logger.info("Nenhum arquivo novo enviado para o SFTP")
    else:
        logger.info(f"Total de arquivos enviados para o SFTP: {arquivos_enviados_sftp}")
        enviar_alerta_arquivo_movido("Sirius - Carga", logger)

    CleanupService().remover_pasta_data(Settings.BASE_DIR)
    logger.info("Pasta data/ removida com sucesso")

    logger.info("=== Automacao Sirius Carga finalizada ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        enviar_alerta_erro("Sirius - Carga", exc, logger)
        raise
