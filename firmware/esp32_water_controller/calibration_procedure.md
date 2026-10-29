# Sensor Calibration Procedure
## ESP32 Smart Water Controller – Firmware Calibration Guide

> **Prerequisites:** Arduino IDE or PlatformIO with the ESP32 board package,
> USB cable, serial monitor at **115200 baud**.

---

## 1. Ultrasonic Sensor (HC-SR04)

### Purpose
Map the raw distance readings (cm) to tank-empty and tank-full reference points
so `calculateTankLevel()` returns accurate percentages.

### Equipment
- Tape measure or ruler
- Empty tank + full tank of known water height

### Procedure

1. **Wire the HC-SR04** per the pin table (TRIG=5, ECHO=18).  
2. Open the serial monitor at 115200 baud and flash the firmware.  
3. **Empty-distance (`EMPTY_DIST_CM`):**
   - Physically empty the tank (or simulate with a flat surface).  
   - Observe the `Dist=` value printed every 500 ms.  
   - Record the stable median value after ≥ 10 readings.  
   - Set `const float EMPTY_DIST_CM = <your_value>;`.
4. **Full-distance (`FULL_DIST_CM`):**
   - Fill the tank to the desired 100% mark.  
   - Record the stable median `Dist=` value.  
   - Set `const float FULL_DIST_CM = <your_value>;`.
5. **Verify:** With tank at a known intermediate level (e.g., 50%), the
   serial output should show `Level≈50.0%`.  Accept ±2% tolerance.
6. **Range guards:** Confirm `MIN_VALID_DIST` is below the closest possible
   valid reading and `MAX_VALID_DIST` is above the farthest possible reading.

### Troubleshooting
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| All readings = -1 | Echo pin not wired, or TRIG/ECHO swapped | Check wiring |
| Level stuck at 0% or 100% | `FULL_DIST_CM` / `EMPTY_DIST_CM` swapped | Swap the values |
| Erratic readings | Sensor too close to tank wall; interference from ripples | Reposition sensor centrally above water |
| Reading valid but noisy | Increase `ULTRASONIC_SAMPLES` from 5 to 7 | Edit constant and reflash |

---

## 2. Pressure Sensor (Analog, 0–5 bar)

### Purpose
Convert ADC counts to bar using zero-offset correction and span calibration.

### Equipment
- Known reference pressure source (e.g., a closed pipe at atmospheric = 0 bar)
- Optional: calibrated pressure gauge for span verification

### Procedure

1. **Zero offset (0 bar = atmospheric):**
   - Disconnect the pipe from the pressure port so the sensor is open to atmosphere.  
   - Observe the `pressure_bar` field in the serial output.  
   - Note the raw ADC count by temporarily adding this line to `readPressure()`:
     ```cpp
     Serial.printf("[CAL] Pressure raw ADC: %.0f\n", raw);
     ```
   - The ADC value at 0 bar = your `PRESSURE_ZERO_OFFSET`.  
   - Update `const float PRESSURE_ZERO_OFFSET = <observed_value>;`.

2. **Span calibration:**
   - Apply a known pressure (e.g., 2.0 bar from a regulated source).  
   - Calculate: `bar_per_lsb = known_pressure / (raw_adc - zero_offset)`.  
   - Update `const float PRESSURE_BAR_PER_LSB = <calculated>;`.

3. **Verify:** Apply 1.0 bar; serial should print `Pressure=1.00 bar` ± 0.05 bar.

### Acceptable Accuracy
- ±2% full-scale (±0.1 bar over 0–5 bar range) for most resistive sensors.

---

## 3. Current Sensor (ACS712-20A)

### Purpose
Map the ADC mid-point (0 A) and scale factor to accurate ampere readings.

### Equipment
- Clamp ammeter for ground truth
- Known load (e.g., a resistive heater rated at a specific wattage)

### Procedure

1. **Zero offset (0 A):**
   - Switch off the pump and all loads on the monitored circuit.  
   - The circuit must be open (no current flowing).  
   - Add a temporary debug print:
     ```cpp
     Serial.printf("[CAL] Current raw ADC: %.0f\n", raw);
     ```
   - The ADC value at 0 A = `CURRENT_MIDPOINT`.  
   - Update `const int CURRENT_MIDPOINT = <observed>;` (typically 2048 ± 50).

2. **Scale factor:**
   - ACS712-20A datasheet sensitivity: **100 mV/A**.  
   - With 3.3 V reference and 12-bit ADC:  
     `scale = 0.1 V/A ÷ (3.3 V / 4095 counts) ≈ 0.1241 A/LSB`  
   - In practice, update `CURRENT_SCALE` by comparing to a clamp meter:  
     `CURRENT_SCALE = clamp_meter_reading / (raw_adc - CURRENT_MIDPOINT)`
   - Default value `0.066` is for a **5 A** ACS712 module variant; for
     the **20 A** module, use `≈ 0.1241`.  Adjust accordingly.

3. **Verify:** With a 1 A load, serial should show `Current≈1.00 A` ± 0.1 A.

### Notes
- The ESP32 ADC is **non-linear** near 0 V and 3.3 V; prefer loads above 0.5 A.
- Shield the ACS712 signal wire from high-frequency switching noise.

---

## 4. Flow Sensor (YF-S201)

### Purpose
Determine the correct **pulses-per-litre** ratio for your specific installation
(pipe diameter, fluid viscosity, and flow rate all affect it).

### Equipment
- Graduated container (minimum 1 L) and a stopwatch
- Multimeter (to count pulses, or use serial monitor)

### Procedure

1. **Connect the flow sensor** (FLOW_SENSOR_PIN=19, INPUT_PULLUP).
2. Add a temporary debug print in `calculateFlowRate()` to display raw pulse count.
3. **Collect reference data:**
   - Flow exactly **1 litre** of water through the sensor into a measuring jug.  
   - Note the pulse count displayed on the serial monitor.  
   - Repeat 3× and average.
4. **Update the constant:**
   ```cpp
   const float FLOW_PULSES_PER_LITRE = <average_pulse_count>;
   ```
   YF-S201 datasheet default: ~450 pulses/L at 1–30 L/min.

5. **Verify:** Flow 2 L; `flow_rate_lpm` should match a stopwatch measurement ± 5%.

### Acceptable Accuracy
- ±3–5% for YF-S201 across its rated range (1–30 L/min).

---

## 5. Verifying All Calibrations via Serial Monitor

After all constants are updated and firmware is reflashed, the serial monitor
output should look similar to:

```
[SENSOR] Dist=12.4 cm  Level=61.3%  Flow=8.35 LPM  Pressure=1.62 bar  Current=1.18 A  Pump=ON
[FSM]    FILLING  level=61.3%  flow=8.35 LPM
[TELEMETRY] Sent OK  HTTP=202
```

### Checklist

- [ ] `Dist=` matches physical measurement with tape ± 1 cm
- [ ] `Level=` reads 0% when empty, 100% when full
- [ ] `Flow=` matches bucket+stopwatch ± 5%
- [ ] `Pressure=` reads ~0 bar with no pipe pressure; matches gauge under load
- [ ] `Current=` reads ~0 A with pump off; matches clamp meter with pump on
- [ ] `[FSM] FAULT` is NOT triggered during normal operation at calibrated values
