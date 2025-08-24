/**
 * RitaliTime - Client-side Data Persistence
 * Uses Dexie.js for IndexedDB operations
 * 
 * This provides true persistence that survives:
 * - Page refreshes
 * - Browser restarts
 * - Browser updates
 * - Tab closures
 */

// Import Dexie from CDN (will be loaded in HTML)
// Dexie is loaded via CDN in the Dash app

// Database schema and operations
class RitaliTimeDB {
    constructor() {
        this.db = null;
        this.init();
    }

    async init() {
        try {
            // Initialize Dexie database
            this.db = new Dexie('RitaliTimeDB');
            
            // Define database schema
            this.db.version(1).stores({
                medications: '++id, time, medication_name, dosage, onset_time_min, peak_time_min, duration_min',
                stimulants: '++id, time, stimulant_name, quantity, component_name, onset_time_min, peak_time_min, duration_min',
                painkillers: '++id, time_hours, name, pills, dosage, onset_min, peak_time_min, duration_min',
                app_settings: 'key, value',
                user_preferences: 'key, value'
            });

            console.log('RitaliTimeDB initialized successfully');
            
            // Auto-load data when database is ready
            this.autoLoadData();
        } catch (error) {
            console.error('Failed to initialize database:', error);
        }
    }

    // Auto-load data from IndexedDB
    async autoLoadData() {
        try {
            const data = await this.exportData();
            if (data && Object.keys(data).length > 0) {
                // Store in localStorage for Dash to access
                localStorage.setItem('ritalitime_data', JSON.stringify(data));
                console.log('Data auto-loaded from IndexedDB');
                
                // Dispatch custom event to notify Dash
                window.dispatchEvent(new CustomEvent('ritalitime_data_loaded', { 
                    detail: data 
                }));
            }
        } catch (error) {
            console.error('Auto-load failed:', error);
        }
    }

    // Medication operations
    async saveMedication(medication) {
        try {
            if (!this.db) await this.init();
            const id = await this.db.medications.add(medication);
            console.log('Medication saved with ID:', id);
            return id;
        } catch (error) {
            console.error('Failed to save medication:', error);
            throw error;
        }
    }

    async getMedications() {
        try {
            if (!this.db) await this.init();
            return await this.db.medications.toArray();
        } catch (error) {
            console.error('Failed to get medications:', error);
            return [];
        }
    }

    async deleteMedication(id) {
        try {
            if (!this.db) await this.init();
            await this.db.medications.delete(id);
            console.log('Medication deleted:', id);
        } catch (error) {
            console.error('Failed to delete medication:', error);
            throw error;
        }
    }

    // Stimulant operations
    async saveStimulant(stimulant) {
        try {
            if (!this.db) await this.init();
            const id = await this.db.stimulants.add(stimulant);
            console.log('Stimulant saved with ID:', id);
            return id;
        } catch (error) {
            console.error('Failed to save stimulant:', error);
            throw error;
        }
    }

    async getStimulants() {
        try {
            if (!this.db) await this.init();
            return await this.db.stimulants.toArray();
        } catch (error) {
            console.error('Failed to get stimulants:', error);
            return [];
        }
    }

    async deleteStimulant(id) {
        try {
            if (!this.db) await this.init();
            await this.db.stimulants.delete(id);
            console.log('Stimulant deleted:', id);
        } catch (error) {
            console.error('Failed to delete stimulant:', error);
            throw error;
        }
    }

    // Painkiller operations
    async savePainkiller(painkiller) {
        try {
            if (!this.db) await this.init();
            const id = await this.db.painkillers.add(painkiller);
            console.log('Painkiller saved with ID:', id);
            return id;
        } catch (error) {
            console.error('Failed to save painkiller:', error);
            throw error;
        }
    }

    async getPainkillers() {
        try {
            if (!this.db) await this.init();
            return await this.db.painkillers.toArray();
        } catch (error) {
            console.error('Failed to get painkillers:', error);
            return [];
        }
    }

    async deletePainkiller(id) {
        try {
            if (!this.db) await this.init();
            await this.db.painkillers.delete(id);
            console.log('Painkiller deleted:', id);
        } catch (error) {
            console.error('Failed to delete painkiller:', error);
            throw error;
        }
    }

    // App settings operations
    async saveAppSetting(key, value) {
        try {
            if (!this.db) await this.init();
            await this.db.app_settings.put({ key, value });
            console.log('App setting saved:', key, value);
        } catch (error) {
            console.error('Failed to save app setting:', error);
            throw error;
        }
    }

    async getAppSetting(key, defaultValue = null) {
        try {
            if (!this.db) await this.init();
            const setting = await this.db.app_settings.get(key);
            return setting ? setting.value : defaultValue;
        } catch (error) {
            console.error('Failed to get app setting:', error);
            return defaultValue;
        }
    }

    // User preferences operations
    async saveUserPreference(key, value) {
        try {
            if (!this.db) await this.init();
            await this.db.user_preferences.put({ key, value });
            console.log('User preference saved:', key, value);
        } catch (error) {
            console.error('Failed to save user preference:', error);
            throw error;
        }
    }

    async getUserPreference(key, defaultValue = null) {
        try {
            if (!this.db) await this.init();
            const preference = await this.db.user_preferences.get(key);
            return preference ? preference.value : defaultValue;
        } catch (error) {
            console.error('Failed to get user preference:', error);
            return defaultValue;
        }
    }

    // Clear all data
    async clearAllData() {
        try {
            if (!this.db) await this.init();
            await this.db.medications.clear();
            await this.db.stimulants.clear();
            await this.db.painkillers.clear();
            await this.db.app_settings.clear();
            await this.db.user_preferences.clear();
            console.log('All data cleared');
        } catch (error) {
            console.error('Failed to clear data:', error);
            throw error;
        }
    }

    // Export data
    async exportData() {
        try {
            if (!this.db) await this.init();
            const data = {
                medications: await this.getMedications(),
                stimulants: await this.getStimulants(),
                painkillers: await this.getPainkillers(),
                app_settings: await this.db.app_settings.toArray(),
                user_preferences: await this.db.user_preferences.toArray(),
                export_date: new Date().toISOString()
            };
            return data;
        } catch (error) {
            console.error('Failed to export data:', error);
            throw error;
        }
    }

    // Import data
    async importData(data) {
        try {
            if (!this.db) await this.init();
            
            // Clear existing data
            await this.clearAllData();
            
            // Import new data
            if (data.medications) {
                for (const med of data.medications) {
                    delete med.id; // Remove old ID
                    await this.saveMedication(med);
                }
            }
            
            if (data.stimulants) {
                for (const stim of data.stimulants) {
                    delete stim.id; // Remove old ID
                    await this.saveStimulant(stim);
                }
            }
            
            if (data.painkillers) {
                for (const pk of data.painkillers) {
                    delete pk.id; // Remove old ID
                    await this.savePainkiller(pk);
                }
            }
            
            if (data.app_settings) {
                for (const setting of data.app_settings) {
                    await this.saveAppSetting(setting.key, setting.value);
                }
            }
            
            if (data.user_preferences) {
                for (const pref of data.user_preferences) {
                    await this.saveUserPreference(pref.key, pref.value);
                }
            }
            
            console.log('Data imported successfully');
        } catch (error) {
            console.error('Failed to import data:', error);
            throw error;
        }
    }

    // Save all current data
    async saveAllData(data) {
        try {
            if (!this.db) await this.init();
            
            // Clear existing data first
            await this.clearAllData();
            
            // Import new data
            await this.importData(data);
            
            console.log('All data saved successfully');
            return true;
        } catch (error) {
            console.error('Failed to save all data:', error);
            throw error;
        }
    }
} // End of RitaliTimeDB class

// Create global instance
window.ritaliTimeDB = new RitaliTimeDB();

// Export for use in Dash callbacks
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RitaliTimeDB;
}
