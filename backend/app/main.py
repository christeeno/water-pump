import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .config import settings
from .database import engine, Base, SessionLocal
from .models.telemetry import TelemetryRecord, AlertEvent, DeviceInfo, SystemSettings, PumpCommand
from .api.v1 import api_router as api_v1_router
from .services.websocket_manager import manager
from .services.simulation import WaterSystemSimulator
from .services.fault_detection import evaluate_all_faults
from .services.sensor_validation import UltrasonicValidator

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger("water_management")

# Global simulator instance
simulator = WaterSystemSimulator(device_id="esp32-water-controller-01")
sim_validator = UltrasonicValidator()


def init_db():
    """Create all tables and initialize default records if absent."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        default_device_id = "esp32-water-controller-01"
        dev = db.query(DeviceInfo).filter(DeviceInfo.device_id == default_device_id).first()
        if not dev:
            dev = DeviceInfo(
                device_id=default_device_id,
                firmware_version="1.0.0",
                last_seen=datetime.now(timezone.utc),
                is_connected=True,
                controller_state="IDLE",
                sensor_health_json=json.dumps({"ultrasonic": "OK", "flow": "OK", "pressure": "OK", "current": "OK"}),
            )
            db.add(dev)

        sys_set = db.query(SystemSettings).filter(SystemSettings.device_id == default_device_id).first()
        if not sys_set:
            sys_set = SystemSettings(
                device_id=default_device_id,
                tank_height_cm=100.0,
                empty_distance_cm=95.0,
                full_distance_cm=15.0,
                low_level_threshold=20.0,
                high_level_threshold=90.0,
                min_flow_lpm=0.5,
                max_flow_lpm=30.0,
                min_pressure_bar=0.5,
                max_pressure_bar=3.5,
                max_current_a=5.0,
                startup_grace_period_s=10,
                sensor_timeout_s=5,
                invalid_reading_threshold=5,
                data_retention_days=30,
            )
            db.add(sys_set)

        db.commit()
    except Exception as e:
        logger.error(f"Error during default initialization: {e}")
        db.rollback()
    finally:
        db.close()


async def run_simulation_loop():
    """Background task running periodic simulation steps when SIMULATION_MODE=true."""
    logger.info("Starting simulation loop background task...")
    while True:
        try:
            step_data = simulator.run_step(delta_seconds=1.0)
            db = SessionLocal()
            try:
                device_id = step_data["device_id"]
                now = datetime.now(timezone.utc)

                # Check for pending commands to simulate execution
                pending_cmds = (
                    db.query(PumpCommand)
                    .filter(
                        PumpCommand.device_id == device_id,
                        PumpCommand.acknowledged.is_(False),
                        PumpCommand.expires_at > now,
                    )
                    .all()
                )
                for cmd in pending_cmds:
                    simulator.handle_command(cmd.command_type)
                    cmd.acknowledged = True
                    cmd.acknowledged_at = now
                    cmd.device_reported_state = simulator.state
                    logger.info(f"Simulator executed command {cmd.command_type} for device {device_id}")

                # Sensor validation
                v_res = sim_validator.validate(step_data["tank_distance_cm"], now)

                # Fault detection
                sys_set = db.query(SystemSettings).filter(SystemSettings.device_id == device_id).first()
                alerts = evaluate_all_faults(step_data, sys_set)

                # Save alerts
                new_alerts_list = []
                for a in alerts:
                    alert_record = AlertEvent(
                        event_id=a["event_id"],
                        timestamp=a["timestamp"],
                        severity=a["severity"],
                        fault_category=a["fault_category"],
                        description=a["description"],
                        sensor_evidence_json=a["sensor_evidence_json"],
                        pump_state=a["pump_state"],
                        recommended_action=a["recommended_action"],
                        acknowledged=False,
                        device_id=device_id,
                    )
                    db.add(alert_record)
                    new_alerts_list.append(a)

                # Save telemetry record
                t_record = TelemetryRecord(
                    device_id=device_id,
                    timestamp=now,
                    tank_distance_cm=step_data["tank_distance_cm"],
                    tank_level_percent=step_data["tank_level_percent"],
                    flow_rate_lpm=step_data["flow_rate_lpm"],
                    pressure_bar=step_data["pressure_bar"],
                    pump_current_a=step_data["pump_current_a"],
                    pump_on=step_data["pump_on"],
                    mode=step_data["mode"],
                    controller_state=step_data["controller_state"],
                    sensor_status_json=json.dumps(step_data["sensor_status"]),
                    is_simulated=True,
                    raw_tank_distance_cm=step_data["raw_tank_distance_cm"],
                    tank_level_valid=v_res.is_valid,
                )
                db.add(t_record)

                # Update device
                dev = db.query(DeviceInfo).filter(DeviceInfo.device_id == device_id).first()
                if dev:
                    dev.last_seen = now
                    dev.last_telemetry_at = now
                    dev.is_connected = True
                    dev.controller_state = step_data["controller_state"]
                    dev.sensor_health_json = json.dumps(step_data["sensor_status"])

                db.commit()
            except Exception as e:
                logger.error(f"Error in simulation step DB commit: {e}")
                db.rollback()
            finally:
                db.close()

            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            logger.info("Simulation loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in simulation loop: {e}")
            await asyncio.sleep(1.0)


async def run_dashboard_push_loop():
    """Periodic dashboard broadcast loop (pushes latest telemetry + active alerts every 2 seconds)."""
    while True:
        try:
            await asyncio.sleep(2.0)
            if not manager.active_connections:
                continue

            db = SessionLocal()
            try:
                latest = db.query(TelemetryRecord).order_by(desc(TelemetryRecord.timestamp)).first()
                active_alerts = (
                    db.query(AlertEvent)
                    .filter(AlertEvent.acknowledged.is_(False))
                    .order_by(desc(AlertEvent.timestamp))
                    .limit(10)
                    .all()
                )

                if latest:
                    payload = {
                        "type": "dashboard_update",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "telemetry": {
                            "id": latest.id,
                            "device_id": latest.device_id,
                            "timestamp": latest.timestamp.isoformat(),
                            "tank_distance_cm": latest.tank_distance_cm,
                            "tank_level_percent": latest.tank_level_percent,
                            "flow_rate_lpm": latest.flow_rate_lpm,
                            "pressure_bar": latest.pressure_bar,
                            "pump_current_a": latest.pump_current_a,
                            "pump_on": latest.pump_on,
                            "mode": latest.mode,
                            "controller_state": latest.controller_state,
                            "is_simulated": latest.is_simulated,
                            "sensor_status": json.loads(latest.sensor_status_json) if latest.sensor_status_json else {},
                        },
                        "active_alerts_count": len(active_alerts),
                        "active_alerts": [
                            {
                                "event_id": a.event_id,
                                "timestamp": a.timestamp.isoformat(),
                                "severity": a.severity,
                                "fault_category": a.fault_category,
                                "description": a.description,
                                "recommended_action": a.recommended_action,
                            }
                            for a in active_alerts
                        ],
                    }
                    await manager.broadcast(payload)
            except Exception as e:
                logger.error(f"Error in dashboard broadcast loop: {e}")
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Unexpected error in dashboard push loop: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    init_db()

    background_tasks = []
    if settings.SIMULATION_MODE:
        sim_task = asyncio.create_task(run_simulation_loop())
        background_tasks.append(sim_task)

    push_task = asyncio.create_task(run_dashboard_push_loop())
    background_tasks.append(push_task)

    yield

    # Shutdown
    logger.info("Shutting down background tasks...")
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)
    logger.info("Application shutdown complete.")


app = FastAPI(
    title="Smart Water Management & Pump Health Monitoring System",
    description="Backend API for real-time telemetry, automated fault detection, pump control, and monitoring.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Routers
app.include_router(api_v1_router, prefix="/api/v1")


@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint pushing real-time telemetry and alert updates to dashboards."""
    await manager.connect(websocket)
    db = SessionLocal()
    try:
        # Send initial state on connection
        latest = db.query(TelemetryRecord).order_by(desc(TelemetryRecord.timestamp)).first()
        active_alerts = (
            db.query(AlertEvent)
            .filter(AlertEvent.acknowledged.is_(False))
            .order_by(desc(AlertEvent.timestamp))
            .limit(10)
            .all()
        )
        if latest:
            initial_payload = {
                "type": "initial_state",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "telemetry": {
                    "id": latest.id,
                    "device_id": latest.device_id,
                    "timestamp": latest.timestamp.isoformat(),
                    "tank_distance_cm": latest.tank_distance_cm,
                    "tank_level_percent": latest.tank_level_percent,
                    "flow_rate_lpm": latest.flow_rate_lpm,
                    "pressure_bar": latest.pressure_bar,
                    "pump_current_a": latest.pump_current_a,
                    "pump_on": latest.pump_on,
                    "mode": latest.mode,
                    "controller_state": latest.controller_state,
                    "is_simulated": latest.is_simulated,
                    "sensor_status": json.loads(latest.sensor_status_json) if latest.sensor_status_json else {},
                },
                "active_alerts_count": len(active_alerts),
                "active_alerts": [
                    {
                        "event_id": a.event_id,
                        "timestamp": a.timestamp.isoformat(),
                        "severity": a.severity,
                        "fault_category": a.fault_category,
                        "description": a.description,
                        "recommended_action": a.recommended_action,
                    }
                    for a in active_alerts
                ],
            }
            await manager.send_personal_message(initial_payload, websocket)
    except Exception as e:
        logger.error(f"Error sending initial state to WebSocket: {e}")
    finally:
        db.close()

    try:
        while True:
            # Keep connection open, receive ping/message from client
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
