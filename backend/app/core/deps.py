from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db


async def get_current_user(db: AsyncSession = Depends(get_db)):
    # TODO: implement JWT verification
    pass
