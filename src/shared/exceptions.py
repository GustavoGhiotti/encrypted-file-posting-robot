# =========================================================
# EXCEÇÕES BASE
# =========================================================

class SiriusException(Exception):
    """Exceção base para a automação Sirius"""
    pass


# =========================================================
# CONFIGURAÇÃO / AMBIENTE
# =========================================================

class SettingsException(SiriusException):
    """Erro relacionado a variáveis de ambiente ou configurações"""
    pass


class DependencyException(SiriusException):
    """Dependência obrigatória não encontrada ou inválida"""
    pass


# =========================================================
# SFTP
# =========================================================

class SFTPConnectionError(SiriusException):
    """Falha ao conectar no servidor SFTP"""
    pass


class SFTPListError(SiriusException):
    """Falha ao listar arquivos no SFTP"""
    pass


class SFTPDownloadError(SiriusException):
    """Erro ao baixar arquivo do SFTP"""
    pass


class SFTPFileNotReady(SiriusException):
    """Arquivo ainda está sendo escrito no servidor"""
    pass


# =========================================================
# ZIP
# =========================================================

class ZipException(SiriusException):
    """Erro genérico ao compactar arquivos"""
    pass


class ZipCreationError(ZipException):
    """Falha na criação do arquivo ZIP"""
    pass


# =========================================================
# GPG
# =========================================================

class GPGException(SiriusException):
    """Erro genérico relacionado ao GPG"""
    pass


class GPGKeyNotFound(GPGException):
    """Chave pública GPG não encontrada"""
    pass


class GPGEncryptionError(GPGException):
    """Erro ao criptografar arquivo"""
    pass


class GPGExecutionError(GPGException):
    """Erro ao executar comando GPG"""
    pass


# =========================================================
# UPLOAD / UI
# =========================================================

class UploadException(SiriusException):
    """Erro genérico no processo de upload"""
    pass


class UploadNavigationError(UploadException):
    """Erro ao navegar até a pasta de upload"""
    pass


class UploadDialogNotFound(UploadException):
    """Modal ou dialog de upload não encontrado"""
    pass


class UploadButtonNotFound(UploadException):
    """Botão de upload não localizado na tela"""
    pass


class FileDialogError(UploadException):
    """Erro ao interagir com o dialog de arquivos do Windows"""
    pass


# =========================================================
# CLEANUP
# =========================================================

class CleanupException(SiriusException):
    """Erro ao limpar arquivos temporários"""
    pass


class FolderCleanupError(CleanupException):
    """Erro ao remover pasta"""
    pass


class FileCleanupError(CleanupException):
    """Erro ao remover arquivo"""
    pass
