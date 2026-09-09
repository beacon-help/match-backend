import hashlib
from pathlib import Path

from match.domain.interfaces import ImageRepository


class LocalImageRepository(ImageRepository):
    def __init__(self, storage_dir: str = "var/uploads") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, image: bytes) -> str:
        file_hash = hashlib.sha256(image).hexdigest()
        file_path = self.storage_dir / file_hash
        file_path.write_bytes(image)
        return str(file_path)

    def delete(self, image_id: str) -> None:
        file_path = Path(image_id)
        if file_path.exists():
            file_path.unlink()
