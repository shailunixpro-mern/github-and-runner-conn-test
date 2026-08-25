import os
import requests
import time
from datetime import datetime

AWX_TEMPLATE_NAME = "Get Ubuntu Hostname Job Template"

AWX_URL = os.environ["AWX_URL"].rstrip("/")
AWX_USERNAME = os.environ["AWX_USERNAME"]
AWX_PASSWORD = os.environ["AWX_PASSWORD"]

SNOW_INSTANCE = os.environ["SERVICENOW_INSTANCE"].rstrip("/")
SNOW_USER = os.environ["SERVICENOW_USER"]
SNOW_PASSWORD = os.environ["SERVICENOW_PASSWORD"]

# Existing ServiceNow Incident SYS_ID
SERVICENOW_SYS_ID = os.environ["SERVICENOW_SYS_ID"]


def get_awx_job_template_id():

    url = f"{AWX_URL}/api/v2/job_templates/"

    r = requests.get(
        url,
        params={"name": AWX_TEMPLATE_NAME},
        auth=(AWX_USERNAME, AWX_PASSWORD),
        timeout=30
    )

    r.raise_for_status()

    results = r.json()["results"]

    if not results:
        raise Exception(
            f"AWX template not found: {AWX_TEMPLATE_NAME}"
        )

    return results[0]["id"]


def get_latest_awx_job(template_id):

    url = f"{AWX_URL}/api/v2/jobs/"

    r = requests.get(
        url,
        params={
            "job_template": template_id,
            "order_by": "-id"
        },
        auth=(AWX_USERNAME, AWX_PASSWORD),
        timeout=30
    )

    r.raise_for_status()

    jobs = r.json()["results"]

    if not jobs:
        raise Exception(
            "No AWX jobs found."
        )

    return jobs[0]


def construct_log_path(job_id, started):

    started_dt = datetime.strptime(
        started,
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )

    timestamp = started_dt.strftime(
        "%Y%m%d_%H%M%S"
    )

    template_folder = AWX_TEMPLATE_NAME.replace(
        " ",
        "_"
    )

    logfile = (
        f"/var/log/awx-job-log/"
        f"{template_folder}/"
        f"{job_id}_joboutput_{timestamp}.log"
    )

    return logfile


def read_log_file(log_path):

    if not os.path.exists(log_path):
        raise Exception(
            f"Log file not found: {log_path}"
        )

    with open(
        log_path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as file:

        return file.read()


def create_incident(job_id):

    short_description = (
        f"{AWX_TEMPLATE_NAME} - Job id {job_id}"
    )

    payload = {
        "variables": {
            "short_description": short_description,
            "description":
                "This is a Automated job output trigger from AWX"
        }
    }

    url = (
        f"https://{SNOW_INSTANCE}"
        f"/api/sn_sc/servicecatalog/items/"
        f"{SERVICENOW_SYS_ID}"
        f"/submit_producer"
    )

    r = requests.post(
        url,
        auth=(SNOW_USER, SNOW_PASSWORD),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json=payload,
        timeout=60
    )

    r.raise_for_status()

    return r.json()["result"]


def update_existing_incident(sys_id, work_notes, job_id):

    url = (
        f"https://{SNOW_INSTANCE}"
        f"/api/now/table/incident/{sys_id}"
    )

    payload = {
        "short_description":
            f"{AWX_TEMPLATE_NAME} - Job id {job_id}",
        "description":
            "This is a Automated job output trigger from AWX",    
        "comments":
            f"AWX Job Output\n\n{work_notes[:15000]}"
    }

    print("PATCH URL:", url)
    print("WORK NOTES SIZE:", len(payload["work_notes"]))

    r = requests.patch(
        url,
        auth=(SNOW_USER, SNOW_PASSWORD),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json=payload,
        timeout=60
    )

    print("PATCH status:", r.status_code)
    print("PATCH response:", r.text)

    try:
        print(r.json())
    except Exception:
        print(r.text)

    r.raise_for_status()

    return r.json()


def close_incident(sys_id):

    url = (
            f"https://{SNOW_INSTANCE}"
        f"/api/now/table/incident/{sys_id}"
    )

    payload = {
        "incident_state": "7",
        "state": "7",
        "close_code": "Solved (Permanently)",
        "close_notes":
            "Closed automatically because AWX job completed successfully."
    }

    r = requests.patch(
        url,
        auth=(SNOW_USER, SNOW_PASSWORD),
        headers={
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=60
    )

    r.raise_for_status()

def get_incident(sys_id):

    url = (
        f"https://{SNOW_INSTANCE}"
        f"/api/now/table/incident/{sys_id}"
    )

    r = requests.get(
        url,
        auth=(SNOW_USER, SNOW_PASSWORD),
        headers={"Accept":"application/json"}
    )

    r.raise_for_status()

    return r.json()["result"]

def verify_incident(sys_id):

    url = (
        f"https://{SNOW_INSTANCE}"
        f"/api/now/table/incident/{sys_id}"
        f"?sysparm_display_value=true"
        f"&sysparm_fields=number,comments,work_notes"
    )

    r = requests.get(
        url,
        auth=(SNOW_USER, SNOW_PASSWORD),
        headers={"Accept": "application/json"}
    )

    r.raise_for_status()

    print("VERIFY INCIDENT:")
    print(r.text)

def main():

    print(
        "Discovering latest AWX job..."
    )

    template_id = get_awx_job_template_id()

    job = get_latest_awx_job(template_id)

    job_id = job["id"]
    job_status = job["status"]
    job_started = job["started"]

    print(f"Job ID: {job_id}")
    print(f"Job Status: {job_status}")
    print(f"Started: {job_started}")

    log_path = construct_log_path(
        job_id,
        job_started
    )

    print(
        f"Searching log file:"
        f" {log_path}"
    )

#    log_contents = read_log_file(
#        log_path
#    )

    log_contents = read_log_file(log_path)

    print(f"Log file length: {len(log_contents)} chars")
    print("First 200 characters:")
    print(log_contents[:200])

    print(
        "Creating ServiceNow incident..."
    )

    created_incident = create_incident(job_id)

    print("Created Incident Response:")
    print(created_incident)

    incident_sys_id = created_incident["sys_id"]
    incident_number = created_incident["number"]

    print(
        f"Created Incident: {incident_number}"
    )

    print(
        f"Incident SYS_ID: {incident_sys_id}"
    )

    incident = get_incident(incident_sys_id)

    print(
        f"Incident Number: "
        f"{incident['number']}"
    )

    result = update_existing_incident(
        incident_sys_id,
        log_contents,
        job_id
    )

    print(result)

    time.sleep(5)

    print(
        "Work notes updated."
    )

    verify_incident(incident_sys_id)

    if job_status.lower() != "failed":

        print(
            "AWX job succeeded."
        )

        close_incident(
            incident_sys_id
        )

        print(
            "ServiceNow incident closed."
        )

    else:

        print(
            "AWX job failed."
        )

        print(
            "Leaving incident open."
        )


if __name__ == "__main__":
    main()
