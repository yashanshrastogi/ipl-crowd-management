/**
 * Constants — Threshold values, gate configurations, stadium data.
 * Mirrors backend thresholds for client-side display logic.
 */

// ── Crowd Density Thresholds (ped/m²) ────────────────────────
export const DENSITY_NORMAL_MAX = 0.5;
export const DENSITY_ELEVATED_MAX = 1.0;
export const DENSITY_WARNING = 1.5;
export const DENSITY_CRITICAL = 4.0;

// ── Physics Constants ────────────────────────────────────────
export const V_MAX = 1.34;        // Free-flow velocity (m/s)
export const A_FOOTPRINT = 0.26;  // Pedestrian area (m²/ped)

// ── Wait Time Thresholds (minutes) ───────────────────────────
export const WAIT_CLEAR_MAX = 5;
export const WAIT_DELAYED_MAX = 15;

// ── Risk Level Labels ────────────────────────────────────────
export const RISK_LEVELS = {
  NORMAL: { label: 'Normal', color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
  ELEVATED: { label: 'Elevated', color: '#06b6d4', bg: 'rgba(6,182,212,0.15)' },
  WARNING: { label: 'Warning', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  CRITICAL: { label: 'Critical', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
};

// ── Gate Status Labels ───────────────────────────────────────
export const GATE_STATUSES = {
  CLEAR: { label: 'Clear', color: '#10b981', markerColor: 'green' },
  DELAYED: { label: 'Delayed', color: '#f59e0b', markerColor: 'yellow' },
  BLOCKED: { label: 'Blocked', color: '#ef4444', markerColor: 'red' },
};

// ── M. Chinnaswamy Stadium Configuration ─────────────────────
export const STADIUM = {
  id: 'chinnaswamy_stadium',
  name: 'M. Chinnaswamy Stadium',
  city: 'Bengaluru',
  capacity: 40000,
  center: { lat: 12.9788, lng: 77.5996 },
  zoom: 17,
};

// ── Gate Positions (approximate real-world coordinates) ──────
export const GATES = [
  { id: 'gate_a', name: 'Gate A', lat: 12.9792, lng: 77.5990, section: 'North' },
  { id: 'gate_b', name: 'Gate B', lat: 12.9795, lng: 77.5998, section: 'North-East' },
  { id: 'gate_c', name: 'Gate C', lat: 12.9790, lng: 77.6003, section: 'East' },
  { id: 'gate_d', name: 'Gate D', lat: 12.9785, lng: 77.6002, section: 'South-East' },
  { id: 'gate_e', name: 'Gate E', lat: 12.9782, lng: 77.5996, section: 'South' },
  { id: 'gate_f', name: 'Gate F', lat: 12.9783, lng: 77.5989, section: 'South-West' },
  { id: 'gate_g', name: 'Gate G', lat: 12.9786, lng: 77.5985, section: 'West' },
  { id: 'gate_h', name: 'Gate H', lat: 12.9790, lng: 77.5986, section: 'North-West' },
];

// ── Banned Items for Strict Protocol ─────────────────────────
export const BANNED_ITEMS = [
  { icon: '🎒', label: 'Bags', detail: 'No backpacks or large bags' },
  { icon: '🪙', label: 'Coins', detail: 'No loose coins allowed' },
  { icon: '🍶', label: 'Bottles', detail: 'No glass or plastic bottles' },
  { icon: '☂️', label: 'Umbrellas', detail: 'No umbrellas permitted' },
  { icon: '🔪', label: 'Sharp Objects', detail: 'No knives or blades' },
  { icon: '🧨', label: 'Fireworks', detail: 'No firecrackers or flares' },
];

// ── Environment Sensor Labels ────────────────────────────────
export const SENSOR_LABELS = {
  temperature: { label: 'Temperature', unit: '°C', icon: '🌡️' },
  humidity: { label: 'Humidity', unit: '%', icon: '💧' },
  co2: { label: 'CO₂', unit: 'ppm', icon: '🌫️' },
  pm25: { label: 'PM2.5', unit: 'µg/m³', icon: '🌬️' },
  tvoc: { label: 'TVOC', unit: 'ppb', icon: '☁️' },
  noise_level: { label: 'Noise', unit: 'dB', icon: '🔊' },
};

// ── API Configuration ────────────────────────────────────────
const configuredApiBaseUrl = import.meta.env.VITE_BACKEND_URL;
export const API_BASE_URL = configuredApiBaseUrl
  ? configuredApiBaseUrl.replace(/\/$/, '')
  : '/api';

// ── Maps Beta Warning ────────────────────────────────────────
export const MAPS_BETA_WARNING =
  'Walking paths may lack completed sidewalks or pedestrian crossings';
