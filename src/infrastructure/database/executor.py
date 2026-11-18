import pyodbc


class Conexao:
    def __init__(self, ipServidor: str, banco: str, usuario: str, senha: str):
        self._ip_servidor = ipServidor
        self._banco = banco
        self._usuario = usuario
        self._senha = senha

    def obter_conexao(self) -> pyodbc.Connection:
        return pyodbc.connect(
            "DRIVER=SQL SERVER;"
            f"SERVER={self._ip_servidor};"
            f"DATABASE={self._banco};"
            f"UID={self._usuario};"
            f"PWD={self._senha};"
            "TrustServerCertificate=YES"
        )


class Executor(Conexao):
    def executar_query(self, *, query: str, parametros: list, fetch: str | None = None):
        conexao = None
        try:
            conexao = self.obter_conexao()
            cursor = conexao.cursor()
            cursor.execute(query, parametros)

            if fetch == "one":
                colunas = [coluna[0] for coluna in cursor.description]
                dados = cursor.fetchone()
                return dict(zip(colunas, dados)) if dados else None

            if fetch == "all":
                colunas = [coluna[0] for coluna in cursor.description]
                return [dict(zip(colunas, dados)) for dados in cursor.fetchall()]

            conexao.commit()
            return None
        finally:
            if conexao is not None:
                conexao.close()
