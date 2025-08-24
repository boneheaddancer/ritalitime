# RitaliTime Migration: Streamlit → Dash

## Overview
This document outlines the migration from Streamlit to Dash for the RitaliTime medication timeline simulator.

## Why Migrate?

### Streamlit Limitations
- ❌ **No true persistence** - Session state only, data lost on refresh
- ❌ **Limited JavaScript integration** - Can't implement IndexedDB properly
- ❌ **Performance issues** - Server-side rendering for complex calculations
- ❌ **State management complexity** - Awkward handling of complex state
- ❌ **Mobile experience** - Not optimized for mobile devices

### Dash Benefits
- ✅ **True persistence** - IndexedDB with Dexie.js
- ✅ **Better performance** - Client-side rendering
- ✅ **Flexible state management** - Better component architecture
- ✅ **JavaScript integration** - Full access to browser APIs
- ✅ **Production ready** - Better for long-term applications
- ✅ **Mobile friendly** - Responsive design capabilities

## Migration Status

### ✅ Phase 1: Setup & Dependencies (COMPLETED)
- [x] Install Dash and related packages
- [x] Create basic Dash application structure
- [x] Set up IndexedDB persistence with Dexie.js
- [x] Create configuration system
- [x] Set up project structure

### 🔄 Phase 2: Core Migration (IN PROGRESS)
- [ ] Convert Streamlit UI components to Dash
- [ ] Implement medication input forms
- [ ] Implement stimulant input forms
- [ ] Implement painkiller input forms
- [ ] Migrate timeline visualization
- [ ] Set up Dash routing

### ⏳ Phase 3: Enhanced Features (PLANNED)
- [ ] Advanced state management
- [ ] Performance optimizations
- [ ] Mobile responsiveness
- [ ] Data export/import
- [ ] User preferences
- [ ] Advanced visualizations

## Project Structure

```
ritalitime/
├── dash_app.py              # Main Dash application
├── config.py                # Configuration settings
├── assets/                  # Static assets
│   ├── persistence.js      # IndexedDB operations
│   └── custom-header.html  # Custom HTML template
├── medication_simulator.py  # Existing simulator logic
├── data_schema.py          # Existing data schemas
├── medications.json        # Existing medication data
├── profiles.json           # Existing profile data
├── painkillers.json        # Existing painkiller data
├── requirements.txt        # Updated dependencies
└── MIGRATION_README.md     # This file
```

## Key Changes

### 1. Dependencies
- **Removed**: `streamlit>=1.48.0`
- **Added**: `dash>=3.2.0`, `dash-bootstrap-components>=2.0.4`, `dash-extensions>=2.0.4`

### 2. Data Persistence
- **Before**: Streamlit session state (temporary)
- **After**: IndexedDB with Dexie.js (persistent)

### 3. Architecture
- **Before**: Single Streamlit app with complex state management
- **After**: Modular Dash app with proper component separation

### 4. Performance
- **Before**: Server-side rendering, slower interactions
- **After**: Client-side rendering, faster interactions

## Running the Application

### Development Mode
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Dash app
python dash_app.py
```

### Production Mode
```bash
# Set environment variable
export ENVIRONMENT=production

# Run with production settings
python dash_app.py
```

## Data Migration

### Existing Data
- All existing JSON data files are preserved
- Medication simulator logic is reused
- Data schemas are maintained

### New Persistence
- User data is stored in IndexedDB
- Data survives browser refreshes and restarts
- Export/import functionality for data backup

## Testing

### Manual Testing
1. Start the Dash application
2. Navigate between tabs
3. Add medications/stimulants/painkillers
4. Verify data persistence across refreshes
5. Test timeline visualizations

### Automated Testing
- Unit tests for medication simulator
- Integration tests for data persistence
- UI component tests

## Rollback Plan

If issues arise during migration:
1. Keep the `main` branch with Streamlit version
2. The `dash-migration` branch contains all changes
3. Can easily revert by switching back to `main`
4. All existing functionality is preserved

## Next Steps

1. **Complete Phase 2**: Core migration of UI components
2. **Test thoroughly**: Ensure all functionality works
3. **Performance testing**: Verify improvements
4. **User testing**: Get feedback on new interface
5. **Documentation**: Update user guides
6. **Deployment**: Deploy to production

## Contact

For questions about the migration:
- Check this README first
- Review the git commit history
- Test the application functionality
- Document any issues found

---

**Migration started**: 2025-01-XX  
**Target completion**: Phase 2 - End of January 2025  
**Status**: Phase 1 Complete ✅
