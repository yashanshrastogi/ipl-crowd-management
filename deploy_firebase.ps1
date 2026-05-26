$ErrorActionPreference = "Stop"

Write-Host "Deploying IPL Crowd Management to Firebase..." -ForegroundColor Cyan

# 1. Build the frontend
Write-Host "Fetching backend URL for frontend build..." -ForegroundColor Cyan
$BACKEND_URL = (gcloud run services describe ipl-backend --region us-central1 --project gen-lang-client-0211219733 --format="value(status.url)")
Write-Host "Backend URL: $BACKEND_URL"

Write-Host "Building frontend..." -ForegroundColor Cyan
Set-Location frontend
$env:VITE_BACKEND_URL = $BACKEND_URL
npm run build
Set-Location ..

# 2. Deploy to Firebase
Write-Host "Deploying to Firebase (Hosting & Firestore rules)..." -ForegroundColor Cyan
Set-Location frontend
npx firebase deploy --project ipl-crowd-mgmt-2026 --only hosting,firestore:rules --config ../firebase.json
Set-Location ..

# 3. Update Cloud Run CORS
Write-Host "Updating Cloud Run backend CORS configuration..." -ForegroundColor Cyan
$FRONTEND_URLS = "https://ipl-crowd-mgmt-2026.web.app,https://ipl-crowd-mgmt-2026.firebaseapp.com"
$BACKEND_INITIAL_CORS = "http://localhost:5173,http://localhost:3000"
$NEW_CORS_ORIGINS = "$FRONTEND_URLS,$BACKEND_INITIAL_CORS"

# Note: Using the project ID where the backend was deployed (gen-lang-client-0211219733)
$CorsEnvVars = "^@^CORS_ORIGINS=$NEW_CORS_ORIGINS"

gcloud run services update ipl-backend `
  --region us-central1 `
  --project gen-lang-client-0211219733 `
  --update-env-vars=$CorsEnvVars

Write-Host "Deployment complete! Visit https://ipl-crowd-mgmt-2026.web.app" -ForegroundColor Green
