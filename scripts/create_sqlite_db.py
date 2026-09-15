import asyncio
from db.models import Base
from db.session import engine

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database schema created in SQLite!")

if __name__ == "__main__":
    asyncio.run(init_db())
