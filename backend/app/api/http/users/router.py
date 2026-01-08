from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import uuid4
import datetime

router = APIRouter(prefix="/users", tags=["users"])

# In-memory storage for demo (replace with database in production)
users_db = {
    "admin-1": {
        "id": "admin-1",
        "email": "admin@hellosales.com",
        "name": "Admin User",
        "role": "admin",
        "status": "active",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "password_hash": "hashed_admin123"
    },
    "user-1": {
        "id": "user-1",
        "email": "sales@hellosales.com",
        "name": "Sales User",
        "role": "sales",
        "status": "active",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "password_hash": "hashed_sales123"
    }
}

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = "sales"

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    status: str
    created_at: str

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int

@router.get("", response_model=UserListResponse)
async def list_users(skip: int = 0, limit: int = 10):
    """List all users (admin only)"""
    users = list(users_db.values())
    return {
        "users": [UserResponse(**u) for u in users[skip:skip + limit]],
        "total": len(users)
    }

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate):
    """Create a new user (admin only)"""
    # Check if email exists
    for user in users_db.values():
        if user["email"] == user_data.email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    if user_data.role not in ["admin", "manager", "sales", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    user_id = f"user-{uuid4().hex[:8]}"
    new_user = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "role": user_data.role,
        "status": "active",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "password_hash": f"hashed_{user_data.password}"
    }
    users_db[user_id] = new_user
    return UserResponse(**new_user)

@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Delete a user (admin only)"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    del users_db[user_id]
    return {"message": "User deleted"}

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get a specific user"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**users_db[user_id])
