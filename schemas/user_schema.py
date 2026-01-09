from datetime import timedelta
from typing_extensions import Annotated
from typing import TypedDict
from schemas.imports import *
from pydantic import AliasChoices, Field, conint, field_validator
import time
from security.hash import hash_password

class UserSignUp(BaseModel):
    firstName:str
    lastName:str    
    email:EmailStr
    password:str | bytes
    
    
class UserLogin(BaseModel):
    email:EmailStr
    password:str | bytes
    
    
class UserBase(BaseModel):
    # Add other fields here 
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    loginType:LoginType
    email:EmailStr
    password:str | bytes
    oauth_access_token:Optional[str]=None
    oauth_refresh_token:Optional[str]=None
    pass

class UserRefresh(BaseModel):
    # Add other fields here 
    refresh_token:str
    pass


class UserCreate(UserBase):
    # Add other fields here
     
    date_created: int = Field(default_factory=lambda: int(time.time()))
    last_updated: int = Field(default_factory=lambda: int(time.time()))
    @model_validator(mode='after')
    def obscure_password(self):
        self.password=hash_password(self.password)
        return self
class UserUpdate(BaseModel):
    # Add other fields here 
    password: Optional[str | bytes] = None
    notifications: Optional["UserNotifications"] = None
    userPersonalProfilingData: Optional["UserPersonalProfilingData"] = None
    last_updated: int = Field(default_factory=lambda: int(time.time()))
    @model_validator(mode='after')
    def obscure_password(self):
        if self.password:
            self.password = hash_password(self.password)
        return self
    
    
    


class UserPersonalProfilingData(BaseModel):
    nativeLanguage: NativeLanguage
    currentProficiency: CurrentProficiency
    mainGoals: List[MainGoals] = Field(
        ..., 
        min_length=1,   
        max_length=4     
    )
    learnerType:LearnerType
    dailyPracticeTime:DailyPracticeTime
    @field_validator("mainGoals")
    @classmethod
    def unique_goals(cls, v):
        if len(set(v)) != len(v):
            raise ValueError("Main goals must be unique")
        return v
    
    
class UserNotificationPreference(BaseModel):
    enabled: bool = False


class UserNotifications(BaseModel):
    preference: UserNotificationPreference = Field(
        default_factory=UserNotificationPreference
    )


class UserUpdateProfile(BaseModel):
    # Add other fields here 
    userPersonalProfilingData:Optional[UserPersonalProfilingData]=None
    last_updated: int = Field(default_factory=lambda: int(time.time()))
 

class UserPersonalProfilingDataOptions(BaseModel):
    nativeLanguages: List[str]
    currentProficiencies: List[str]
    mainGoals: List[str]
    learnerTypes: List[str]
    dailyPracticeTimes: List[str]

from enum import Enum


class UserScenerioOptions(BaseModel):
    scenarioName: ScenarioName
    scenarioDifficultyRating: Annotated[int, Field(ge=1, le=5)]
    scenerioImageUrl: str
    benefitsOfScenerio: str


class ScenarioConfig(TypedDict):
    scenarioDifficultyRating: int
    scenerioImageUrl: str
    benefitsOfScenerio: str


SCENARIO_CONFIG: dict[ScenarioName, ScenarioConfig] = {
    ScenarioName.CAFE_ORDERING: {
        "scenarioDifficultyRating": 1,
        "scenerioImageUrl": "https://placehold.co/600x400?text=Cafe+Ordering",
        "benefitsOfScenerio": "Practice quick ordering, clarifying items, and handling payment politely.",
    },
    ScenarioName.AIRPORT_CHECK_IN: {
        "scenarioDifficultyRating": 3,
        "scenerioImageUrl": "https://placehold.co/600x400?text=Airport+Check-in",
        "benefitsOfScenerio": "Build confidence with documents, baggage questions, and gate changes.",
    },
    ScenarioName.DOCTOR_VISIT: {
        "scenarioDifficultyRating": 3,
        "scenerioImageUrl": "https://placehold.co/600x400?text=Doctor+Visit",
        "benefitsOfScenerio": "Explain symptoms clearly, ask follow-up questions, and understand advice.",
    },
    ScenarioName.JOB_INTERVIEW: {
        "scenarioDifficultyRating": 4,
        "scenerioImageUrl": "https://placehold.co/600x400?text=Job+Interview",
        "benefitsOfScenerio": "Answer behavioral questions, describe experience, and ask smart questions.",
    },
    ScenarioName.SCHOOL_CLASS_PARTICIPATION: {
        "scenarioDifficultyRating": 2,
        "scenerioImageUrl": "https://placehold.co/600x400?text=School+Class+Participation",
        "benefitsOfScenerio": "Practice asking and answering questions in class with clear pronunciation.",
    },
    ScenarioName.SCHOOL_PRESENTATION: {
        "scenarioDifficultyRating": 3,
        "scenerioImageUrl": "https://placehold.co/600x400?text=School+Presentation",
        "benefitsOfScenerio": "Organize ideas, signal transitions, and handle audience questions.",
    },
    ScenarioName.SCHOOL_ENROLLMENT: {
        "scenarioDifficultyRating": 2,
        "scenerioImageUrl": "https://placehold.co/600x400?text=School+Enrollment",
        "benefitsOfScenerio": "Handle forms, requirements, and schedule questions with staff.",
    },
    ScenarioName.UNIVERSITY_ORIENTATION: {
        "scenarioDifficultyRating": 2,
        "scenerioImageUrl": "https://placehold.co/600x400?text=University+Orientation",
        "benefitsOfScenerio": "Navigate campus info sessions and ask for directions and details.",
    },
    ScenarioName.UNIVERSITY_SEMINAR_DISCUSSION: {
        "scenarioDifficultyRating": 4,
        "scenerioImageUrl": "https://placehold.co/600x400?text=University+Seminar+Discussion",
        "benefitsOfScenerio": "Practice turn-taking, citing points, and respectful disagreement.",
    },
    ScenarioName.UNIVERSITY_ADMIN_OFFICE: {
        "scenarioDifficultyRating": 3,
        "scenerioImageUrl": "https://placehold.co/600x400?text=University+Admin+Office",
        "benefitsOfScenerio": "Resolve enrollment issues, deadlines, and fee questions confidently.",
    },
    ScenarioName.GROUP_PROJECT_MEETING: {
        "scenarioDifficultyRating": 3,
        "scenerioImageUrl": "https://placehold.co/600x400?text=Group+Project+Meeting",
        "benefitsOfScenerio": "Assign tasks, negotiate deadlines, and summarize next steps.",
    },
    ScenarioName.DORM_ROOMMATE_DISCUSSION: {
        "scenarioDifficultyRating": 2,
        "scenerioImageUrl": "https://placehold.co/600x400?text=Dorm+Roommate+Discussion",
        "benefitsOfScenerio": "Discuss shared rules, resolve issues, and stay polite but direct.",
    },
    ScenarioName.LIBRARY_RESEARCH_HELP: {
        "scenarioDifficultyRating": 2,
        "scenerioImageUrl": "https://placehold.co/600x400?text=Library+Research+Help",
        "benefitsOfScenerio": "Ask for sources, explain topics, and understand guidance.",
    },
    ScenarioName.CAMPUS_CLUB_MEETING: {
        "scenarioDifficultyRating": 2,
        "scenerioImageUrl": "https://placehold.co/600x400?text=Campus+Club+Meeting",
        "benefitsOfScenerio": "Introduce yourself, share interests, and volunteer for roles.",
    },
    ScenarioName.WORKPLACE_TEAM_MEETING: {
        "scenarioDifficultyRating": 4,
        "scenerioImageUrl": "https://placehold.co/600x400?text=Workplace+Team+Meeting",
        "benefitsOfScenerio": "Give updates, clarify blockers, and align on priorities.",
    },
    ScenarioName.CUSTOMER_SUPPORT_CALL: {
        "scenarioDifficultyRating": 4,
        "scenerioImageUrl": "https://placehold.co/600x400?text=Customer+Support+Call",
        "benefitsOfScenerio": "Explain issues clearly, follow troubleshooting steps, and confirm fixes.",
    },
    ScenarioName.APARTMENT_RENTAL_VIEWING: {
        "scenarioDifficultyRating": 3,
        "scenerioImageUrl": "https://placehold.co/600x400?text=Apartment+Rental+Viewing",
        "benefitsOfScenerio": "Ask about lease terms, utilities, and neighborhood details.",
    },
    ScenarioName.BANK_ACCOUNT_OPENING: {
        "scenarioDifficultyRating": 3,
        "scenerioImageUrl": "https://placehold.co/600x400?text=Bank+Account+Opening",
        "benefitsOfScenerio": "Understand account options, fees, and required documents.",
    },
}


def build_user_scenerio_options() -> List[UserScenerioOptions]:
    missing = [name for name in ScenarioName if name not in SCENARIO_CONFIG]
    extra = [name for name in SCENARIO_CONFIG.keys() if name not in ScenarioName]
    if missing or extra:
        raise TypeError(
            "Scenario config mismatch: "
            f"missing={missing}, extra={extra}"
        )
    options: List[UserScenerioOptions] = []
    for scenario_name in ScenarioName:
        config = SCENARIO_CONFIG[scenario_name]
        options.append(
            UserScenerioOptions(
                scenarioName=scenario_name,
                scenarioDifficultyRating=config["scenarioDifficultyRating"],
                scenerioImageUrl=config["scenerioImageUrl"],
                benefitsOfScenerio=config["benefitsOfScenerio"],
            )
        )
    return options
    

class UserOut(UserBase):
    # Add other fields here 
    loginType:Optional[LoginType]=None
    userPersonalProfilingData:Optional[UserPersonalProfilingData]=None
    onboardingCompleted:Optional[bool]=False
    notifications: Optional[UserNotifications] = None
    avatarUrl:str =Field(default="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS6LXNJFTmLzCoExghcATlCWG85kI8dsnhJng&s")
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
    date_Joined:Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("date_Joined", "dateJoined"),
        serialization_alias="dateJoined",
    )
    accountStatus:Optional[AccountStatus]=AccountStatus.ACTIVE
    last_updated: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("last_updated", "lastUpdated"),
        serialization_alias="lastUpdated",
    )
 
    refresh_token: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("refresh_token", "refreshToken"),
        serialization_alias="refreshToken",
    )
    access_token: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("access_token", "accessToken"),
        serialization_alias="accessToken",
    )
    
    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if "_id" in values and isinstance(values["_id"], ObjectId):
            values["_id"] = str(values["_id"])  # coerce to string before validation
        return values
    
    
    @model_validator(mode="before")
    @classmethod
    def normalize_date_joined(cls, values):
        date_joined = values.get("date_Joined")
        date_created = values.get("date_created")
        dt = None

        if date_joined is None and date_created is not None:
            dt = datetime.fromtimestamp(date_created, tz=timezone.utc)
        elif isinstance(date_joined, int):
            dt = datetime.fromtimestamp(date_joined, tz=timezone.utc)
        elif isinstance(date_joined, datetime):
            dt = date_joined
        elif isinstance(date_joined, str):
            try:
                dt = datetime.fromisoformat(date_joined.replace("Z", "+00:00"))
            except Exception:
                dt = None

        if dt:
            values["date_Joined"] = dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

        return values
    
    @model_validator(mode="after")
    @classmethod
    def set_date_joined(cls, model):
        """If date_joined is None, calculate from date_created."""
        
        if model.date_Joined is None and model.date_created is not None:
            # Convert timestamp to UTC datetime
            dt_created = datetime.fromtimestamp(model.date_created, tz=timezone.utc)

            # Example calculation: here we just use the same date_created (adjust as needed)
            dt_joined = dt_created  # or dt_created + timedelta(days=1)

            # Format as ISO 8601 with milliseconds and UTC offset
            model.date_Joined = dt_joined.isoformat(timespec="milliseconds")
        if model.userPersonalProfilingData is None:
            model.onboardingCompleted=False
        else:
            model.onboardingCompleted=True
        return model
    class Config:
        populate_by_name = True  # allows using `id` when constructing the model
        arbitrary_types_allowed = True  # allows ObjectId type
        json_encoders = {
            ObjectId: str  # automatically converts ObjectId → str
        }
        
        
        
        
class UserUpdatePassword(UserUpdate):
    pass
        
        
