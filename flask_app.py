from flask import Flask, render_template, request, jsonify, make_response
import json
import numpy as np
from datetime import datetime
import os

app = Flask(__name__)

# Load medication data
def load_medications():
    try:
        with open('medications.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

medications_data = load_medications()

# Simple simulator class
class MedicationSimulator:
    def __init__(self):
        self.medications = []
        self.stimulants = []
        self.painkillers = []
        self.dose_id_counter = 0
    
    def get_next_dose_id(self):
        self.dose_id_counter += 1
        return self.dose_id_counter
    
    def add_medication(self, time_hours, name, dosage):
        dose_entry = {
            'id': self.get_next_dose_id(),
            'time_hours': time_hours,
            'name': name,
            'dosage': dosage
        }
        self.medications.append(dose_entry)
        return dose_entry
    
    def add_stimulant(self, time_hours, name, quantity):
        dose_entry = {
            'id': self.get_next_dose_id(),
            'time_hours': time_hours,
            'name': name,
            'quantity': quantity
        }
        self.stimulants.append(dose_entry)
        return dose_entry
    
    def add_painkiller(self, time_hours, name, pills):
        dose_entry = {
            'id': self.get_next_dose_id(),
            'time_hours': time_hours,
            'name': name,
            'pills': pills
        }
        self.painkillers.append(dose_entry)
        return dose_entry
    
    def clear_all_medications(self):
        self.medications = []
    
    def clear_all_stimulants(self):
        self.stimulants = []
    
    def clear_all_painkillers(self):
        self.painkillers = []
    
    def remove_dose(self, dose_id):
        self.medications = [d for d in self.medications if d['id'] != dose_id]
        self.stimulants = [d for d in self.stimulants if d['id'] != dose_id]
        self.painkillers = [d for d in self.painkillers if d['id'] != dose_id]

# Global simulator instance
simulator = MedicationSimulator()

@app.route('/')
def index():
    # Load medications data
    try:
        with open('medications.json', 'r') as f:
            medications_data = json.load(f)
    except FileNotFoundError:
        medications_data = {}
    
    # Load current settings
    try:
        with open('profiles.json', 'r') as f:
            profiles_data = json.load(f)
    except FileNotFoundError:
        profiles_data = {}
    
    response = make_response(render_template('index.html', medications_data=medications_data, profiles_data=profiles_data))
    # Add cache-busting headers to prevent 404 errors from cached requests
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/add_medication', methods=['POST'])
def add_medication():
    data = request.get_json()
    time_str = data.get('time', '08:00')
    name = data.get('name')
    dosage = data.get('dosage', 1)
    
    # Convert time string to hours
    hour, minute = map(int, time_str.split(':'))
    time_hours = hour + minute / 60.0
    
    dose = simulator.add_medication(time_hours, name, dosage)
    
    return jsonify({
        'success': True,
        'dose': dose,
        'message': f'Added {dosage}mg of {name} at {time_str}'
    })

@app.route('/api/add_stimulant', methods=['POST'])
def add_stimulant():
    data = request.get_json()
    time_str = data.get('time', '08:00')
    name = data.get('name')
    quantity = data.get('quantity', 1)
    
    # Convert time string to hours
    hour, minute = map(int, time_str.split(':'))
    time_hours = hour + minute / 60.0
    
    dose = simulator.add_stimulant(time_hours, name, quantity)
    
    return jsonify({
        'success': True,
        'dose': dose,
        'message': f'Added {quantity} of {name} at {time_str}'
    })

@app.route('/api/add_painkiller', methods=['POST'])
def add_painkiller():
    data = request.get_json()
    time_str = data.get('time', '08:00')
    name = data.get('name')
    pills = data.get('pills', 1)
    
    # Convert time string to hours
    hour, minute = map(int, time_str.split(':'))
    time_hours = hour + minute / 60.0
    
    dose = simulator.add_painkiller(time_hours, name, pills)
    
    return jsonify({
        'success': True,
        'dose': dose,
        'message': f'Added {pills} pill(s) of {name} at {time_str}'
    })

@app.route('/api/get_doses', methods=['GET'])
def get_doses():
    return jsonify({
        'medications': simulator.medications,
        'stimulants': simulator.stimulants,
        'painkillers': simulator.painkillers
    })

@app.route('/api/clear_all', methods=['POST'])
def clear_all():
    data = request.get_json()
    dose_type = data.get('type')
    
    if dose_type == 'medications':
        simulator.clear_all_medications()
    elif dose_type == 'stimulants':
        simulator.clear_all_stimulants()
    elif dose_type == 'painkillers':
        simulator.clear_all_painkillers()
    elif dose_type == 'all':
        simulator.clear_all_medications()
        simulator.clear_all_stimulants()
        simulator.clear_all_painkillers()
    
    return jsonify({'success': True, 'message': f'Cleared all {dose_type}'})

@app.route('/api/remove_dose', methods=['POST'])
def remove_dose():
    data = request.get_json()
    dose_id = data.get('id')
    
    simulator.remove_dose(dose_id)
    
    return jsonify({'success': True, 'message': f'Removed dose {dose_id}'})

@app.route('/api/settings', methods=['GET'])
def get_settings():
    try:
        with open('profiles.json', 'r') as f:
            profiles_data = json.load(f)
        # Return the preset_profiles section, or empty dict if not found
        return jsonify(profiles_data.get('preset_profiles', {}))
    except FileNotFoundError:
        return jsonify({})

@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = request.get_json()
    try:
        with open('profiles.json', 'w') as f:
            json.dump(data, f, indent=2)
        return jsonify({'success': True, 'message': 'Settings saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error saving settings: {str(e)}'})



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
