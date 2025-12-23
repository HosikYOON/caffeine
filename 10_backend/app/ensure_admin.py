import asyncio
import sys
sys.path.append('/app')

from app.db.database import init_db
from app.db.model.user import User
from app.core.security import get_password_hash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async def ensure_admin():
    engine = await init_db()
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == "admin@example.com"))
        user = result.scalar_one_or_none()
        if not user:
            print("Creating admin user...")
            user = User(
                email="admin@example.com",
                hashed_password=get_password_hash("password123"),
                name="System Admin",
                is_active=True,
                is_superuser=True
            )
            db.add(user)
        else:
            print("Admin user exists. Updating permissions/password...")
            user.is_superuser = True
            user.hashed_password = get_password_hash("password123")
        
        await db.commit()
        print("Admin ready: admin@example.com / password123")

if __name__ == "__main__":
    asyncio.run(ensure_admin())
