from datetime import datetime
from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED = {"image": {"jpg", "jpeg", "png", "webp", "heic", "heif"}, "video": {"mp4", "webm", "mov"}, "audio": {"webm", "wav", "mp3", "m4a", "ogg"}}


def file_kind(upload):
    extension = Path(upload.filename or "").suffix.lower().lstrip(".")
    for kind, extensions in ALLOWED.items():
        if extension in extensions:
            return kind
    return None


def _valid_signature(kind, extension, header):
    if kind == "image":
        return (extension in {"jpg", "jpeg"} and header.startswith(b"\xff\xd8\xff")) or (extension == "png" and header.startswith(b"\x89PNG\r\n\x1a\n")) or (extension == "webp" and header.startswith(b"RIFF") and header[8:12] == b"WEBP") or (extension in {"heic", "heif"} and header[4:8] == b"ftyp")
    if kind == "video":
        return (extension in {"mp4", "mov"} and header[4:8] == b"ftyp") or (extension == "webm" and header.startswith(b"\x1aE\xdf\xa3"))
    return (extension == "webm" and header.startswith(b"\x1aE\xdf\xa3")) or (extension == "wav" and header.startswith(b"RIFF") and header[8:12] == b"WAVE") or (extension == "mp3" and (header.startswith(b"ID3") or header.startswith(b"\xff\xfb") or header.startswith(b"\xff\xf3"))) or (extension == "m4a" and header[4:8] == b"ftyp") or (extension == "ogg" and header.startswith(b"OggS"))


def validate_upload(upload):
    kind = file_kind(upload)
    extension = Path(upload.filename or "").suffix.lower().lstrip(".")
    if not kind:
        raise ValueError("סוג הקובץ אינו נתמך")
    header = upload.stream.read(16)
    upload.stream.seek(0)
    if not _valid_signature(kind, extension, header):
        raise ValueError("תוכן הקובץ אינו תואם לסוג שנבחר")
    return kind


def save_upload(upload):
    kind = validate_upload(upload)
    now = datetime.now(); folder = ROOT / f"{kind}s" / now.strftime("%Y") / now.strftime("%m"); folder.mkdir(parents=True, exist_ok=True)
    original = Path((upload.filename or "").replace("\\", "/")).name or f"{kind}.bin"
    stored = f"{uuid4().hex}_{secure_filename(original) or kind + '.bin'}"; destination = folder / stored
    upload.save(destination)
    return (kind, str(destination.relative_to(ROOT.parent)).replace("\\", "/"), original, upload.mimetype or "application/octet-stream", destination.stat().st_size)


def delete_stored(local_path):
    candidate = (ROOT.parent / local_path).resolve()
    if ROOT.resolve() in candidate.parents and candidate.is_file():
        candidate.unlink()
