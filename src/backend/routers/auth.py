"""
Authentication endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from argon2 import PasswordHasher

from ..database import teachers_collection, MONGODB_AVAILABLE

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

def login(username: str, password: str) -> Dict[str, Any]:
    """Login a teacher account"""
    from ..database import _fallback_teachers
    
    # Find the teacher in the database
    teacher = None
    if MONGODB_AVAILABLE:
        teacher = teachers_collection.find_one({"_id": username})
    else:
        teacher = _fallback_teachers.get(username)
    
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Verify password using Argon2
    ph = PasswordHasher()
    try:
        ph.verify(teacher["password"], password)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Return teacher information (excluding password)
    return {
        "username": teacher.get("username", username),
        "display_name": teacher["display_name"],
        "role": teacher["role"]
    }

@router.get("/check-session")
def check_session(username: str) -> Dict[str, Any]:
    """Check if a session is valid by username"""
    from ..database import _fallback_teachers
    
    teacher = None
    if MONGODB_AVAILABLE:
        teacher = teachers_collection.find_one({"_id": username})
    else:
        teacher = _fallback_teachers.get(username)
    
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    return {
        "username": teacher.get("username", username),
        "display_name": teacher["display_name"],
        "role": teacher["role"]
    }