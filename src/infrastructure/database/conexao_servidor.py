import smbclient
from io import BufferedReader
import subprocess
from typing import BinaryIO


class ConexaoServidor:
    def __init__(self, servidor:str, usuario:str, senha:str):
        self._servidor = servidor
        self._usuario = usuario
        self._senha = senha

class Servidor(ConexaoServidor):
    def __init__(self, servidor:str, usuario:str, senha:str):
        super().__init__(servidor, usuario, senha)

    def conectar(self) -> None:
        try:
            smbclient.register_session(
                server=self._servidor,
                username=self._usuario,
                password=self._senha,
            )
            return
        except Exception as exc_credencial:
            # Fallback: tenta sessao SMB ja existente no Windows (credencial do usuario logado).
            try:
                smbclient.register_session(server=self._servidor)
                return
            except Exception as exc_sessao:
                raise RuntimeError(
                    "Falha ao autenticar no SMB. Verifique SERVER_USER/SERVER_SENHA "
                    "ou a sessao SMB ja conectada no Windows."
                ) from exc_sessao


    def listar_arquivos(self, caminho: str) -> list:
        arquivos = []
        for entry in smbclient.scandir(caminho):
            if entry.is_file():
                arquivos.append(entry.name)
        return arquivos
    
    def abrir_arquivo(self, caminho:str) -> BufferedReader:
        return smbclient.open_file(caminho, mode="rb")
    
    def mover(self, carga:BinaryIO, destino:BinaryIO) -> None:
        destino.write(carga)
        destino.close()
    def gerar_caminho_destino(self, caminho:str) -> BinaryIO: 
        return smbclient.open_file(caminho, mode="wb")
   


class ServidorSO(ConexaoServidor):
    def __init__(self, servidor:str, usuario:str, senha:str, letra:str):
        super().__init__(servidor, usuario, senha)
        self.letra = letra
        self.__conectar()

    def __conectar(self):
        if not self.__verifica_conexao():
            subprocess.run([
                "net", "use", f"{self.letra}:", fr"\\{self._servidor}\easycollector",
                fr"/user:{self._usuario}", self._senha
            ], check=True)

    def __verifica_conexao(self) -> bool:
        resultado = subprocess.run(["net", "use"], capture_output=True, text=True)
        saida = resultado.stdout.lower()

        letra = self.letra.lower() + ":"
        servidor = self._servidor.lower().replace("\\", "")

        for linha in saida.splitlines():
            if letra in linha and servidor in linha:
                return True
            
        return False
    
