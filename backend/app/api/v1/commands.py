from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ...database import get_db
from ...models.telemetry import PumpCommand
from ...schemas.commands import PumpCommandCreate, PumpCommandAck, PumpCommandResponse
from ..deps import verify_device_api_key, verify_frontend_token

router = APIRouter(prefix="/devices", tags=["commands"])

COMMAND_EXPIRY_SECONDS = 60


@router.post("/{device_id}/commands", response_model=PumpCommandResponse, status_code=status.HTTP_201_CREATED)
def create_command(
    device_id: str,
    payload: PumpCommandCreate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_frontend_token),
):
    """
    Issue a control command to a water pump controller.
    Requires frontend authentication token.
    Enforces duplicate command protection for active pending commands.
    """
    now = datetime.now(timezone.utc)

    # Duplicate command protection: check if an identical pending & unexpired command already exists
    existing_pending = (
        db.query(PumpCommand)
        .filter(
            PumpCommand.device_id == device_id,
            PumpCommand.command_type == payload.command_type,
            PumpCommand.acknowledged.is_(False),
            PumpCommand.expires_at > now,
        )
        .first()
    )

    if existing_pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate command: A pending '{payload.command_type}' command already exists for device '{device_id}'",
        )

    expires_at = now + timedelta(seconds=COMMAND_EXPIRY_SECONDS)

    cmd = PumpCommand(
        device_id=device_id,
        command_type=payload.command_type,
        issued_at=now,
        expires_at=expires_at,
        acknowledged=False,
        issued_by=payload.issued_by or "frontend",
    )
    db.add(cmd)
    db.commit()
    db.refresh(cmd)
    return cmd


@router.get("/{device_id}/commands/pending", response_model=List[PumpCommandResponse])
def get_pending_commands(
    device_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_device_api_key),
):
    """
    Device polling endpoint for unacknowledged, unexpired commands.
    Requires device API key.
    """
    now = datetime.now(timezone.utc)
    pending = (
        db.query(PumpCommand)
        .filter(
            PumpCommand.device_id == device_id,
            PumpCommand.acknowledged.is_(False),
            PumpCommand.expires_at > now,
        )
        .order_by(PumpCommand.issued_at.asc())
        .all()
    )
    return pending


@router.post("/{device_id}/commands/{command_id}/ack", response_model=PumpCommandResponse)
def acknowledge_command(
    device_id: str,
    command_id: str,
    payload: PumpCommandAck,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_device_api_key),
):
    """
    Device acknowledges receipt and execution of command, reporting actual state.
    Requires device API key.
    """
    now = datetime.now(timezone.utc)

    cmd = (
        db.query(PumpCommand)
        .filter(
            PumpCommand.command_id == command_id,
            PumpCommand.device_id == device_id,
        )
        .first()
    )

    if not cmd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Command '{command_id}' not found for device '{device_id}'",
        )

    cmd_expires_at = cmd.expires_at
    if cmd_expires_at.tzinfo is None:
        cmd_expires_at = cmd_expires_at.replace(tzinfo=timezone.utc)

    # Expired command handling
    if cmd_expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Command '{command_id}' has already expired",
        )

    cmd.acknowledged = True
    cmd.acknowledged_at = now
    cmd.device_reported_state = payload.device_reported_state
    db.commit()
    db.refresh(cmd)
    return cmd
