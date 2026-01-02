from bson import ObjectId
from pydantic import GetJsonSchemaHandler
from pydantic import BaseModel, EmailStr, Field,model_validator
from pydantic_core import core_schema
from datetime import datetime,timezone
from typing import Optional,List,Any
from enum import Enum
import time

class ScenarioName(str, Enum):
    CAFE_ORDERING = "cafe_ordering"
    AIRPORT_CHECKIN = "airport_checkin"
    DOCTOR_VISIT = "doctor_visit"
    JOB_INTERVIEW = "job_interview"
    SCHOOL_CLASS_PARTICIPATION = "school_class_participation"
    SCHOOL_PRESENTATION = "school_presentation"
    SCHOOL_ENROLLMENT = "school_enrollment"
    UNIVERSITY_ORIENTATION = "university_orientation"
    UNIVERSITY_SEMINAR_DISCUSSION = "university_seminar_discussion"
    UNIVERSITY_ADMIN_OFFICE = "university_admin_office"
    GROUP_PROJECT_MEETING = "group_project_meeting"
    DORM_ROOMMATE_DISCUSSION = "dorm_roommate_discussion"
    LIBRARY_RESEARCH_HELP = "library_research_help"
    CAMPUS_CLUB_MEETING = "campus_club_meeting"
    WORKPLACE_TEAM_MEETING = "workplace_team_meeting"
    CUSTOMER_SUPPORT_CALL = "customer_support_call"
    APARTMENT_RENTAL_VIEWING = "apartment_rental_viewing"
    BANK_ACCOUNT_OPENING = "bank_account_opening"
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
    BEGINNER = "[https://res.cloudinary.com/dloh0ffv3/image/upload/v1767333942/begginer_current_proficiency_a7bbpe.png] (BEGINNER) I know basic words and phrases. "
    INTERMEDIATE = "[https://res.cloudinary.com/dloh0ffv3/image/upload/v1767333942/intermediate_current_proficiency_fhwou3.png] (INTERMEDIATE) I can hold everyday conversation."
    ADVANCED = "[https://res.cloudinary.com/dloh0ffv3/image/upload/v1767333942/advanced_current_proficiency_y0usq8.png] (ADVANCED) I speak confidently and fluently."
    
    
class LearnerType(str, Enum):
    SpeakingFirstLearner = "[https://res.cloudinary.com/dloh0ffv3/image/upload/v1767333942/Speaking_first_learner_type_xy4js2.png] (Speaking-first learner) I prefer to speak as much as possible.  "
    VisualLearner = "[https://res.cloudinary.com/dloh0ffv3/image/upload/v1767333942/Visual_learner_type_q2q4zn.png] (Visual learner) I learn better with images and examples."
    ShortBurstLearner = " [https://res.cloudinary.com/dloh0ffv3/image/upload/v1767333942/Short_burst_learner_type_agw8xv.png] (Short-burst learner) I like quick, focused practice sessions."
    StructuredLearner="[https://res.cloudinary.com/dloh0ffv3/image/upload/v1767333942/Structural_learner_type_nbarte.png] (Structured learner) I prefer step-by-step lessons."
    


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
