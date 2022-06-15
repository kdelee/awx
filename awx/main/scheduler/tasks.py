# Python
import logging

# Redis
import redis

# Django
from django.conf import settings

# AWX
from awx.main.scheduler import TaskManager
from awx.main.dispatch.publish import task
from awx.main.dispatch import get_local_queuename

logger = logging.getLogger('awx.main.scheduler')


@task(queue=get_local_queuename)
def run_task_manager():
    logger.debug("Running task manager.")
    redis_conn = redis.Redis.from_url(settings.BROKER_URL)
    start_task_limit = redis_conn.get('start_task_limit')
    TaskManager(start_task_limit=start_task_limit).schedule()
