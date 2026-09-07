# Deploy Backend to Cloud Run

```bash
cd backend

gcloud builds submit --tag gcr.io/PROJECT_ID/founder-shortcut-api

gcloud run deploy founder-shortcut-api \
  --image gcr.io/PROJECT_ID/founder-shortcut-api \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=PROJECT_ID,GOOGLE_GENAI_USE_VERTEXAI=TRUE,PUBSUB_TOPIC=founder-shortcut-jobs,DEMO_MODE=false \
  --service-account founder-shortcut@PROJECT_ID.iam.gserviceaccount.com
```

Grant the service account roles: `roles/datastore.user`, `roles/pubsub.publisher`, `roles/aiplatform.user`, `roles/secretmanager.secretAccessor`.

Secrets (Twilio, OAuth refresh token) should live in Secret Manager and be mounted via `--set-secrets`.

Frontend: `next build` then deploy to Cloud Run with the `Dockerfile` pattern or Firebase Hosting, setting `NEXT_PUBLIC_API_URL` to the backend URL.

Firestore rules should restrict reads/writes to authenticated users in production.
