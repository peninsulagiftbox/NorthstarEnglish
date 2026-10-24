import { request } from './catalog';
export type Preferences = { timezone: string; defaultSpeed: number; showTranslation: boolean; showHints: boolean; shortcutEnabled: boolean; recordingEnabled: boolean; rowVersion: number };
export const getPreferences = () => request<Preferences>('/settings');
export const savePreferences = (value: Preferences) => request<{ rowVersion: number }>('/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-Northstar-Request': 'local-workspace' }, body: JSON.stringify(value) });
