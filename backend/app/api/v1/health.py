from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from ...database import get_db
from ...config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health(db: Session = Depends(get_db)):
    """Health check endpoint checking application and database status."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "database": db_status},
        )

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "simulation_mode": settings.SIMULATION_MODE,
    }
