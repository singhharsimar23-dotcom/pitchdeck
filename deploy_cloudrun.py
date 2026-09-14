import time
import os
import tarfile
import json
import requests
import google.auth
from google.auth.transport.requests import Request

PROJECT_ID = "qwiklabs-gcp-03-58f8a6ff95cf"
REGION = "us-central1"
SERVICE_NAME = "grounded-pitch-tester"
BUCKET_NAME = f"run-sources-{PROJECT_ID}-{REGION}"
IMAGE_TAG = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/cloud-run-source-deploy/{SERVICE_NAME}:prod-{int(time.time())}"

def get_headers():
    creds, _ = google.auth.default()
    creds.refresh(Request())
    return {
        "Authorization": f"Bearer {creds.token}",
        "X-Goog-User-Project": PROJECT_ID
    }

def package_source(archive_name="source_deploy.tar.gz"):
    print("[1/5] Packaging source code...", flush=True)
    with tarfile.open(archive_name, "w:gz") as tar:
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "scratch", "venv", "env")]
            for file in files:
                if file.endswith((".tar.gz", ".zip", ".pyc", ".log")) or file == "deploy_cloudrun.py":
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, ".")
                tar.add(file_path, arcname=arcname)
    print(f"      Created {archive_name} ({os.path.getsize(archive_name)} bytes)", flush=True)
    return archive_name

def upload_source(archive_name="source_deploy.tar.gz"):
    print(f"[2/5] Uploading to Google Cloud Storage (gs://{BUCKET_NAME}/source.tar.gz)...", flush=True)
    headers = get_headers()
    headers["Content-Type"] = "application/gzip"
    url = f"https://storage.googleapis.com/upload/storage/v1/b/{BUCKET_NAME}/o?uploadType=media&name=source.tar.gz"
    with open(archive_name, "rb") as f:
        data = f.read()
    res = requests.post(url, headers=headers, data=data)
    res.raise_for_status()
    print("      Upload complete: HTTP 200 OK", flush=True)

def trigger_build():
    print(f"[3/5] Submitting Cloud Build for container: {IMAGE_TAG}...", flush=True)
    headers = get_headers()
    headers["Content-Type"] = "application/json"
    url = f"https://cloudbuild.googleapis.com/v1/projects/{PROJECT_ID}/builds"
    payload = {
        "source": {
            "storageSource": {
                "bucket": BUCKET_NAME,
                "object": "source.tar.gz"
            }
        },
        "steps": [
            {
                "name": "gcr.io/cloud-builders/docker",
                "args": ["build", "-t", IMAGE_TAG, "."]
            },
            {
                "name": "gcr.io/cloud-builders/docker",
                "args": ["push", IMAGE_TAG]
            }
        ],
        "images": [IMAGE_TAG]
    }
    res = requests.post(url, headers=headers, json=payload)
    res.raise_for_status()
    build_data = res.json()
    build_id = build_data["metadata"]["build"]["id"]
    print(f"      Cloud Build job initiated: {build_id}", flush=True)
    return build_id

def wait_for_build(build_id):
    print("      Waiting for Cloud Build container image compilation...", flush=True)
    url = f"https://cloudbuild.googleapis.com/v1/projects/{PROJECT_ID}/builds/{build_id}"
    while True:
        headers = get_headers()
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        status = res.json().get("status")
        print(f"      Build status: {status}", flush=True)
        if status in ("SUCCESS", "FAILURE", "INTERNAL_ERROR", "TIMEOUT", "CANCELLED"):
            if status != "SUCCESS":
                raise RuntimeError(f"Cloud Build failed with status: {status}")
            break
        time.sleep(10)
    print("      Container image successfully built and pushed to Artifact Registry!", flush=True)

def update_cloud_run():
    print(f"[4/5] Updating Cloud Run service '{SERVICE_NAME}' to image: {IMAGE_TAG}...", flush=True)
    headers = get_headers()
    get_url = f"https://run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}"
    res = requests.get(get_url, headers=headers)
    res.raise_for_status()
    service_def = res.json()

    # Update template container image
    service_def["template"]["containers"][0]["image"] = IMAGE_TAG
    
    # Send PATCH update
    headers["Content-Type"] = "application/json"
    patch_url = f"https://run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}"
    patch_res = requests.patch(patch_url, headers=headers, json=service_def)
    patch_res.raise_for_status()
    op_name = patch_res.json().get("name")
    print(f"      Service update operation started: {op_name}", flush=True)
    return op_name

def wait_for_service(op_name):
    print("[5/5] Waiting for Cloud Run service revision rollout...", flush=True)
    url = f"https://run.googleapis.com/v2/{op_name}"
    while True:
        headers = get_headers()
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json()
        done = data.get("done", False)
        if done:
            if "error" in data:
                raise RuntimeError(f"Cloud Run deployment failed: {data['error']}")
            service_resp = data.get("response", {})
            uri = service_resp.get("uri")
            print("==================================================", flush=True)
            print("DEPLOYMENT SUCCESSFUL!", flush=True)
            print(f"LIVE URL: {uri}", flush=True)
            print("==================================================", flush=True)
            return uri
        time.sleep(5)

if __name__ == "__main__":
    archive = package_source()
    upload_source(archive)
    build_id = trigger_build()
    wait_for_build(build_id)
    op = update_cloud_run()
    live_url = wait_for_service(op)
    if os.path.exists(archive):
        os.remove(archive)
