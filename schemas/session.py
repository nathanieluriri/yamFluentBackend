from schemas.imports import *
from pydantic import AliasChoices, Field, field_validator
import time


def _calculate_average_score(script: Optional[FluencyScript]) -> Optional[float]:
    if not script or not getattr(script, "turns", None):
        return None
    per_turn_averages = []
    for turn in script.turns:
        score = getattr(turn, "score", None)
        if score is None:
            continue
        values = [score.confidence, score.fluency, score.hesitation]
        values = [value for value in values if value is not None]
        if values:
            per_turn_averages.append(sum(values) / len(values))
    if not per_turn_averages:
        return None
    return sum(per_turn_averages) / len(per_turn_averages)


def _calculate_completed(script: Optional[FluencyScript]) -> bool:
    if not script or not getattr(script, "turns", None):
        return False
    return all(
        getattr(turn, "score", None) is not None
        for turn in script.turns
        if getattr(turn, "role", None) == "user"
    )


class SessionBaseRequest(BaseModel):
 
    scenario: ScenarioName
 

class SessionBase(SessionBaseRequest):
    userId:str
 

class SessionCreate(SessionBase):
    script:FluencyScript
    date_created: int = Field(default_factory=lambda: int(time.time()), serialization_alias="dateCreated")
    last_updated: int = Field(default_factory=lambda: int(time.time()), serialization_alias="lastUpdated")


class ScriptTurnsUpdate(BaseModel):
    turns: List[TurnUpdate]
    
    
class SessionUpdate(BaseModel):
    script: ScriptTurnsUpdate
    last_updated: int = Field(default_factory=lambda: int(time.time()), serialization_alias="lastUpdated")
    
class SessionOut(SessionBase):
    script:FluencyScript
    average_score: Optional[float] = Field(default=None, serialization_alias="averageScore")
    completed: Optional[bool] = Field(default=None, serialization_alias="completed")
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
    @field_validator("scenario", mode="before")
    @classmethod
    def normalize_scenario(cls, v):
        if v == "airport_checkin":
            return "airport_check_in"
        return v
    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if "_id" in values and isinstance(values["_id"], ObjectId):
            values["_id"] = str(values["_id"])
        return values
    
    @model_validator(mode="after")
    def set_completed_and_average(self):
        self.average_score = _calculate_average_score(self.script)
        self.completed = _calculate_completed(self.script)
        return self
            
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders ={
            ObjectId: str
        }


class ListOfSessionOut(BaseModel):
    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    scenario: ScenarioName
    totalNumberOfTurns: Optional[int] = Field(default=None, serialization_alias="totalNumberOfTurns")
    last_updated: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("last_updated", "lastUpdated"),
        serialization_alias="lastUpdated",
    )
    average_score: Optional[float] = Field(default=None, serialization_alias="averageScore")
    script: Optional[FluencyScript] = Field(default=None, exclude=True)
    @field_validator("scenario", mode="before")
    @classmethod
    def normalize_scenario(cls, v):
        if v == "airport_checkin":
            return "airport_check_in"
        return v
    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if "_id" in values and isinstance(values["_id"], ObjectId):
            values["_id"] = str(values["_id"])
        return values
    @model_validator(mode="after")
    def set_list_summary_fields(self):
        if self.totalNumberOfTurns is None and self.script is not None:
            total = getattr(self.script, "totalNumberOfTurns", None)
            if total is None and getattr(self.script, "turns", None) is not None:
                total = len(self.script.turns)
            self.totalNumberOfTurns = total
        if self.average_score is None:
            self.average_score = _calculate_average_score(self.script)
        return self

    class Config:
        populate_by_name = True
