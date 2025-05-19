from celery import Celery
from discord_agents.env import REDIS_URL

celery_app = Celery("discord_agents", broker=REDIS_URL, backend=REDIS_URL)
