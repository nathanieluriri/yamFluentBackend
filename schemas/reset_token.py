from schemas.imports import *
from pydantic import AliasChoices, Field
import time

class ResetTokenBase(BaseModel):
    userId:str
    userType:UserType
    token:str
    expiresAt: Optional[datetime] = Field(
        default=None,
        validation_alias=AliasChoices("expiresAt", "expires_at"),
        serialization_alias="expiresAt",
    )
    used: bool = False
    usedAt: Optional[datetime] = Field(
        default=None,
        validation_alias=AliasChoices("usedAt", "used_at"),
        serialization_alias="usedAt",
    )
    

class ResetTokenCreate(ResetTokenBase):
    date_created: int = Field(default_factory=lambda: int(time.time()))
    last_updated: int = Field(default_factory=lambda: int(time.time()))

class ResetTokenUpdate(BaseModel):
    last_updated: int = Field(default_factory=lambda: int(time.time()))

class ResetTokenOut(ResetTokenBase):
    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    date_created: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("date_created", "dateCreated"),
        serialization_alias="dateCreated",
    )
    last_updated: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("last_updated", "lastUpdated"),
        serialization_alias="lastUpdated",
    )
    
    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if "_id" in values and isinstance(values["_id"], ObjectId):
            values["_id"] = str(values["_id"])
        return values
            
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders ={
            ObjectId: str
        }
