import asyncio
from arq import create_pool
from arq.connections import RedisSettings
from bot.core.config import settings
from bot.core.logger import setup_logging, logger
from bot.ml_modules.vision import process_ocr

setup_logging()

async def startup(ctx):
    logger.info("Worker started")
    # Initialize resources here (e.g. database connection pool for worker)

async def shutdown(ctx):
    logger.info("Worker shutting down")

async def test_task(ctx, word: str):
    logger.info(f"Processing test task with word: {word}")
    return f"Processed {word}"

# Worker Settings
class WorkerSettings:
    functions = [test_task, process_ocr]
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT
    )
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10

if __name__ == '__main__':
    # This block is for testing the worker configuration locally if needed,
    # but arq usually runs via command line: arq bot.worker.WorkerSettings
    pass
