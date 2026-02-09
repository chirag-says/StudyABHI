import asyncio
import sys
import os

# Add current directory to path so imports work
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.user import User

async def list_users():
    print("Checking registered users...")
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User.email))
            users = [r[0] for r in result.all()]
            print(f"Found {len(users)} users:")
            for email in users:
                print(f" - {email}")
    except Exception as e:
        print(f"Error checking DB: {e}")

if __name__ == "__main__":
    asyncio.run(list_users())
