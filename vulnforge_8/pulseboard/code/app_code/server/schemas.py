from typing import Literal

from pydantic import BaseModel, Field


class FilterBody(BaseModel):
    field: Literal["region"] = "region"
    operator: Literal["contains"] = "contains"
    value: str = Field(min_length=1, max_length=96)


class CheckBody(BaseModel):
    filter: FilterBody
    id_filter: str = Field(default="", max_length=12)


class CheckResponse(BaseModel):
    status: Literal["processed"]
