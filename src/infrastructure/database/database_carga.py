from src.infrastructure.database.executor import Executor, Conexao


class Carga:
    def __init__(self, conexao: Conexao):
        self.executor = Executor(**conexao)

    def obter_credencial(self, id_cedente: int) -> dict | None:
        query = """
            SELECT
                NM_CEDENTE,
                HOSTNAME,
                USUARIO,
                SENHA,
                PORTA_HOST,
                ORIGEM_CARGA,
                DESTINO_CARGA
            FROM Carga.TB_CONEXAO_SFTP WITH(NOLOCK)
            WHERE ID_CEDENTE = ?
        """
        return self.executor.executar_query(
            query=query,
            parametros=[id_cedente],
            fetch="one",
        )
