# Home Battery Storage Simulation Guide

## Overview

The updated `bat-speicher.py` code has been enhanced to simulate realistic home battery storage systems with capacities of 5-20 kWh and power levels of 1-10 kW, typical for single-family homes.

## Key Changes for Home Battery Simulation

### 1. Enhanced BatterySimulator Class

```python
# Create a home battery system
battery = BatterySimulator(
    model_type="SPM",       # Efficient for home scale
    capacity_kwh=13.5,      # Tesla Powerwall-like capacity
    nominal_voltage=400.0   # Typical home battery voltage
)
```

**New Parameters:**
- `capacity_kwh`: Battery capacity in kilowatt-hours (5-20 kWh typical)
- `nominal_voltage`: System voltage (typically 400V for home systems)

### 2. Power Input in kW Scale

The simulation now accepts power values in **kilowatts** instead of watts:

```python
# Old way (watts):
power_values = [3000, -2000, 5000]  # Watts

# New way (kilowatts):
power_values_kw = [3.0, -2.0, 5.0]  # kW - much more intuitive for home use
```

### 3. Home Battery Specifications

Get realistic specs for your battery:

```python
specs = battery.get_home_battery_specs()
print(f"Capacity: {specs['capacity_kwh']} kWh")
print(f"Max Power: {specs['max_recommended_power_kw']:.1f} kW")
```

## Typical Home Battery Applications

### 1. **Solar Energy Storage**
```python
# Morning: Use stored solar from yesterday
# Day: Solar charges battery
# Evening: Use stored solar energy

daily_pattern = [
    (4.0, 2.0),   # 4kW discharge for 2 hours (morning)
    (-3.0, 7.0),  # 3kW charge for 7 hours (solar excess)
    (5.0, 6.0),   # 5kW discharge for 6 hours (evening)
    (1.0, 9.0),   # 1kW discharge for 9 hours (night)
]
```

### 2. **Peak Shaving**
```python
# Charge during cheap off-peak hours
# Discharge during expensive peak hours

peak_shaving = [
    (-7.0, 8.0),   # Charge at night (off-peak rates)
    (8.0, 5.0),    # Discharge during peak hours
]
```

### 3. **Backup Power**
```python
# Provide emergency power during outages
backup_power = [
    (2.0, 12.0),   # 2kW for 12 hours = 24kWh backup
]
```

## Realistic Power and Capacity Ranges

| Home Size | Battery Capacity | Max Power | Typical Use |
|-----------|------------------|-----------|-------------|
| Small (1-2 people) | 5-8 kWh | 3-5 kW | Essential loads, overnight |
| Medium (3-4 people) | 10-15 kWh | 5-7 kW | Most appliances, 1-2 days |
| Large (5+ people) | 15-20 kWh | 7-10 kW | Whole home, 2-3 days |

## Example Usage Patterns

### Daily Solar Home
```python
# Simulate a full day with solar and load profiles
results = battery.simulate_daily_home_usage(
    solar_profile_kw=[0,0,0,0,0,0,1,3,6,8,8,7,6,4,2,0,0,0,0,0,0,0,0,0],
    load_profile_kw=[2,1,1,1,1,2,4,3,2,2,2,2,2,2,3,4,6,5,4,3,3,2,2,2],
    initial_soc=0.5
)
```

### Tesla Powerwall Example
```python
battery = BatterySimulator(
    model_type="DFN",
    capacity_kwh=13.5,      # Powerwall 2 capacity
    nominal_voltage=400.0
)

# Typical daily usage
battery.simulate_power_profile(
    power_values_kw=[4.0, -3.0, 5.0, 1.0],  # kW
    time_durations=[2.0, 7.0, 6.0, 9.0],    # hours
    initial_soc=0.9
)
```

## Model Selection for Home Batteries

| Model | Best For | Power Range | Speed |
|-------|----------|-------------|-------|
| **SPM** | Basic simulations, efficiency studies | 1-5 kW | Fast |
| **DFN** | Detailed analysis, high power | 1-50 kW | Slower |
| **SPMe** | Balanced accuracy/speed | 1-15 kW | Medium |

**Recommendation**: Use **DFN** for home battery simulations as it handles the kW power levels more robustly.

## Energy Economics

### Cost Savings Calculation
```python
# Example: Peak shaving savings
energy_shifted_kwh = 10  # kWh shifted from peak to off-peak
rate_difference = 0.25   # $/kWh difference between peak and off-peak
daily_savings = energy_shifted_kwh * rate_difference
annual_savings = daily_savings * 365

print(f"Annual savings: ${annual_savings:.0f}")
```

### Battery ROI Factors
- **Electricity rate spread** (peak vs off-peak)
- **Solar self-consumption** increase
- **Backup power value** (avoiding outage costs)
- **Battery lifespan** (typically 10-15 years)

## Common Home Battery Configurations

### 1. **Small Backup System** (5 kWh)
- **Purpose**: Essential loads during outages
- **Runtime**: 6-12 hours at reduced power
- **Cost**: Lower upfront investment

### 2. **Solar + Storage** (10-15 kWh)
- **Purpose**: Maximize solar self-consumption
- **Runtime**: 1-2 days of normal usage
- **Benefits**: Energy independence, peak shaving

### 3. **Whole Home Backup** (15-20 kWh)
- **Purpose**: Complete home backup power
- **Runtime**: 2-3 days with normal usage
- **Benefits**: Extended outage protection

## Best Practices

1. **Size for daily usage**: Battery should handle 1-2 days of essential loads
2. **Consider solar integration**: Size battery to store excess solar production
3. **Plan for peak shaving**: Utilize time-of-use electricity rates
4. **Include safety margins**: Don't regularly discharge below 10% SOC
5. **Account for efficiency**: ~90-95% round-trip efficiency typical

## Quick Start Example

```python
# Create a typical 10kWh home battery
battery = BatterySimulator(
    model_type="DFN",
    capacity_kwh=10.0,
    nominal_voltage=400.0
)

# Simulate typical daily pattern
daily_usage = [
    (3.0, 2.0),    # Morning peak: 3kW for 2 hours
    (-4.0, 6.0),   # Solar charging: 4kW for 6 hours  
    (5.0, 4.0),    # Evening peak: 5kW for 4 hours
    (1.5, 12.0),   # Night load: 1.5kW for 12 hours
]

powers = [p[0] for p in daily_usage]
durations = [p[1] for p in daily_usage]

battery.simulate_power_profile(
    power_values_kw=powers,
    time_durations=durations,
    initial_soc=0.2  # Start day at 20%
)

# Get results
state = battery.get_battery_state()
print(f"End of day SOC: {state['soc']*100:.1f}%")
print(f"Energy cycled: {abs(state['energy_consumed_Wh'])/1000:.1f} kWh")
```

This updated simulation framework provides realistic modeling of home battery storage systems with proper scaling for residential applications.
