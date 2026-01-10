import os
from apscheduler.jobstores.mongodb import MongoDBJobStore
from pymongo import MongoClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
mongo_client = MongoClient(MONGO_URL)
jobstore = MongoDBJobStore(database="apscheduler", collection="background_jobs", client=mongo_client)
scheduler = AsyncIOScheduler()
scheduler.add_jobstore(jobstore)

