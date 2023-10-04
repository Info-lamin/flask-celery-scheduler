import os
import dotenv

dotenv.load_dotenv(f"{os.path.dirname(os.path.realpath(__file__))}/.env")

MONGO_URI = os.getenv('MONGO_URI')
REDIS_BROKER_URI = os.getenv('REDIS_BROKER_URI')
SQL_URI = os.getenv('SQL_URI')
