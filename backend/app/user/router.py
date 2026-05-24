from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, get_current_admin_user
from app.auth.schemas import UserResponse, ErrorResponse
from app.user.schemas import (
    UserUpdateRequest, PasswordChangeRequest, UserAdminUpdateRequest,
    UserListResponse, UserDetailResponse
)
from app.user.service import (
    get_user_by_id, update_user_profile, change_user_password,
    get_all_users, admin_update_user, delete_user
)
from app.auth.models import User

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    }
)
async def get_my_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Update failed"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    }
)
async def update_my_profile(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's nickname and/or email"""
    try:
        user = await update_user_profile(db, current_user.id, request)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": "Update failed", "detail": str(e)}
        )


@router.put(
    "/me/password",
    response_model=UserResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Password change failed"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    }
)
async def change_my_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change current user's password"""
    try:
        user = await change_user_password(db, current_user.id, request.old_password, request.new_password)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": "Password change failed", "detail": str(e)}
        )


@router.get(
    "/",
    response_model=list[UserListResponse],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    }
)
async def get_users_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Admin: Get list of all users"""
    users = await get_all_users(db, skip=skip, limit=limit)
    return [UserListResponse.model_validate(u) for u in users]


@router.patch(
    "/{user_id}",
    response_model=UserDetailResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Update failed"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "User not found"},
    }
)
async def admin_update_user_by_id(
    user_id: int,
    request: UserAdminUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Admin: Update a user's profile"""
    try:
        user = await admin_update_user(db, user_id, request)
        return UserDetailResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "User not found", "detail": str(e)}
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "User not found"},
    }
)
async def admin_delete_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Admin: Delete a user"""
    try:
        await delete_user(db, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "User not found", "detail": str(e)}
        )
