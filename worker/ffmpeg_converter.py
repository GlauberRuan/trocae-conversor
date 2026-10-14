
import subprocess
from pathlib import Path


FORMATOS_AUDIO = {"mp3", "wav"}
FORMATOS_VIDEO = {"mp4", "avi", "mov"}


def converter_audio_video(
    caminho_origem: str,
    caminho_destino: str,
    tipo_midia: str,
    formato_destino: str
):
    """
    Converte arquivos de áudio ou vídeo usando FFmpeg.
    """

    formato = formato_destino.lower().lstrip(".")

    if tipo_midia == "audio":
        if formato not in FORMATOS_AUDIO:
            raise ValueError(
                f"Formato de áudio não suportado: {formato}"
            )

    elif tipo_midia == "video":
        if formato not in FORMATOS_VIDEO:
            raise ValueError(
                f"Formato de vídeo não suportado: {formato}"
            )

    else:
        raise ValueError(
            f"Tipo de mídia não suportado: {tipo_midia}"
        )

    # Garante que a pasta de destino exista
    Path(caminho_destino).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Comando básico do FFmpeg
    comando = [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-i", caminho_origem
    ]

    if tipo_midia == "audio":
        comando.extend(["-vn"])

        if formato == "mp3":
            comando.extend([
                "-c:a", "libmp3lame",
                "-b:a", "192k"
            ])

        elif formato == "wav":
            comando.extend([
                "-c:a", "pcm_s16le"
            ])

    elif tipo_midia == "video":
        comando.extend([
            "-c:v", "mpeg4",
            "-q:v", "5",
            "-c:a", "aac"
        ])

    comando.append(caminho_destino)

    # Executa o FFmpeg e aguarda o resultado
    resultado = subprocess.run(
        comando,
        capture_output=True,
        text=True,
        timeout=1800
    )

    if resultado.returncode != 0:
        raise RuntimeError(
            "Falha na conversão com FFmpeg: "
            + resultado.stderr[-2000:]
        )

    # Verifica se o arquivo foi realmente criado
    arquivo_convertido = Path(caminho_destino)

    if (
        not arquivo_convertido.exists()
        or arquivo_convertido.stat().st_size == 0
    ):
        raise RuntimeError(
            "O FFmpeg não gerou um arquivo válido."
        )

    return caminho_destino
