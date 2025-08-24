#!/usr/bin/env python3
"""
Test script to verify ADHD medication curve generation
"""

from medication_simulator import MedicationSimulator
import numpy as np

def test_adhd_med():
    """Test ADHD medication curve generation"""
    print("Testing ADHD medication curve generation...")
    
    # Create simulator
    sim = MedicationSimulator()
    
    # Add an ADHD medication
    print("Adding Ritalin IR medication...")
    sim.add_medication("08:00", 20.0, medication_name="ritalin_IR")
    
    print(f"Medications added: {len(sim.medications)}")
    print(f"Medication data: {sim.medications[0]}")
    
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
            print("✅ ADHD medication curve generated successfully!")
        else:
            print("❌ ADHD medication curve generated but has no effect")
    else:
        print("❌ No timeline generated")

if __name__ == "__main__":
    test_adhd_med()
