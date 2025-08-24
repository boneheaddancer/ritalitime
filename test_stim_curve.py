#!/usr/bin/env python3
"""
Test script to verify stim curve generation
"""

from medication_simulator import MedicationSimulator
import numpy as np

def test_stim_curve():
    """Test stim curve generation"""
    print("Testing stim curve generation...")
    
    # Create simulator
    sim = MedicationSimulator()
    
    # Add a stimulant
    print("Adding coffee stimulant...")
    sim.add_stimulant("09:00", "coffee", "caffeine", 1.0)
    
    print(f"Stimulants added: {len(sim.stimulants)}")
    print(f"Stimulant data: {sim.stimulants[0]}")
    
    # Generate timeline
    print("Generating timeline...")
    time_points, combined_effect = sim.generate_daily_timeline()
    
    print(f"Time points: {len(time_points)}")
    print(f"Combined effect: {len(combined_effect)}")
    
    if len(combined_effect) > 0:
        print(f"Effect range: {np.min(combined_effect):.6f} to {np.max(combined_effect):.6f}")
        print(f"Non-zero effects: {np.count_nonzero(combined_effect)}")
        
        # Check if we have any actual effect
        if np.max(combined_effect) > 0:
            print("✅ Stim curve generated successfully!")
        else:
            print("❌ Stim curve generated but has no effect")
    else:
        print("❌ No timeline generated")

if __name__ == "__main__":
    test_stim_curve()
