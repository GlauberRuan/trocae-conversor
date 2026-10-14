# Trocaê — Conversor de Arquivos

**De um formato pra outro, sem aperreio!**

Projeto acadêmico desenvolvido por Marian e Glauber para a disciplina de Sistemas Distribuídos do IFPE — Campus Jaboatão dos Guararapes.

## Sobre o projeto

O Trocaê é uma aplicação de conversão de imagens, áudios e vídeos que utiliza processamento assíncrono e arquitetura distribuída.

O usuário envia um arquivo pela interface web, escolhe o formato de destino e informa seu e-mail. A aplicação registra a solicitação, coloca a tarefa em uma fila e realiza o processamento por meio de Workers independentes.

Após a conclusão, o arquivo fica disponível para download e o usuário recebe uma notificação por e-mail.

## Tecnologias utilizadas

| Componente | Tecnologia |
|---|---|
| Frontend | HTML5, CSS3 e JavaScript |
| API | Python e FastAPI |
| Banco de dados | PostgreSQL |
| Mensageria | RabbitMQ |
| Armazenamento | MinIO |
| Conversão de mídias | FFmpeg e Pillow |
| Notificações | Python, SMTP e Mailpit |
| Containers | Docker e Docker Compose |
| Versionamento | Git e GitHub |

## Arquitetura

O projeto utiliza serviços independentes, executados em containers Docker.

**Fluxo de processamento:**

1. O usuário envia um arquivo pelo frontend.
2. A API recebe a solicitação e armazena o arquivo original no MinIO.
3. O PostgreSQL registra a solicitação com um identificador único (`jobId`).
4. O RabbitMQ recebe uma mensagem para processamento.
5. Um Worker consome a mensagem, realiza a conversão e salva o resultado no MinIO.
6. O status da solicitação é atualizado no PostgreSQL.
7. O serviço de notificação identifica as conversões concluídas e envia um e-mail pelo SMTP.
8. O usuário acompanha o status e baixa o arquivo convertido pela interface web.

## Estrutura do projeto

- **api/** — endpoints, integração com banco, RabbitMQ, MinIO e download.
- **worker/** — consumo das tarefas e conversão dos arquivos.
- **notification/** — envio de notificações por e-mail.
- **frontend/** — interface gráfica da aplicação.
- **docker-compose.yml** — configuração dos serviços.
- **.env.example** — exemplo das variáveis de ambiente.

## Funcionalidades

- Upload de imagens, áudios e vídeos.
- Seleção do formato de saída.
- Processamento assíncrono.
- Acompanhamento do status da conversão.
- Armazenamento de arquivos no MinIO.
- Download dos arquivos convertidos.
- Notificação por e-mail.
- Execução de múltiplos Workers.
- Confirmação manual das mensagens.
- Recuperação de tarefas após interrupção de um Worker.
- Controle de reservas no PostgreSQL.
- Tentativas limitadas de processamento e Dead Letter Queue (DLQ).

## Execução

**Pré-requisitos:** Docker e Docker Compose.

1. Clonar o repositório.
2. Criar o arquivo `.env` a partir de `.env.example` e configurar as credenciais.
3. Construir e iniciar os serviços com dois Workers:

`docker compose up -d --build --scale worker=2`

4. Conferir os containers:

`docker compose ps`

Na primeira execução, verificar se os buckets `originais` e `convertidos` existem no MinIO e se a tabela `conversoes` foi inicializada. A preparação inicial desses recursos deve ser realizada conforme a configuração do ambiente.

### Endereços locais

| Serviço | Endereço |
|---|---|
| Trocaê | http://localhost:8000/app |
| Documentação da API | http://localhost:8000/docs |
| RabbitMQ Management | http://localhost:15672 |
| MinIO Console | http://localhost:9001 |
| Mailpit | http://localhost:8025 |

## Escalabilidade

A aplicação permite aumentar o número de Workers sem modificar o código.

Exemplo com três instâncias:

`docker compose up -d --scale worker=3 worker`

Cada Worker consome tarefas do RabbitMQ. O controle de reservas no PostgreSQL ajuda a impedir que instâncias diferentes executem simultaneamente a mesma solicitação.

## Tratamento de falhas

O sistema utiliza confirmações manuais no RabbitMQ e mecanismos de recuperação de mensagens.

Em caso de falha durante a conversão, o processamento pode ser tentado novamente. Erros persistentes são limitados a três tentativas e encaminhados para uma Dead Letter Queue.

O PostgreSQL mantém o status das solicitações e as informações de controle de execução.

## Testes realizados

Foram realizados testes de conversão de imagens, áudios e vídeos, além de testes de distribuição de solicitações entre dois Workers, mensagens duplicadas, recuperação após queda de container e encaminhamento de erros persistentes à DLQ.

### Comparação preliminar de desempenho

| Cenário | Solicitações | Tempo medido |
|---|---:|---:|
| 1 Worker | 10 | 5,21 segundos |
| 2 Workers | 10 | 3,20 segundos |

A redução observada foi de aproximadamente **38,6%** no tempo medido.

Esses resultados são preliminares: incluem inicialização de serviços e verificações periódicas da fila, não representando uma medição isolada do tempo de conversão.

## Observações

O Mailpit é utilizado para capturar e verificar os e-mails no ambiente local de desenvolvimento.

Os links de download utilizam o endereço local da API. Para acesso externo, é necessário configurar um endereço público apropriado.

O sistema de notificações consulta periodicamente o PostgreSQL para identificar conversões concluídas.

## Autores

**Glauber Ruan e Marian Lopes**

Instituto Federal de Pernambuco — IFPE  
Campus Jaboatão dos Guararapes  
Disciplina: Sistemas Distribuídos