# Label Updater

This script updates "Best if Used By:" dates on Google Drive PDFs for fudge and rice crispy treats labels.

## Deployment

1. Clone the repo
2. Set environment variables:
   - GOOGLE_CLIENT_ID
   - GOOGLE_CLIENT_SECRET
   - GOOGLE_REFRESH_TOKEN
3. Deploy to Cloud Run with Docker.
4. Schedule daily runs with Cloud Scheduler at 2 AM.
