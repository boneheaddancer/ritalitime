# 💊 RitaliTime - ADHD Medication & Painkiller Timeline Simulator

A comprehensive Python application for simulating and visualizing ADHD medication, stimulant, and painkiller effects throughout a 24-hour period. This tool helps users understand how different doses, timing, and combinations affect their daily energy levels and pain relief, and identify optimal sleep windows.

## 🌟 Features

### **Dual Application System**
- **ADHD Medications**: Simulate prescription stimulants and medications
- **Painkillers**: Simulate over-the-counter and prescription pain relief

### **Smart Pharmacokinetic Modeling**
- **Realistic Effect Curves**: Rise, plateau, and fall phases based on clinical data
- **Multiple Formulations**: Immediate-release, extended-release, and modified-release
- **Combination Effects**: Hill saturation prevents unlimited additive effects
- **Individual Response**: Customizable sleep thresholds and sensitivity

### **Advanced Visualization**
- **Interactive Timeline**: 24-hour effect curves with hover details
- **Individual Doses**: Separate curves for each medication/stimulant
- **Sleep Windows**: Automatic detection of suitable sleep periods
- **Peak Windows**: Visual indication of optimal effect periods

### **Clinical Intelligence**
- **Evidence-Based Thresholds**: 30%, 60%, and 80% pain relief levels
- **Clinical Recommendations**: Dosing strategy suggestions
- **Combination Therapy**: Recognition of synergistic effects
- **Coverage Analysis**: Assessment of relief gaps and optimization

## 🚀 Getting Started

### **Prerequisites**
- Python 3.8+
- pip package manager

### **Installation**
```bash
# Clone the repository
git clone <repository-url>
cd ritalitime

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **Running the Application**
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run Streamlit app
streamlit run streamlit_app.py
```

## 📊 Application Structure

### **ADHD Medications App**
- **Medication Management**: Add, remove, and configure prescription medications
- **Stimulant Support**: Coffee, energy drinks, and prescription stimulants
- **Custom Parameters**: Override default pharmacokinetic values
- **Profile System**: Save and load medication schedules

### **Painkillers App**
- **Product Database**: Paracetamol, Ibuprofen, Panodil MR
- **Pill Count Support**: Automatic dosage calculation
- **Clinical Thresholds**: Evidence-based pain relief analysis
- **Timing Optimization**: Identify gaps and optimize coverage

## 🔬 Pharmacokinetic Models

### **Effect Curve Phases**
1. **Rise Phase**: Linear increase from 0 to peak effect
2. **Plateau Phase**: Maintain peak effect for specified duration
3. **Fall Phase**: Gradual decline from peak to baseline

### **Formulation Types**
- **Immediate Release**: Rapid onset, shorter duration
- **Extended Release**: Slower onset, longer duration
- **Modified Release**: Sustained release with controlled kinetics

### **Multiple Dose Effects**
- **Modified Release**: Primarily extends duration (30% per pill)
- **Immediate Release**: Increases peak intensity (40% per pill)

## 📁 Project Structure

```
ritalitime/
├── streamlit_app.py          # Main Streamlit application
├── medication_simulator.py   # Core pharmacokinetic engine
├── meds_stimulants.json     # Medication and stimulant database
├── painkillers.json         # Painkiller database
├── profiles.json            # Preset medication profiles
├── requirements.txt         # Python dependencies
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## 🗄️ Data Files

### **meds_stimulants.json**
- **Common Stimulants**: Coffee, Red Bull, Monster
- **Prescription Stimulants**: Ritalin, Adderall, Vyvanse, Concerta
- **Parameters**: Onset, Tmax, peak duration, total duration, wear-off

### **painkillers.json**
- **Products**: Paracetamol 500mg, Ibuprofen 400mg, Panodil 665mg MR
- **Clinical Data**: Onset, Tmax, plateau duration, total duration
- **Intensity Scales**: Peak and average relief levels (1-10 scale)

### **profiles.json**
- **Preset Schedules**: Common medication combinations
- **Clinical Scenarios**: Different dosing strategies
- **Sleep Preferences**: Integrated sleep timing

## 🎯 Clinical Applications

### **ADHD Management**
- **Dose Timing**: Optimize medication coverage throughout the day
- **Combination Therapy**: Coordinate multiple medications
- **Sleep Planning**: Identify optimal sleep windows
- **Side Effect Management**: Monitor effect levels and timing

### **Pain Management**
- **Relief Optimization**: Maximize pain relief coverage
- **Dose Scheduling**: Prevent gaps in pain control
- **Combination Therapy**: Leverage synergistic effects
- **Clinical Monitoring**: Track relief levels and duration

## 🔧 Configuration

### **Sleep Thresholds**
- **Very Sensitive**: 0.01-0.2 (requires very low effect levels)
- **Moderately Sensitive**: 0.2-0.5 (moderate tolerance)
- **Tolerant**: 0.5-1.0 (higher tolerance)
- **Very Tolerant**: 1.0+ (high tolerance to effects)

### **Custom Parameters**
- **Onset Time**: Time from dose to first effect
- **Peak Time**: Time from dose to maximum effect (Tmax)
- **Duration**: Total duration of therapeutic effect
- **Peak Effect**: Maximum effect level

## 📈 Usage Examples

### **Morning ADHD Schedule**
1. **8:00 AM**: Ritalin IR 20mg (rapid onset for morning focus)
2. **12:00 PM**: Coffee 2x (maintain afternoon energy)
3. **4:00 PM**: Concerta 36mg (extended coverage for evening)

### **Pain Management Schedule**
1. **8:00 AM**: Panodil MR 2 pills (1330mg for sustained relief)
2. **2:00 PM**: Ibuprofen 400mg (additional anti-inflammatory)
3. **8:00 PM**: Paracetamol 1000mg (evening pain control)

## 🚨 Important Notes

### **Clinical Disclaimer**
- This tool is for educational and planning purposes only
- Always consult healthcare professionals for medical decisions
- Individual responses to medications vary significantly
- Use clinical judgment when interpreting results

### **Data Limitations**
- Effect curves are based on population averages
- Individual pharmacokinetics may differ substantially
- Drug interactions and comorbidities not modeled
- Environmental and lifestyle factors not considered

## 🤝 Contributing

### **Development Setup**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### **Areas for Improvement**
- Additional medication databases
- Drug interaction modeling
- Individual response prediction
- Mobile application
- Clinical validation studies

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Clinical Research**: Based on published pharmacokinetic data
- **Streamlit**: Web application framework
- **Plotly**: Interactive visualization library
- **Medical Community**: For feedback and clinical insights

## 📞 Support

For questions, issues, or contributions:
- Create an issue on GitHub
- Review the documentation
- Check clinical references
- Consult healthcare professionals

---

**Remember**: This tool is designed to complement, not replace, professional medical advice. Always work with your healthcare team to develop and adjust medication schedules.
