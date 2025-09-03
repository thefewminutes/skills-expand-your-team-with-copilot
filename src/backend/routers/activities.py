"""
Endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from typing import Dict, Any, Optional, List

from ..database import activities_collection, teachers_collection, MONGODB_AVAILABLE

router = APIRouter(
    prefix="/activities",
    tags=["activities"]
)

@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any])
def get_activities(
    day: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get all activities with their details, with optional filtering by day and time
    
    - day: Filter activities occurring on this day (e.g., 'Monday', 'Tuesday')
    - start_time: Filter activities starting at or after this time (24-hour format, e.g., '14:30')
    - end_time: Filter activities ending at or before this time (24-hour format, e.g., '17:00')
    """
    from ..database import _fallback_activities
    
    activities = {}
    
    if MONGODB_AVAILABLE:
        # Build the query based on provided filters
        query = {}
        
        if day:
            query["schedule_details.days"] = {"$in": [day]}
        
        if start_time:
            query["schedule_details.start_time"] = {"$gte": start_time}
        
        if end_time:
            query["schedule_details.end_time"] = {"$lte": end_time}
        
        # Query the database
        for activity in activities_collection.find(query):
            name = activity.pop('_id')
            activities[name] = activity
    else:
        # Use fallback storage with filtering
        for name, details in _fallback_activities.items():
            # Apply day filter
            if day and "schedule_details" in details:
                if day not in details["schedule_details"]["days"]:
                    continue
            
            # Apply time filters
            if start_time and "schedule_details" in details:
                if details["schedule_details"]["start_time"] < start_time:
                    continue
                    
            if end_time and "schedule_details" in details:
                if details["schedule_details"]["end_time"] > end_time:
                    continue
            
            activities[name] = details
    
    return activities

@router.get("/days", response_model=List[str])
def get_available_days() -> List[str]:
    """Get a list of all days that have activities scheduled"""
    from ..database import _fallback_activities
    
    days = []
    
    if MONGODB_AVAILABLE:
        # Aggregate to get unique days across all activities
        pipeline = [
            {"$unwind": "$schedule_details.days"},
            {"$group": {"_id": "$schedule_details.days"}},
            {"$sort": {"_id": 1}}  # Sort days alphabetically
        ]
        
        for day_doc in activities_collection.aggregate(pipeline):
            days.append(day_doc["_id"])
    else:
        # Use fallback storage
        unique_days = set()
        for details in _fallback_activities.values():
            if "schedule_details" in details:
                unique_days.update(details["schedule_details"]["days"])
        days = sorted(list(unique_days))
    
    return days

@router.post("/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, teacher_username: Optional[str] = Query(None)):
    """Sign up a student for an activity - requires teacher authentication"""
    from ..database import _fallback_activities, _fallback_teachers
    
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(status_code=401, detail="Authentication required for this action")
    
    teacher = None
    if MONGODB_AVAILABLE:
        teacher = teachers_collection.find_one({"_id": teacher_username})
    else:
        teacher = _fallback_teachers.get(teacher_username)
    
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")
    
    # Get the activity
    activity = None
    if MONGODB_AVAILABLE:
        activity = activities_collection.find_one({"_id": activity_name})
    else:
        activity = _fallback_activities.get(activity_name)
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400, detail="Already signed up for this activity")

    # Add student to participants
    if MONGODB_AVAILABLE:
        result = activities_collection.update_one(
            {"_id": activity_name},
            {"$push": {"participants": email}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update activity")
    else:
        _fallback_activities[activity_name]["participants"].append(email)
    
    return {"message": f"Signed up {email} for {activity_name}"}

@router.post("/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, teacher_username: Optional[str] = Query(None)):
    """Remove a student from an activity - requires teacher authentication"""
    from ..database import _fallback_activities, _fallback_teachers
    
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(status_code=401, detail="Authentication required for this action")
    
    teacher = None
    if MONGODB_AVAILABLE:
        teacher = teachers_collection.find_one({"_id": teacher_username})
    else:
        teacher = _fallback_teachers.get(teacher_username)
    
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")
    
    # Get the activity
    activity = None
    if MONGODB_AVAILABLE:
        activity = activities_collection.find_one({"_id": activity_name})
    else:
        activity = _fallback_activities.get(activity_name)
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400, detail="Not registered for this activity")

    # Remove student from participants
    if MONGODB_AVAILABLE:
        result = activities_collection.update_one(
            {"_id": activity_name},
            {"$pull": {"participants": email}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update activity")
    else:
        _fallback_activities[activity_name]["participants"].remove(email)
    
    return {"message": f"Unregistered {email} from {activity_name}"}