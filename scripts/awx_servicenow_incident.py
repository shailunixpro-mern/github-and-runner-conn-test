import os
import requests
from datetime import datetime

AWX_TEMPLATE_NAME = "Get Ubuntu Hostname Job Template"

AWX_URL = os.environ["AWX_URL"].rstrip("/")
AWX_USERNAME = os.environ["AWX_USERNAME"]
AWX_PASSWORD = os.environ["AWX_PASSWORD"]

SNOW_INSTANCE = os.environ["SERVICENOW_INSTANCE"].rstrip("/")
SNOW_USER = os.environ["SERVICENOW_USER"]
SNOW_PASSWORD = os.environ["SERVICENOW_PASSWORD"]


def get_awx_job_template_id():
    url = f"{AWX_URL}/api/v2/job_templates/"
    r = requests.get(
        url,
        params={"name": AWX_TEMPLATE_NAME},
        auth=(AWX_USERNAME, AWX_PASSWORD),
        timeout=30,
    )
    r.raise_for_status()

    results = r.json()["results"]
