# Battery Simulator with PyBaMM

This program provides a flexible battery simulation tool using PyBaMM that can handle varying power input/output profiles to track battery state of charge and energy storage.

## Features

- **Variable Power Input**: Simulate battery with positive (discharge) or negative (charge) power values
- **Flexible Time Profiles**: Define custom time durations for each power level
- **Battery State Tracking**: Monitor voltage, current, state of charge (SOC), and energy
- **Multiple Battery Models**: Support for DFN, SPM, and SPMe models
- **Visualization**: Plot battery behavior over time

## Usage

### Basic Usage

```python
from bat_speicher import BatterySimulator

# Create simulator
battery = BatterySimulator()

# Define power profile (Watts) and durations (hours)
power_values = [10, -5, 15, 0, -8, 20]  # + = discharge, - = charge, 0 = rest
time_durations = [0.5, 1.0, 0.3, 0.2, 0.8, 0.4]  # hours

# Run simulation
battery.simulate_power_profile(
    power_values=power_values,
    time_durations=time_durations,
    initial_soc=0.8  # Start at 80% charge
)

# Get results
state = battery.get_battery_state()
print(f"Final SOC: {state['soc']*100:.1f}%")
print(f"Energy consumed: {state['energy_consumed_Wh']:.2f} Wh")
```

### Quick Function

```python
from bat_speicher import simulate_custom_power

# Quick simulation
battery = simulate_custom_power(
    power_values=[5, -3, 8],
    durations=[0.5, 1.0, 0.3],
    initial_soc=0.9
)

state = battery.get_battery_state()
```

## Power Convention

- **Positive values**: Battery discharge (power output)
- **Negative values**: Battery charge (power input)
- **Zero values**: Rest period (no power flow)

## Battery State Information

The `get_battery_state()` method returns:
- `soc`: State of charge (0-1)
- `voltage_V`: Terminal voltage in Volts
- `current_A`: Current in Amperes
- `energy_consumed_Wh`: Total energy consumed/provided in Watt-hours
- `time_h`: Total simulation time in hours

## Examples

### Example 1: Discharge Profile
```python
# Simulate high discharge followed by rest
battery = simulate_custom_power(
    power_values=[20, 0],  # 20W discharge, then rest
    durations=[0.5, 0.1],  # 30 minutes discharge, 6 minutes rest
    initial_soc=1.0        # Start fully charged
)
```

### Example 2: Charging Profile
```python
# Simulate charging from low battery
battery = simulate_custom_power(
    power_values=[-15, -5, 0],  # Fast charge, slow charge, rest
    durations=[0.3, 0.5, 0.1],
    initial_soc=0.2  # Start at 20%
)
```

### Example 3: Mixed Profile
```python
# Simulate realistic usage pattern
battery = simulate_custom_power(
    power_values=[10, -8, 15, 0, -5, 25],  # Mixed usage
    durations=[0.4, 0.6, 0.2, 0.1, 0.8, 0.3],
    initial_soc=0.7  # Start at 70%
)
```

## Running the Program

1. Make sure you have PyBaMM installed:
   ```
   pip install pybamm
   ```

2. Run the main program:
   ```
   python bat-speicher.py
   ```

3. Run examples:
   ```
   python example_usage.py
   ```

## Model Types

Choose from different battery models:
- `"DFN"`: Doyle-Fuller-Newman (most detailed, default)
- `"SPM"`: Single Particle Model (faster)
- `"SPMe"`: Single Particle Model with electrolyte (balanced)

```python
battery = BatterySimulator(model_type="SPM")  # Faster simulation
```

## Notes

- Simulation automatically stops if voltage limits are reached (3.0V min, 4.2V max)
- Power values are in Watts, time durations in hours
- Initial SOC should be between 0 (empty) and 1 (full)
- Higher power values may cause voltage limits to be reached faster

## Requirements

- Python 3.7+
- PyBaMM
- NumPy
- Matplotlib (for plotting)
- SciPy (dependency of PyBaMM)
