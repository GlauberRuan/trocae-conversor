
from pathlib import Path

from PIL import Image, ImageOps


FORMATOS_IMAGEM = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP"
}


def converter_imagem(
    caminho_origem: str,
    caminho_destino: str,
    formato_destino: str
):
    """
    Converte uma imagem para JPG, PNG ou WEBP.

    Exemplo:
    foto.jpg -> foto.webp
    """

    formato = formato_destino.lower().lstrip(".")

    if formato not in FORMATOS_IMAGEM:
        raise ValueError(
            f"Formato de imagem não suportado: {formato}"
        )

    # Garante que a pasta de destino exista
    Path(caminho_destino).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with Image.open(caminho_origem) as imagem:

        # Corrige a orientação de fotos que possuem
        # metadados EXIF de rotação
        imagem = ImageOps.exif_transpose(imagem)

        # JPG não suporta transparência.
        # Por isso, usamos um fundo branco quando
        # a imagem original possui transparência.
        if formato in {"jpg", "jpeg"}:
            if (
                imagem.mode in {"RGBA", "LA"}
                or "transparency" in imagem.info
            ):
                imagem_rgba = imagem.convert("RGBA")

                fundo = Image.new(
                    "RGB",
                    imagem_rgba.size,
                    (255, 255, 255)
                )

                fundo.paste(
                    imagem_rgba,
                    mask=imagem_rgba.getchannel("A")
                )

                imagem = fundo

            else:
                imagem = imagem.convert("RGB")

        # Salva a imagem no formato solicitado
        imagem.save(
            caminho_destino,
            format=FORMATOS_IMAGEM[formato]
        )

    return caminho_destino
