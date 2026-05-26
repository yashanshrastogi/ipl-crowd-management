# 1. Configuration
$PROJECT_ID = "gen-lang-client-0211219733"
$REGION = "us-central1"

# V-18: Secrets are stored in Google Secret Manager, not passed on command line.
# Before first run, create secrets:
#   "your-gemini-key" | gcloud secrets create GEMINI_API_KEY --data-file=- --project $PROJECT_ID
#   "your-maps-key" | gcloud secrets create MAPS_API_KEY --data-file=- --project $PROJECT_ID
#   "your-strong-admin-key" | gcloud secrets create ADMIN_API_KEY --data-file=- --project $PROJECT_ID

# 2. Enable APIs (One-time)
Write-Host "--- Enabling GCP APIs for $PROJECT_ID ---" -ForegroundColor Cyan
gcloud services enable run.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com pubsub.googleapis.com bigquery.googleapis.com dataflow.googleapis.com secretmanager.googleapis.com --project $PROJECT_ID

# 3. Deploy Backend (Direct Source Upload)
Write-Host "--- Deploying Backend to Cloud Run ---" -ForegroundColor Cyan
Push-Location backend
gcloud run deploy ipl-backend `
    --source . `
    --region $REGION `
    --project $PROJECT_ID `
    --no-allow-unauthenticated `
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID" `
    --set-secrets="GOOGLE_API_KEY=GEMINI_API_KEY:latest,GOOGLE_MAPS_API_KEY=MAPS_API_KEY:latest,ADMIN_API_KEY=ADMIN_API_KEY:latest"
$BACKEND_URL = (gcloud run services describe ipl-backend --region $REGION --project $PROJECT_ID --format="value(status.url)")
Pop-Location

# 4. Deploy Frontend (Direct Source Upload)
Write-Host "--- Deploying Frontend to Cloud Run ---" -ForegroundColor Cyan
Push-Location frontend
try {
    $dockerfilePath = "Dockerfile"
    $backupPath = $null
    if (Test-Path $dockerfilePath) {
        $backupPath = "Dockerfile.codex-backup"
        Move-Item -LiteralPath $dockerfilePath -Destination $backupPath -Force
    }

    # Create a temporary Dockerfile for the frontend to serve via node.
    @"
FROM node:20-slim
WORKDIR /app
COPY . .
RUN npm install && npm run build
RUN npm install -g serve@14.2.4
EXPOSE 8080
CMD ["serve", "-s", "dist", "-l", "8080"]
"@ | Out-File -FilePath $dockerfilePath -Encoding utf8

    gcloud run deploy ipl-frontend `
        --source . `
        --region $REGION `
        --project $PROJECT_ID `
        --allow-unauthenticated `
        --set-env-vars="VITE_BACKEND_URL=$BACKEND_URL"
}
finally {
    if (Test-Path $dockerfilePath) {
        Remove-Item -LiteralPath $dockerfilePath -Force
    }
    if ($backupPath -and (Test-Path $backupPath)) {
        Move-Item -LiteralPath $backupPath -Destination $dockerfilePath -Force
    }
    Pop-Location
}

Write-Host "`n--- Deployment Complete! ---" -ForegroundColor Green
Write-Host "Backend URL: $BACKEND_URL" -ForegroundColor Cyan
Write-Host "Frontend URL: Use the URL provided by the 'ipl-frontend' deployment above." -ForegroundColor Cyan
