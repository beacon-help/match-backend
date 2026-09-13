import uuid
from pathlib import Path

from match.domain.interfaces import ImageRepository

STORAGE_DIR = ".data/imgs"


class LocalImageRepository(ImageRepository):
    def __init__(self, storage_dir: str = STORAGE_DIR, backend_host: str = "") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.backend_host = backend_host

    def _file_path(self, image_id: str) -> Path:
        return self.storage_dir / image_id

    def upload(self, image: bytes) -> str:
        image_id = str(uuid.uuid4())
        self._file_path(image_id).write_bytes(image)
        return image_id

    def read(self, image_ids: list[str]) -> dict[str, bytes]:
        return {image_id: self._file_path(image_id).read_bytes() for image_id in image_ids}

    def delete(self, image_id: str) -> None:
        file_path = self._file_path(image_id)
        if file_path.exists():
            file_path.unlink()

    def path(self, image_id: str) -> str:
        return f"{self.backend_host}/task/images/{image_id}"
