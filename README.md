
# Conversor Escalável de Mídia

Projeto desenvolvido para a disciplina de Sistemas Distribuídos.

## Objetivo

Desenvolver uma aplicação web capaz de converter arquivos de vídeo, áudio e imagem de forma assíncrona, utilizando uma arquitetura distribuída e escalável.

## Funcionalidades previstas

- Upload de arquivos de vídeo, áudio e imagem.
- Seleção do formato de saída.
- Processamento assíncrono das conversões.
- Acompanhamento do status das solicitações.
- Disponibilização dos arquivos convertidos.
- Notificação por e-mail após a conclusão.
- Processamento paralelo utilizando múltiplos workers.
- Tratamento de falhas e tentativas de reprocessamento.

## Tecnologias

- Python e FastAPI
- HTML, CSS e JavaScript
- RabbitMQ
- MinIO
- PostgreSQL
- FFmpeg e Pillow
- Mailpit
- Docker e Docker Compose

## Arquitetura

O sistema será composto por quatro componentes principais:

- **Frontend:** interface utilizada pelo usuário.
- **API:** recebimento de arquivos e gerenciamento das solicitações.
- **Worker:** processamento das conversões.
- **Notification:** envio de notificações por e-mail.

## Como executar

As instruções de instalação e execução serão adicionadas durante o desenvolvimento.

## Status

Em desenvolvimento.
