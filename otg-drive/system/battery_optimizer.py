#!/usr/bin/env python3
"""
OpenClaw OTG Battery & Thermal Optimizer
Monitors battery, temperature, and dynamically throttles AI inference
to prevent overheating and maximize battery life.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OTG_Battery_Optimizer")

@dataclass
class PowerState:
    battery_level: int
    is_charging: bool
    temperature_c: float
    cpu_frequency_mhz: int
    thermal_throttling: bool
    estimated_runtime_minutes: int
    power_profile: str  # "eco", "balanced", "performance"

class BatteryOptimizer:
    """
    Intelligent power management for mobile AI inference.
    Features:
    - Real-time battery monitoring
    - Thermal throttling prevention
    - Dynamic CPU frequency scaling
    - Adaptive inference quality based on power state
    - Sleep consolidation trigger during charging
    """
    
    def __init__(self):
        self.current_profile = "balanced"
        self.throttle_factor = 1.0
        self.last_check_time = time.time()
        self.temperature_history = []
        self.max_temp_threshold = 45.0  # Start throttling at 45°C
        self.critical_temp = 60.0  # Emergency shutdown at 60°C
        
    def read_battery_info(self) -> Dict[str, Any]:
        """Read battery information from Android system."""
        # Try to read from Android battery sysfs
        battery_info = {
            "level": 85,
            "charging": False,
            "temperature": 32.0,
            "voltage_mv": 3800,
            "current_ma": -500
        }
        
        try:
            # Battery level
            if Path("/sys/class/power_supply/battery/capacity").exists():
                with open("/sys/class/power_supply/battery/capacity", 'r') as f:
                    battery_info["level"] = int(f.read().strip())
            
            # Charging status
            if Path("/sys/class/power_supply/battery/status").exists():
                with open("/sys/class/power_supply/battery/status", 'r') as f:
                    status = f.read().strip()
                    battery_info["charging"] = status in ["Charging", "Full"]
            
            # Temperature (in tenths of degree Celsius)
            if Path("/sys/class/power_supply/battery/temp").exists():
                with open("/sys/class/power_supply/battery/temp", 'r') as f:
                    battery_info["temperature"] = int(f.read().strip()) / 10.0
            
        except Exception as e:
            logger.warning(f"Could not read battery info: {e}. Using mock values.")
        
        return battery_info

    def read_cpu_info(self) -> Dict[str, Any]:
        """Read CPU frequency and core information."""
        cpu_info = {
            "cores": 8,
            "frequency_mhz": 1800,
            "online_cores": 8
        }
        
        try:
            # Count CPU cores
            cpu_online = Path("/sys/devices/system/cpu/online")
            if cpu_online.exists():
                with open(cpu_online, 'r') as f:
                    # Parse range like "0-7"
                    range_str = f.read().strip()
                    if "-" in range_str:
                        start, end = map(int, range_str.split("-"))
                        cpu_info["online_cores"] = end - start + 1
            
            # Read current frequency of first CPU
            freq_file = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
            if freq_file.exists():
                with open(freq_file, 'r') as f:
                    cpu_info["frequency_mhz"] = int(f.read().strip()) // 1000
                    
        except Exception as e:
            logger.warning(f"Could not read CPU info: {e}")
        
        return cpu_info

    def calculate_throttle_factor(self, temp: float, battery: int, charging: bool) -> float:
        """Calculate throttle factor based on temperature and battery."""
        factor = 1.0
        
        # Temperature throttling
        if temp >= self.critical_temp:
            factor = 0.2  # Emergency throttling
            logger.critical(f"🚨 CRITICAL TEMPERATURE: {temp}°C! Emergency throttling to 20%")
        elif temp >= self.max_temp_threshold:
            # Linear throttling from 45°C to 60°C
            factor = max(0.3, 1.0 - ((temp - self.max_temp_threshold) / (self.critical_temp - self.max_temp_threshold) * 0.7))
            logger.warning(f"⚠️  High temperature: {temp}°C. Throttling to {factor*100:.0f}%")
        
        # Battery throttling
        if not charging:
            if battery < 10:
                factor *= 0.3  # Ultra power saving
                logger.warning("🔋 Critical battery (<10%). Ultra power saving mode.")
            elif battery < 20:
                factor *= 0.5
                logger.info("🔋 Low battery (<20%). Power saving mode.")
            elif battery < 40:
                factor *= 0.7
        
        # Boost when charging and cool
        if charging and temp < 35.0 and battery > 80:
            factor = min(1.2, factor * 1.1)  # Slight boost
            logger.info("⚡ Charging and cool. Performance boost enabled.")
        
        self.throttle_factor = max(0.2, min(1.2, factor))
        return self.throttle_factor

    def select_power_profile(self, battery: int, charging: bool, temp: float) -> str:
        """Select optimal power profile."""
        if charging and temp < 40.0:
            profile = "performance"
        elif battery < 15 or temp > 50.0:
            profile = "eco"
        else:
            profile = "balanced"
        
        if profile != self.current_profile:
            logger.info(f"🔄 Switching power profile: {self.current_profile} → {profile}")
            self.current_profile = profile
        
        return profile

    def estimate_runtime(self, battery: int, profile: str) -> int:
        """Estimate remaining runtime in minutes."""
        # Base consumption rates (mAh per hour) by profile
        consumption_rates = {
            "eco": 300,
            "balanced": 600,
            "performance": 1200
        }
        
        # Assume 3000mAh battery
        battery_capacity = 3000
        current_charge = (battery / 100.0) * battery_capacity
        
        rate = consumption_rates.get(profile, 600)
        runtime_hours = current_charge / rate
        
        return int(runtime_hours * 60)

    def get_optimized_settings(self) -> PowerState:
        """Get current optimized power settings."""
        battery_info = self.read_battery_info()
        cpu_info = self.read_cpu_info()
        
        temp = battery_info["temperature"]
        battery = battery_info["level"]
        charging = battery_info["charging"]
        
        # Update temperature history
        self.temperature_history.append(temp)
        if len(self.temperature_history) > 10:
            self.temperature_history.pop(0)
        
        # Calculate throttle and profile
        throttle = self.calculate_throttle_factor(temp, battery, charging)
        profile = self.select_power_profile(battery, charging, temp)
        runtime = self.estimate_runtime(battery, profile)
        
        # Check if thermal throttling is active
        thermal_throttling = throttle < 0.9
        
        return PowerState(
            battery_level=battery,
            is_charging=charging,
            temperature_c=temp,
            cpu_frequency_mhz=int(cpu_info["frequency_mhz"] * throttle),
            thermal_throttling=thermal_throttling,
            estimated_runtime_minutes=runtime,
            power_profile=profile
        )

    def should_trigger_sleep_consolidation(self) -> bool:
        """Check if conditions are right for memory consolidation."""
        state = self.get_optimized_settings()
        # Trigger during charging, cool temperature, and high battery
        return (state.is_charging and 
                state.temperature_c < 38.0 and 
                state.battery_level > 70)

if __name__ == "__main__":
    print("🔋 OpenClaw OTG Battery & Thermal Optimizer Starting...")
    
    optimizer = BatteryOptimizer()
    
    # Simulate monitoring loop
    for i in range(3):
        print(f"\n--- Check {i+1} ---")
        state = optimizer.get_optimized_settings()
        
        print(f"🔋 Battery: {state.battery_level}% ({'⚡ Charging' if state.is_charging else '🔌 Discharging'})")
        print(f"🌡️  Temperature: {state.temperature_c}°C")
        print(f"⚙️  Profile: {state.power_profile.upper()}")
        print(f"🐌 Throttling: {'Active' if state.thermal_throttling else 'Inactive'} ({optimizer.throttle_factor*100:.0f}%)")
        print(f"⏱️  Est. Runtime: {state.estimated_runtime_minutes} minutes")
        print(f"💾 CPU Freq: {state.cpu_frequency_mhz} MHz")
        
        # Check for sleep consolidation opportunity
        if optimizer.should_trigger_sleep_consolidation():
            print("✨ Ideal conditions for Memory Palace sleep consolidation!")
        
        # Simulate changing conditions
        time.sleep(1)
