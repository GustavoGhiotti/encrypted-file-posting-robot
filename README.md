# Encrypted File Posting Robot

> **Versão de portfólio.** Código real de produção, anonimizado: nomes de empresa, clientes, pessoas, hosts, e-mails e credenciais foram trocados por valores fictícios (`Acme`, `Banco Alfa`, `10.0.0.x`, `empresa.example`). Toda configuração sensível vem do `.env` (modelo em `.env.example`). O código não aponta para nenhum sistema real.

Robô que prepara arquivos de carga e retorno de um credor, criptografa/descriptografa com GPG e publica/coleta os arquivos em SFTP e em servidor interno, com monitoramento de execução.

**Stack:** Python, GnuPG (CLI), paramiko, Playwright

## Destaques

- Serviços separados para criptografia e descriptografia GPG (chaves fora do repositório).
- Verificação de arquivo já existente no destino para evitar reenvio.

## Estrutura

```text
encrypted-file-posting-robot/
├── scripts/
├── src/
│   ├── application/
│   │   └── service/
│   ├── infrastructure/
│   │   ├── database/
│   │   ├── logging/
│   │   └── services/
│   └── shared/
│       └── utils/
├── start/
└── requirements.txt
```

## Como executar

```bash
pip install -r requirements.txt
python scripts/sirius.py
```
