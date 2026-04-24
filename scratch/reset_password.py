import asyncio
import bcrypt
from sqlalchemy import select, update
from src.infrastructure.db.session import get_db_session
from src.infrastructure.db.models.tenant_model import UserModel

async def reset_password():
    email = "hasnain@gmail.com"
    new_password = "password123"
    password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    async for db in get_db_session():
        await db.execute(
            update(UserModel)
            .where(UserModel.email == email)
            .values(password_hash=password_hash)
        )
        await db.commit()
        print(f"Password for {email} has been reset to: {new_password}")
        break

if __name__ == "__main__":
    asyncio.run(reset_password())
