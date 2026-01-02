from bson import ObjectId
from pydantic import GetJsonSchemaHandler
from pydantic import BaseModel, EmailStr, Field,model_validator
from pydantic_core import core_schema
from datetime import datetime,timezone
from typing import Optional,List,Any
from enum import Enum
import time

class UserType(str,Enum):
    member= "member"
   
    admin="admin"

class ResetPasswordInitiation(BaseModel):
    # Add other fields here
    email:EmailStr 
    
class ResetPasswordInitiationResponse(BaseModel):
    # Add other fields here
    message:str
    
    
class ResetPasswordConclusion(BaseModel):
    # Add other fields here
    resetToken:str
    password:str
    
class LoginType(str, Enum):
    google = "GOOGLE"
    password = "PASSWORD"
    passwordless="PASSWORDLESS"

class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"



class MainGoals(str, Enum):
    Travel="Travel"
    Business="Business"
    Academic="Academic"
    EverydayConversations="Everyday Conversations"
    SoundMorePolite="Sound More Polite"
    SoundClearer="Sound Clearer"
    ReduceHesitation="Reduce Hesitation"
    ImprovePronunciation="Improve Pronunciation"
    SucceedInJobInterviews="Succeed in Job Interviews"
    SoundMoreNatural="Sound More Natural"
    StopTranslatingInMyHead="Stop Translating in My Head"
 
    


class CurrentProficiency(str, Enum):
    BEGINNER = "(BEGINNER) I know basic words and phrases. "
    INTERMEDIATE = "(INTERMEDIATE) I can hold everyday conversation."
    ADVANCED = "(ADVANCED) I speak confidently and fluently."
    
    
class LearnerType(str, Enum):
    SpeakingFirstLearner = "(Speaking-first learner) I prefer to speak as much as possible.  "
    VisualLearner = "(Visual learner) I learn better with images and examples."
    ShortBurstLearner = "(Short-burst learner) I like quick, focused practice sessions."
    StructuredLearner="(Structured learner) I prefer step-by-step lessons."
    


class DailyPracticeTime(str, Enum):
    fiveMins = "5 minutes a day — the easiest way to start."
    tenMins = "10 minutes a day — small, steady progress."
    twelveMins = "12 minutes a day — a little extra momentum."
    fifteenMins = "15 minutes a day — a focused daily habit."
    twentyMins = "20 minutes a day — deeper daily practice."
    


class NativeLanguage(str, Enum):
    ARABIC = "Arabic (العربية)"
    BENGALI = "Bengali (বাংলা)"
    CHINESE = "Chinese (中文)"
    CZECH = "Czech (Čeština)"
    DUTCH = "Dutch (Nederlands)"
    ENGLISH = "English (English)"
    FILIPINO = "Filipino (Filipino)"
    FINNISH = "Finnish (Suomi)"
    FRENCH = "French (Français)"
    GERMAN = "German (Deutsch)"
    GREEK = "Greek (Ελληνικά)"
    HAUSA = "Hausa (Hausa)"
    HINDI = "Hindi (हिन्दी)"
    IGBO = "Igbo (Igbo)"
    ITALIAN = "Italian (Italiano)"
    JAPANESE = "Japanese (日本語)"
    KOREAN = "Korean (한국어)"
    MALAY = "Malay (Bahasa Melayu)"
    PERSIAN = "Persian (فارسی)"
    POLISH = "Polish (Polski)"
    PORTUGUESE = "Portuguese (Português)"
    ROMANIAN = "Romanian (Română)"
    RUSSIAN = "Russian (Русский)"
    SPANISH = "Spanish (Español)"
    SWAHILI = "Swahili (Kiswahili)"
    SWEDISH = "Swedish (Svenska)"
    THAI = "Thai (ไทย)"
    TURKISH = "Turkish (Türkçe)"
    UKRAINIAN = "Ukrainian (Українська)"
    VIETNAMESE = "Vietnamese (Tiếng Việt)"
    YORUBA = "Yoruba (Yorùbá)"

class Permission(BaseModel):
    name: str
    methods: List[str]
    path: str
    description: Optional[str] = None

class PermissionList(BaseModel):
    permissions: List[Permission]
