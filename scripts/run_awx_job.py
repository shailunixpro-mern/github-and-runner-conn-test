#!/usr/bin/env python3

import os
import sys
import time
import requests

AWX_URL = os.environ["AWX_URL"].rstrip("/")
AWX_USERNAME = os.environ["AWX_USERNAME"]
AWX_PASSWORD = os.environ["AWX_PASSWORD"]

JOB_TEMPLATE_NAME = os.environ.get(
    "JOB_TEMPLATE_NAME",
    "Get Ubuntu Hostname Job Template"
)

session = requests.Session()
session.auth = (AWX_USERNAME, AWX_PASSWORD)
session.verify = False


def get_job_template_id(job_template_name):
    url = f"{AWX_URL}/api/v2/job_templates/"
    response = session.get(
        url,
        params={"name": job_template_name}
    )
    response.raise_for_status()

    results = response.json()["results"]

    if not results:
        raise Exception(
            f"Job Template '{job_template_name}' not found"
        )

    return results[0]["id"]


def launch_job(template_id):
    url = f"{AWX_URL}/api/v2/job_templates/{template_id}/launch/"

    response = session.post(url, json={})
    response.raise_for_status()

    data = response.json()

    if not data.get("job"):
        raise Exception("Failed to start AWX job")

    return data["job"]


def wait_for_completion(job_id):

    while True:

        response = session.get(
            f"{AWX_URL}/api/v2/jobs/{job_id}/"
        )
        response.raise_for_status()

        status = response.json()["status"]

        print(f"Current Status : {status}")

        if status == "successful":
            return

        if status in ["failed", "error", "canceled"]:
            raise Exception(
                f"AWX Job ended with status {status}"
            )

        time.sleep(10)


def get_job_name(job_id):
    response = session.get(
        f"{AWX_URL}/api/v2/jobs/{job_id}/"
    )
    response.raise_for_status()

    return response.json()["name"]


def download_stdout(job_id, log_file):

    url = (
        f"{AWX_URL}/api/v2/jobs/"
        f"{job_id}/stdout/?format=txt_download"
    )

    response = session.get(url)
    response.raise_for_status()

    with open(log_file, "w") as f:
        f.write(response.text)


def main():

    print(f"Searching Job Template: {JOB_TEMPLATE_NAME}")

    template_id = get_job_template_id(
        JOB_TEMPLATE_NAME
    )

    print(f"Template ID: {template_id}")

    job_id = launch_job(template_id)

    print(f"Job ID: {job_id}")

    wait_for_completion(job_id)

    job_name = get_job_name(job_id)

    log_dir = f"/var/log/awx-job-log/{job_name}"
    os.makedirs(log_dir, exist_ok=True)

    log_file = f"{log_dir}/joboutput.log"

    download_stdout(job_id, log_file)

    print(f"Log saved at: {log_file}")

    with open(log_file, "r") as f:
        print("\n===== AWX JOB OUTPUT =====\n")
        print(f.read())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
