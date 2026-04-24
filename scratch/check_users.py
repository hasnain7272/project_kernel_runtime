import asyncio
from sqlalchemy import select
from src.infrastructure.db.session import get_db_session
from src.infrastructure.db.models.tenant_model import UserModel

async def list_users():
    async for db in get_db_session():
        result = await db.execute(select(UserModel))
        users = result.scalars().all()
        print("Users in DB:")
        for u in users:
            print(f"- {u.email} (Tenant: {u.tenant_id})")
        break

if __name__ == "__main__":
    asyncio.run(list_users())
