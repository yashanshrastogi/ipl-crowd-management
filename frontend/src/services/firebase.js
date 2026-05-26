/**
 * Firebase SDK initialization.
 * Configures Firestore for real-time listener support.
 *
 * Supports dynamic configuration loading from Firebase Hosting
 * and environment variable fallbacks.
 */

import { initializeApp, getApps } from 'firebase/app';
import { getFirestore, connectFirestoreEmulator } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'ipl-crowd-mgmt-2026.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'ipl-crowd-mgmt-2026',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || 'ipl-crowd-mgmt-2026.firebasestorage.app',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '',
};

let app = null;
let db = null;

// Initialize if API key is provided and is not the demo fallback
if (firebaseConfig.apiKey && firebaseConfig.apiKey !== 'demo-key') {
  try {
    app = initializeApp(firebaseConfig);
    db = getFirestore(app);
    if (import.meta.env.DEV && import.meta.env.VITE_USE_EMULATOR === 'true') {
      connectFirestoreEmulator(db, 'localhost', 8080);
    }
  } catch (error) {
    console.error('Failed to initialize Firebase with environment variables:', error);
  }
}

// Function to initialize dynamically when hosted on Firebase Hosting (fetch init.json)
export async function initFirebaseDynamic() {
  if (db) return db;
  try {
    const response = await fetch('/__/firebase/init.json');
    if (response.ok) {
      const config = await response.json();
      if (getApps().length === 0) {
        app = initializeApp(config);
      } else {
        app = getApps()[0];
      }
      db = getFirestore(app);
      console.log('Firebase initialized dynamically from hosting');
      return db;
    }
  } catch (err) {
    console.warn('Firebase dynamic initialization not available', err);
  }
  return null;
}

export { app, db };
export default db;
