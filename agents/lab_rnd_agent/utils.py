import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB')]

# Collections
lab_data = db[os.getenv('MONGODB_LAB_COLLECTION')]
research_data = db[os.getenv('MONGODB_RESEARCH_COLLECTION')]
experiments = db[os.getenv('MONGODB_EXPERIMENTS_COLLECTION')]

def log(msg):
    print(f"[LabAgent] {msg}")

async def save_lab_data(data):
    """Save lab sensor data to MongoDB"""
    try:
        result = lab_data.insert_one(data)
        log(f"Saved lab data with ID: {result.inserted_id}")
        return result.inserted_id
    except Exception as e:
        log(f"Error saving lab data: {str(e)}")
        return None

async def save_research_data(data):
    """Save scraped research data to MongoDB"""
    try:
        result = research_data.insert_one(data)
        log(f"Saved research data with ID: {result.inserted_id}")
        return result.inserted_id
    except Exception as e:
        log(f"Error saving research data: {str(e)}")
        return None

async def save_experiment(experiment):
    """Save experiment data to MongoDB"""
    try:
        result = experiments.insert_one(experiment)
        log(f"Saved experiment with ID: {result.inserted_id}")
        return result.inserted_id
    except Exception as e:
        log(f"Error saving experiment: {str(e)}")
        return None

async def get_latest_experiments(limit=5):
    """Get latest experiments from MongoDB"""
    try:
        return list(experiments.find().sort('timestamp', -1).limit(limit))
    except Exception as e:
        log(f"Error fetching experiments: {str(e)}")
        return [] 