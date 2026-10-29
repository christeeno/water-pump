# Sensor Calibration Guide

## Smart Water Management & Pump Health Monitoring System

---

## Overview

Accurate sensor calibration is essential for reliable pump control.  
This guide covers the theory behind each sensor, step-by-step calibration procedures, acceptable accuracy ranges, and fixes for common problems.

> **Before you start:** Flash the firmware with debug print lines where indicated,
> open the serial monitor at **115200 baud**, and have your calibration tools ready.

---

## 1. HC-SR04 Ultrasonic Distance Sensor

### Theory

The HC-SR04 uses time-of-flight acoustics.  A 40 kHz burst is emitted, reflects
off the water surface, and the echo pulse duration is measured:

```
distance (cm) = pulse_duration (µs) × speed_of_sound / 2
             = pulse_duration (µs) × 0.01715
```

Speed of sound varies with temperature (~0.6 m/s per °C).  At 20°C it is 343 m/s.
For tank-level monitoring, the effect of ±5°C ambient variation is small (< 1% error)
and can be ignored unless extreme precision is required.

**Effective range:** 2 cm – 400 cm (HC-SR04 datasheet).  
**Firmware timeout:** 30 ms (`PULSIN_TIMEOUT_US = 30000`), corresponding to ~5 m.

### Calibration Procedure

#### Step 1 – Physical setup
- Mount the HC-SR04 vertically above the water surface, centred over the tank.
- Ensure nothing obstructs the acoustic beam (no pipes, ladders, floats) within a 15° cone below the sensor.

#### Step 2 – Determine EMPTY distance
1. Completely empty the tank (or measure to a known low reference mark).
2. With firmware running, monitor the serial output:
   ```
   [SENSOR] Dist=29.8 cm  Level=-1.0% ...
   ```
3. Allow 10+ readings and note the stable median value.
4. Measure the physical distance from the sensor face to the water surface with a tape measure.  
   They should match within ±1 cm; if not, re-check wiring and sensor mounting.
5. Set in firmware:
   ```cpp
   const float EMPTY_DIST_CM = 29.8f;  // your measured value
   ```

#### Step 3 – Determine FULL distance
1. Fill the tank to the desired 100% mark.
2. Record the stable `Dist=` value from serial.
3. Set in firmware:
   ```cpp
   const float FULL_DIST_CM = 5.2f;  // your measured value
   ```

#### Step 4 – Verify intermediate levels
Fill the tank to a known intermediate level (e.g., exactly half the depth).
Serial output should show `Level≈50.0%`.  Accept ±3%.

#### Common Problems & Fixes

| Symptom | Cause | Fix |
|---|---|---|
| All readings = -1 | TRIG/ECHO swapped, or no 5 V supply | Check wiring; verify 5 V on VCC |
| Reading wildly erratic | Sensor too close to water (< 2 cm) | Raise sensor; increase `MIN_VALID_DIST` |
| Reading jumps between two values | Interference between TRIG pulse and echo from tank walls | Shield with foam padding around sensor housing |
| Level reads 120% or negative | `EMPTY_DIST_CM` and `FULL_DIST_CM` swapped | Swap the values |
| Reading drifts slowly over minutes | Temperature compensation needed | Implement Celsius correction: `dist × (331.3 + 0.606×T_C) / 343.0` |

#### Acceptable Accuracy
| Specification | Value |
|---|---|
| Distance accuracy | ±1 cm |
| Level accuracy (after calibration) | ±2–3% |
| Minimum stable distance | 2 cm |
| Maximum reliable range | 400 cm (HC-SR04 datasheet) |

---

## 2. YF-S201 Hall-Effect Flow Sensor

### Theory

A small turbine wheel spins inside the flow path.  A Hall-effect sensor detects
each magnetic pole as the wheel rotates, generating one pulse per blade pass.

```
flow_rate (L/min) = pulse_count / calibration_factor / measurement_time_min
```

The YF-S201 datasheet specifies the relationship as:

```
F (Hz) = 7.5 × Q (L/min)
```

where `F` = pulse frequency.  This gives **450 pulses per litre** at steady flow —
but this varies with backpressure, pipe fittings, and fluid viscosity.  Always
calibrate empirically.

### Calibration Procedure

#### Step 1 – Collect raw pulses
Temporarily add to the firmware (inside `loop()`, before `calculateFlowRate()`):
```cpp
static uint32_t dbgPulses = 0;
noInterrupts();
dbgPulses = g_flowPulseCount;
interrupts();
Serial.printf("[CAL] Flow pulses: %lu\n", dbgPulses);
```

#### Step 2 – Bucket test
1. Reset the pulse counter by restarting the ESP32 with zero flow.
2. Place a **1-litre graduated jug** at the sensor outlet.
3. Start flow.  When exactly 1 litre has passed through, stop flow.
4. Note the pulse count from serial.  Repeat 3 times; average the results.

**Example:** 447, 451, 452 → average = 450 pulses/L

#### Step 3 – Update firmware
```cpp
const float FLOW_PULSES_PER_LITRE = 450.0f;  // your average
```

#### Step 4 – Verify
Flow 2 L while timing with a stopwatch.  `flow_rate_lpm` should match:  
`LPM = 2 L / (stopwatch_seconds / 60)` ± 5%.

#### Common Problems & Fixes
| Symptom | Cause | Fix |
|---|---|---|
| Always 0 LPM | No pulses received | Check signal wire, try `INPUT_PULLDOWN` instead of `INPUT_PULLUP` |
| LPM too high | Wrong pulses/L value | Re-calibrate with bucket test |
| LPM too low | Flow rate below 1 L/min | YF-S201 minimum reliable rate is ~1 L/min; consider a low-flow sensor |
| Erratic readings at low flow | Turbine stalling | Ensure minimum 1 bar pipe pressure |

#### Acceptable Accuracy
| Specification | Value |
|---|---|
| Rated flow range | 1–30 L/min |
| Accuracy (within range) | ±3–5% |
| Operating pressure | ≤ 1.75 MPa |

---

## 3. Analog Pressure Sensor (0–5 bar)

### Theory

A resistive pressure sensor converts pipe pressure to a proportional voltage:

```
V_out = V_supply × (pressure / P_max) × span + V_offset
```

For a typical 0.5–4.5 V output sensor with 5 V supply:
- 0 bar → 0.5 V
- 5 bar → 4.5 V

The ESP32 ADC (0–3.3 V, 12-bit) reads 0–4095 counts.  The firmware maps:

```
pressure (bar) = (ADC_raw - zero_offset) × bar_per_lsb
```

**Important:** Many analog pressure sensors output 0.5 V (not 0 V) at zero pressure.  
This requires a non-zero `PRESSURE_ZERO_OFFSET`.

### Calibration Procedure

#### Step 1 – Zero offset (atmospheric)
1. Leave the pressure port open to atmosphere (unpressurised pipe or no connection).
2. Add a temporary debug print in `readPressure()`:
   ```cpp
   Serial.printf("[CAL] Pressure raw ADC: %.1f\n", raw);
   ```
3. Note the ADC value.  This is your `PRESSURE_ZERO_OFFSET`.
4. Update:
   ```cpp
   const float PRESSURE_ZERO_OFFSET = 620.0f;  // example: 0.5V → 620 counts
   ```

#### Step 2 – Span calibration
1. Apply a **known reference pressure** (e.g., from a calibrated regulator or a closed, measured water column).
2. Note the ADC reading.
3. Calculate:
   ```
   bar_per_lsb = known_pressure / (ADC_at_pressure - PRESSURE_ZERO_OFFSET)
   ```
4. Update:
   ```cpp
   const float PRESSURE_BAR_PER_LSB = 0.00118f;  // example calculation
   ```

#### Common Problems & Fixes
| Symptom | Cause | Fix |
|---|---|---|
| Reads negative pressure | Zero offset too high | Recalibrate zero offset |
| Reads 3–4× expected | Wrong sensor full-scale (e.g., 0–10 bar sensor used with 0–5 bar constant) | Match constants to sensor datasheet |
| Noisy readings | ADC interference from relay or motor switching | Add 100 nF ceramic cap from signal to GND; separate power rails |

#### Acceptable Accuracy
| Specification | Value |
|---|---|
| Typical accuracy (calibrated) | ±0.5% FS (±0.025 bar at 5 bar FS) |
| ESP32 ADC contribution | ±1–2% (due to non-linearity; use `analogSetAttenuation(ADC_11db)`) |
| Combined system accuracy | ±2% full scale |

---

## 4. ACS712-20A Current Sensor

### Theory

The ACS712 is a Hall-effect current sensor with galvanic isolation.  It outputs
a voltage proportional to the current through its sense conductor (IP+ → IP−):

```
V_out = V_offset + Sensitivity × I
```

For the ACS712-20A:
- `V_offset` = VCC/2 = 2.5 V (with 5 V supply) → ADC ≈ 3102 (at 3.3 V range)  
- Or with 3.3 V powered module: `V_offset` ≈ 1.65 V → ADC ≈ 2048  
- `Sensitivity` = 100 mV/A → in ADC counts: `0.1 V/A ÷ (3.3/4095) ≈ 0.1241 A/LSB`

The firmware constant `CURRENT_SCALE = 0.066` is correct for the **5A** module;
for the **20A** module use `≈ 0.124`.  Verify with the module's silkscreen.

### Calibration Procedure

#### Step 1 – Zero offset (no current)
1. Open-circuit the pump – no current flowing through ACS712 IP terminals.
2. Add temporary debug:
   ```cpp
   Serial.printf("[CAL] Current raw ADC: %d\n", (int)(sum / SAMPLES));
   ```
3. Note the ADC value.  Update:
   ```cpp
   const int CURRENT_MIDPOINT = 2055;  // your zero-current ADC reading
   ```

#### Step 2 – Scale factor
1. Connect a **known load** (e.g., a 60 W incandescent lamp at 240 V = 0.25 A,
   or a resistive heater of known rating).
2. Measure actual current with a clamp ammeter.
3. Calculate:
   ```
   CURRENT_SCALE = clamp_reading / (ADC_with_load - CURRENT_MIDPOINT)
   ```
4. Update:
   ```cpp
   const float CURRENT_SCALE = 0.124f;  // refined value
   ```

#### Step 3 – Verify
Run the pump; compare `pump_current_a` with clamp meter reading.  Accept ±10%.

#### Common Problems & Fixes
| Symptom | Cause | Fix |
|---|---|---|
| Current reads ~0.5 A with no load | `CURRENT_MIDPOINT` too low | Increase `CURRENT_MIDPOINT` |
| Current oscillates rapidly | High-frequency switching noise from VFD or motor | Add 10 µF + 100 nF cap across ACS712 VIOUT and GND |
| Negative current reading | Pump power connections through ACS712 reversed | Swap IP+ and IP− wire connections |
| Reads 2× actual | Using 5A scale for 20A module | Change `CURRENT_SCALE` from 0.066 to ~0.124 |

#### Acceptable Accuracy
| Specification | Value |
|---|---|
| ACS712-20A total error | ±1.5% FS (±0.3 A at 20 A) at 25°C |
| ESP32 ADC + noise contribution | ±2–3% at typical currents |
| Combined system accuracy | ±5–10% for pump monitoring (sufficient for fault detection) |

---

## 5. Complete Post-Calibration Verification

### Test Sequence

After updating all constants and reflashing:

1. **Empty tank test:**
   - Empty tank; verify `Level=0.0%` ± 2%
   - Pump should NOT be running (level is 0%, but pump starts when < `LOW_LEVEL_THRESHOLD = 20%`)
   - Fill slightly above 20%; pump should START and FSM → FILLING

2. **Filling test:**
   - Let pump run; verify `Level` increases smoothly
   - `Flow=` should show a non-zero LPM value (verify against your reference)
   - `Pressure=` should show system pressure

3. **Full tank test:**
   - Fill to 90%+; pump should STOP automatically, FSM → IDLE

4. **Fault test (dry run simulation):**
   - In MANUAL mode, close the inlet valve (simulate dry running)
   - After `GRACE_PERIOD_MS` (10 s), FSM should enter `FAULT` with message "possible dry run"
   - Pump should switch OFF

5. **Overload test (simulate):**
   - Temporarily lower `MAX_CURRENT_A` to just above idle current
   - Start pump; FSM should detect overload and enter FAULT

### Serial Monitor Expected Output (normal operation)
```
[BOOT] Smart Water Controller v1.0.0
[BOOT] Device ID: esp32-water-controller-01
[WIFI] Connecting to SSID: MyNetwork
....
[WIFI] Connected. IP: 192.168.1.105
[BOOT] Initialisation complete. Entering main loop.

[SENSOR] Dist=28.2 cm  Level=7.7%  Flow=0.00 LPM  Pressure=0.00 bar  Current=0.05 A  Pump=OFF
[FSM] IDLE → VERIFY  (level=7.7% < threshold=20.0%)
[PUMP] ON – reason: Level below LOW threshold
[SENSOR] Dist=27.8 cm  Level=8.1%  Flow=7.42 LPM  Pressure=1.58 bar  Current=1.14 A  Pump=ON
[FSM] VERIFY → FILLING  (flow=7.42 LPM OK)
[TELEMETRY] Sent OK  HTTP=202
```
