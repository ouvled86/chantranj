import asyncio

from app.db.seed.run import seed_all

if __name__ == "__main__":
    asyncio.run(seed_all())
