"""
Upload de imagens (Cloudinary). Sem CLOUDINARY_URL configurada (ex.: dev local
sem conta Cloudinary), ou se o Cloudinary falhar por qualquer motivo (rede,
credencial, formato rejeitado), upload_imagem() retorna None sem quebrar a
página — o formulário segue funcionando normalmente, só sem foto.
"""
import os
import sys

TAMANHO_MAXIMO = 10 * 1024 * 1024  # 10MB (limite do plano gratuito do Cloudinary)

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

    try:
        resultado = cloudinary.uploader.upload(
            file_storage, folder=pasta, resource_type="image"
        )
        return resultado.get("secure_url")
    except Exception as e:
        print(f"[uploads] falha ao enviar imagem pro Cloudinary: {e}", file=sys.stderr)
        return None
