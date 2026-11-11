import re

from pydantic import BaseModel, Field, field_validator


class Note(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    summary: str = Field(min_length=20)
    key_points: list[str] = Field(min_length=1, max_length=12)
    tags: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("key_points")
    @classmethod
    def _strip_points(cls, value: list[str]) -> list[str]:
        points = [p.strip() for p in value if p.strip()]
        if not points:
            raise ValueError("key_points vazio")
        return points

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, value: list[str]) -> list[str]:
        tags = [re.sub(r"[^a-z0-9à-ÿ]+", "-", t.lower()).strip("-") for t in value]
        return list(dict.fromkeys(t for t in tags if t))
