
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter()


@router.get("/app", include_in_schema=False)
def abrir_interface():
    caminho = Path(__file__).resolve().parent / "frontend.html"

    return FileResponse(
        caminho,
        media_type="text/html",
    )
