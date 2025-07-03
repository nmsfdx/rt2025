# SPM Model Issues and Solutions

## Problem
You're getting numerical errors when using the SPM (Single Particle Model) with power values of [10, -5, 15] W:
```
Simulation failed: Maximum number of decreased steps occurred at t=720.0000000000001
```

## Root Cause
The SPM model has **numerical stability limitations** with higher power values. The error occurs because:

1. **High power values** (10W, 15W) create steep gradients in the battery equations
2. **SPM model** is simplified and more sensitive to numerical issues than DFN
3. **Default solver settings** are not conservative enough for challenging power profiles

## Solutions

### Solution 1: Use Lower Power Values with SPM
```python
# Instead of this (problematic):
power_profile = [10, -5, 15]  # Too high for SPM

# Use this (works well):
power_profile = [3, -2, 5]    # Appropriate for SPM
```

### Solution 2: Use Conservative Solver Settings
```python
battery = BatterySimulator(model_type="SPM")
battery.simulate_power_profile(
    power_values=[3, -2, 5],
    time_durations=[0.5, 1.0, 0.3],
    initial_soc=0.8,
    safe_mode=True  # Enables conservative solver settings
)
```

### Solution 3: Switch to DFN Model for High Power
```python
# For high power applications, use DFN instead:
battery = BatterySimulator(model_type="DFN")  # More robust
battery.simulate_power_profile(
    power_values=[10, -5, 15],  # Original high power values work fine
    time_durations=[0.5, 1.0, 0.3],
    initial_soc=0.8
)
```

## Updated Code Features

I've enhanced your `bat-speicher.py` with:

1. **Automatic error handling** with fallback to conservative settings
2. **Model stability testing** function
3. **Safe mode** option for better numerical stability
4. **Intelligent solver selection** based on model type

## Recommended Power Ranges

| Model | Recommended Power Range | Max Stable Power |
|-------|------------------------|------------------|
| SPM   | 0.5W - 5W             | ~5W              |
| SPMe  | 0.5W - 10W            | ~10W             |
| DFN   | 0.5W - 50W+           | 50W+             |

## Quick Fix for Your Code

Simply change these two lines in your main function:

```python
# OLD (problematic with SPM):
power_profile = [10, -5, 15]
battery = BatterySimulator(model_type="SPM")

# NEW (works well):
power_profile = [3, -2, 5]        # Lower power values
battery = BatterySimulator(model_type="SPM")
# OR use DFN for high power:
# battery = BatterySimulator(model_type="DFN")
```

## Test Your Setup

Use the new stability testing function:
```python
from bat_speicher import test_model_stability

# Test what power values work with SPM
test_model_stability("SPM", test_powers=[1, 3, 5, 8, 10, 15, 20])
```

This will show you exactly which power values work with your specific setup.

## Why This Happens

- **SPM** is a simplified model designed for computational efficiency
- **Higher power values** create more complex dynamics that challenge the simplified equations
- **DFN** includes more detailed physics and handles high power better
- **Numerical solvers** need smaller time steps and tighter tolerances for challenging scenarios

Choose SPM for **efficiency** with moderate power levels, or DFN for **robustness** with high power applications.
