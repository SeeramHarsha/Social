# Social Media Post Generator Deployment on Google Cloud Run

This guide provides step-by-step instructions for deploying the Social Media Post Generator application to Google Cloud Run.

## Prerequisites

1.  **Google Cloud Platform (GCP) Account**: You need a GCP account with an active project and billing enabled.
2.  **Google Cloud SDK**: Install and initialize the `gcloud` command-line tool on your local machine. You can find instructions [here](https://cloud.google.com/sdk/docs/install).
3.  **Enabled APIs**: Ensure the following APIs are enabled in your GCP project:
    *   Cloud Build API
    *   Cloud Run API
    *   Artifact Registry API
4.  **Permissions**: Make sure your GCP user account has the necessary permissions to manage Cloud Run, Cloud Build, and Artifact Registry (e.g., `roles/run.admin`, `roles/cloudbuild.builds.editor`, `roles/artifactregistry.admin`).

## Deployment Steps

### 1. Containerize the Application

First, you need to create a `Dockerfile` to containerize the Flask application.

**Create a `Dockerfile` in the root of your project with the following content:**

```Dockerfile
# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV PORT 8080

# Run app.py when the container launches
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
```

You will also need to add `gunicorn` to your `requirements.txt` file.

### 2. Update `requirements.txt`

Add `gunicorn` to your [`requirements.txt`](requirements.txt) file. It should look like this:

```
Flask
pytrends
google-generativeai
requests
python-dotenv
gunicorn
```

### 3. Build the Docker Image using Google Cloud Build

Use Google Cloud Build to build the Docker image and push it to Google Artifact Registry. Replace `[PROJECT-ID]` with your GCP Project ID and `[REGION]` with your preferred region (e.g., `us-central1`).

```bash
gcloud builds submit --tag [REGION]-docker.pkg.dev/[PROJECT-ID]/cloud-run-source-deploy/social-media-app
```

### 4. Deploy to Google Cloud Run

Deploy the container image to Cloud Run. This command will create a new service.

```bash
gcloud run deploy social-media-app \
    --image [REGION]-docker.pkg.dev/[PROJECT-ID]/cloud-run-source-deploy/social-media-app \
    --platform managed \
    --region [REGION] \
    --allow-unauthenticated
```

### 5. Set Environment Variables

Your application uses environment variables stored in a `.env` file. In Cloud Run, you need to set these as secrets. It is highly recommended to use **Secret Manager** for this.

1.  **Store your secrets in Secret Manager**:
    ```bash
    echo "your-gemini-api-key" | gcloud secrets create GEMINI_API_KEY --data-file=-
    echo "your-unsplash-access-key" | gcloud secrets create UNSPLASH_ACCESS_KEY --data-file=-
    echo "your-ayrshare-api-key" | gcloud secrets create AYRSHARE_API_KEY --data-file=-
    ```

2.  **Grant your Cloud Run service account access to the secrets.**

3.  **Update your Cloud Run service to use the secrets**:
    Go to your service in the Google Cloud Console, click "Edit & Deploy New Revision", and under the "Variables & Secrets" tab, add the secrets.

After completing these steps, your application will be deployed and accessible at the URL provided by Cloud Run.