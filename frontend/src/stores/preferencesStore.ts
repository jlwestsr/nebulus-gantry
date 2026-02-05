import { create } from 'zustand';

const PREFS_KEY = 'nebulus-preferences';

interface Preferences {
  showTimestamps: boolean;
  showTokenUsage: boolean;
  showGenerationSpeed: boolean;
}

interface PreferencesState extends Preferences {
  setPreference: <K extends keyof Preferences>(key: K, value: Preferences[K]) => void;
}

function loadPreferences(): Preferences {
  try {
    const stored = localStorage.getItem(PREFS_KEY);
    if (stored) return { ...defaults, ...JSON.parse(stored) };
  } catch {
    // ignore
  }
  return defaults;
}

const defaults: Preferences = {
  showTimestamps: true,
  showTokenUsage: false,
  showGenerationSpeed: false,
};

export const usePreferencesStore = create<PreferencesState>((set) => ({
  ...loadPreferences(),
  setPreference: (key, value) =>
    set((state) => {
      const next = { ...state, [key]: value };
      localStorage.setItem(
        PREFS_KEY,
        JSON.stringify({
          showTimestamps: next.showTimestamps,
          showTokenUsage: next.showTokenUsage,
          showGenerationSpeed: next.showGenerationSpeed,
        })
      );
      return { [key]: value };
    }),
}));
