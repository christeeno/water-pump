import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class WaterSystemSimulator:
    """
    Deterministic simulator for water system demo mode.
    Simulates:
      - Tank draining (pump OFF), tank filling (pump ON)
      - Periodic faults:
          * dry-run after 5 minutes (300s)
          * pressure spike after 10 minutes (600s)
      - State machine: IDLE -> FILLING -> VERIFY -> FAULT
      - Returns real telemetry payload shape with is_simulated=True
    """

    def __init__(
        self,
        device_id: str = "esp32-water-controller-01",
        tank_height_cm: float = 100.0,
        empty_distance_cm: float = 95.0,
        full_distance_cm: float = 15.0,
        initial_level_percent: float = 45.0,
        low_threshold: float = 20.0,
        high_threshold: float = 90.0,
    ):
        self.device_id = device_id
        self.tank_height_cm = tank_height_cm
        self.empty_distance_cm = empty_distance_cm
        self.full_distance_cm = full_distance_cm
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold

        self.current_level: float = initial_level_percent
        self.mode: str = "AUTO"  # AUTO or MANUAL
        self.state: str = "IDLE"  # IDLE, FILLING, VERIFY, FAULT
        self.pump_on: bool = False
        self.elapsed_seconds: int = 0
        self.verify_timer: int = 0

        self.drain_rate_percent_per_sec: float = 0.2
        self.fill_rate_percent_per_sec: float = 0.8

        self.fault_dry_run_interval: int = 300  # 5 minutes
        self.fault_pressure_spike_interval: int = 600  # 10 minutes
        self.fault_duration_sec: int = 15

    def handle_command(self, command_type: str) -> bool:
        if command_type == "PUMP_ON":
            self.pump_on = True
            self.state = "FILLING"
            return True
        elif command_type == "PUMP_OFF":
            self.pump_on = False
            self.state = "IDLE"
            return True
        elif command_type == "SET_MODE_AUTO":
            self.mode = "AUTO"
            return True
        elif command_type == "SET_MODE_MANUAL":
            self.mode = "MANUAL"
            return True
        return False

    def run_step(self, delta_seconds: float = 1.0) -> Dict[str, Any]:
        """Advance simulation by delta_seconds (default 1s) and return telemetry record."""
        self.elapsed_seconds += int(delta_seconds)

        # Check periodic simulated fault conditions
        is_dry_run_period = (
            self.pump_on
            and (self.elapsed_seconds >= self.fault_dry_run_interval)
            and (self.elapsed_seconds % self.fault_dry_run_interval < self.fault_duration_sec)
        )
        is_pressure_spike_period = (
            self.pump_on
            and (self.elapsed_seconds >= self.fault_pressure_spike_interval)
            and (self.elapsed_seconds % self.fault_pressure_spike_interval < self.fault_duration_sec)
        )

        # State machine logic
        if is_dry_run_period or is_pressure_spike_period:
            self.state = "FAULT"
        elif self.mode == "AUTO":
            if self.state == "IDLE":
                if self.current_level <= self.low_threshold:
                    self.state = "FILLING"
                    self.pump_on = True
            elif self.state == "FILLING":
                if self.current_level >= self.high_threshold:
                    self.state = "VERIFY"
                    self.verify_timer = 3
            elif self.state == "VERIFY":
                self.verify_timer -= int(delta_seconds)
                if self.verify_timer <= 0:
                    self.state = "IDLE"
                    self.pump_on = False
            elif self.state == "FAULT":
                # Recover from transient simulated fault
                if not is_dry_run_period and not is_pressure_spike_period:
                    self.state = "FILLING" if self.pump_on else "IDLE"

        # Update physical simulation values
        flow_rate_lpm: float = 0.0
        pressure_bar: float = 0.2
        pump_current_a: float = 0.0
        sensor_status = {
            "ultrasonic": "OK",
            "flow": "OK",
            "pressure": "OK",
            "current": "OK",
        }

        if self.pump_on:
            self.current_level = min(100.0, self.current_level + (self.fill_rate_percent_per_sec * delta_seconds))
            osc = math.sin(self.elapsed_seconds * 0.1)

            if is_dry_run_period:
                # Pump running, but water supply failure
                flow_rate_lpm = 0.1
                pressure_bar = round(0.4 + (osc * 0.05), 2)
                pump_current_a = round(0.9 + (osc * 0.05), 2)
            elif is_pressure_spike_period:
                # Discharge blocked
                flow_rate_lpm = 0.3
                pressure_bar = round(4.2 + (osc * 0.1), 2)
                pump_current_a = round(2.5 + (osc * 0.1), 2)
            else:
                # Normal pumping
                flow_rate_lpm = round(8.4 + (osc * 0.3), 2)
                pressure_bar = round(1.6 + (osc * 0.1), 2)
                pump_current_a = round(1.2 + (osc * 0.05), 2)
        else:
            # Gravity consumption drain
            self.current_level = max(0.0, self.current_level - (self.drain_rate_percent_per_sec * delta_seconds))
            flow_rate_lpm = 0.0
            pressure_bar = round(max(0.1, (self.current_level / 100.0) * 0.5), 2)
            pump_current_a = 0.0

        # Calculate ultrasonic distance
        usable_height = self.empty_distance_cm - self.full_distance_cm
        water_height = (self.current_level / 100.0) * usable_height
        tank_distance_cm = round(self.empty_distance_cm - water_height, 2)

        return {
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tank_distance_cm": tank_distance_cm,
            "tank_level_percent": round(self.current_level, 2),
            "flow_rate_lpm": flow_rate_lpm,
            "pressure_bar": pressure_bar,
            "pump_current_a": pump_current_a,
            "pump_on": self.pump_on,
            "mode": self.mode,
            "controller_state": self.state,
            "sensor_status": sensor_status,
            "is_simulated": True,
            "raw_tank_distance_cm": tank_distance_cm,
            "tank_level_valid": True,
        }
