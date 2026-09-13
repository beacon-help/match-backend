import hashlib
from pathlib import Path

from match.domain.interfaces import ImageRepository

STORAGE_DIR = ".data/imgs"


class LocalImageRepository(ImageRepository):
    def __init__(self, storage_dir: str = STORAGE_DIR) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, image: bytes, task_id: int) -> str:
        file_hash = hashlib.sha256(image).hexdigest()
        task_dir = self.storage_dir / str(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        file_path = task_dir / file_hash
        file_path.write_bytes(image)
        return str(file_path)

    def read(self, image_id: str) -> bytes:
        return Path(image_id).read_bytes()

    def delete(self, image_id: str) -> None:
        file_path = Path(image_id)
        if file_path.exists():
            file_path.unlink()
