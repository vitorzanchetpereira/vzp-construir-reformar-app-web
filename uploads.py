"""
Upload de imagens (Cloudinary). Sem CLOUDINARY_URL configurada (ex.: dev local
sem conta Cloudinary), upload_imagem() retorna None sem erro — o formulário
segue funcionando normalmente, só sem foto.
"""
import os

TAMANHO_MAXIMO = 5 * 1024 * 1024  # 5MB

_CONFIGURADO = bool(os.environ.get("CLOUDINARY_URL"))
if _CONFIGURADO:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(secure=True)


def upload_imagem(file_storage, pasta="construir-reformar"):
    if not _CONFIGURADO or not file_storage or not file_storage.filename:
        return None
    if not (file_storage.mimetype or "").startswith("image/"):
        return None

    file_storage.seek(0, os.SEEK_END)
    tamanho = file_storage.tell()
    file_storage.seek(0)
    if tamanho > TAMANHO_MAXIMO:
        return None

    resultado = cloudinary.uploader.upload(
        file_storage, folder=pasta, resource_type="image"
    )
    return resultado.get("secure_url")
