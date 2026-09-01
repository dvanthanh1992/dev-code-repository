from __future__ import annotations

from pydantic import BaseModel, Field


class DemoValueRequest(BaseModel):
    value: str = Field(min_length=1, max_length=200)
