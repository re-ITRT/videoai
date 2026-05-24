from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login():
    # TODO: implement
    pass


@router.post("/register")
async def register():
    # TODO: implement
    pass
