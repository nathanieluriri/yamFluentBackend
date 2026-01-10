from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

T = TypeVar("T")

class APIResponse(GenericModel, Generic[T]):
    status_code: int = Field(serialization_alias="status_code")
    data: Optional[T] = Field(default=None, serialization_alias="data")
    detail: str = Field(serialization_alias="detail")

    model_config = {"populate_by_name": True}
