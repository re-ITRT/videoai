from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.core.security import create_access_token
from app.auth.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse, ErrorResponse
from app.auth.service import create_user, get_user_by_username, authenticate_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "Username already exists"},
    }
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    # Check if username already exists
    existing_user = await get_user_by_username(db, request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 409, "message": "Username already exists", "detail": f"Username '{request.username}' is already taken"}
        )
    
    try:
        # Create new user
        user = await create_user(
            db=db,
            username=request.username,
            password=request.password,
            nickname=request.nickname
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 409, "message": "Username already exists", "detail": "Registration failed due to duplicate username"}
        )
    
    # Generate access token
    access_token = create_access_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
    }
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login with username and password"""
    user = await authenticate_user(db, request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": "Invalid credentials", "detail": "Incorrect username or password"}
        )
    
    # Generate access token
    access_token = create_access_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    }
)
async def get_current_user_info(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(__import__("app.core.deps", fromlist=["get_current_user"]).get_current_user)
):
    """Get current authenticated user information"""
    return UserResponse.model_validate(current_user)
