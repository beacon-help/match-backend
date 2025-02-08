from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Config:
    ENV: Literal["dev", "test", "live"]
