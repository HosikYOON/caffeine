import asyncio
import sys
sys.path.append('/app')
from app.db.database import init_db
from app.db.model.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async def make_superuser():
    engine = await init_db()
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Check for admin@example.com
        result = await db.execute(select(User).where(User.email == "admin@example.com"))
        user = result.scalar_one_or_none()
        if user:
            print(f"Found user: {user.email} (ID: {user.id})")
            user.is_superuser = True
            await db.commit()
            print("Successfully promoted to SUPERUSER.")
        else:
            print("User admin@example.com not found.")

if __name__ == "__main__":
    asyncio.run(make_superuser())
