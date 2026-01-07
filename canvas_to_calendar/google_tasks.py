from datetime import timedelta, time
from zoneinfo import ZoneInfo
from typing import Iterable
import os
import pickle

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from canvas_client import Assignment, MOUNTAIN_TZ

SCOPES = ["https://www.googleapis.com/auth/tasks"]

def get_tasks_service():
    creds = None
    if os.path.exists("token.json"):
        with open("token.json", "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "wb") as f:
            pickle.dump(creds, f)

    return build("tasks", "v1", credentials=creds)


def normalize_due_time(dt: 'datetime') -> 'datetime':
    """If due at midnight, change to 6 PM"""
    if dt.time() == time(0, 0):
        dt = dt.replace(hour=18, minute=0)
    return dt


def get_existing_tasks(service, tasklist_id="@default"):
    """Fetch all tasks from Google Tasks with pagination"""
    tasks = []
    page_token = None
    while True:
        result = service.tasks().list(tasklist=tasklist_id, pageToken=page_token).execute()
        tasks.extend(result.get("items", []))
        page_token = result.get('nextPageToken')
        if not page_token:
            break
    return tasks


def export_assignments_to_tasks(assignments: Iterable[Assignment]):
    """Export assignments to Google Tasks, returning a summary of created/updated tasks."""
    service = get_tasks_service()
    tasklist_id = "@default"

    # Load existing tasks to avoid duplicates
    existing_tasks = get_existing_tasks(service, tasklist_id)
    existing_titles = {task["title"]: task for task in existing_tasks}

    # Determine earliest assignment for scheduling no-due-date reminders
    dated_assignments = [a for a in assignments if a.due_at]
    earliest_due = min(a.due_at for a in dated_assignments) if dated_assignments else None

    summary = {
        "created": [],
        "updated": [],
        "no_due_tasks_created": []
    }

    for a in assignments:
        course_short = a.course_name.split("-")[0].strip()
        title = f"{course_short} — {a.name}"

        if a.due_at:
            # Standard assignment: reminder 1 day early at 8 AM
            due_local = normalize_due_time(a.due_at)
            reminder_time = (due_local - timedelta(days=1)).replace(hour=8, minute=0)

            task_body = {
                "title": title,
                "notes": f"Due: {due_local.strftime('%Y-%m-%d %H:%M %Z')}",
                "due": reminder_time.isoformat()
            }

            if title in existing_titles:
                service.tasks().update(
                    tasklist=tasklist_id,
                    task=existing_titles[title]["id"],
                    body=task_body
                ).execute()
                summary["updated"].append(title)
            else:
                service.tasks().insert(
                    tasklist=tasklist_id,
                    body=task_body
                ).execute()
                summary["created"].append(title)

        else:
            # No due date assignment (extra credit, practice, etc.)
            if not earliest_due:
                continue  # no dated assignments to base schedule on

            for i in range(4):
                reminder_time = (earliest_due + timedelta(days=30 * i)).replace(hour=8, minute=0)
                no_due_title = f"{title} — Reminder {i+1}"
                task_body = {
                    "title": no_due_title,
                    "notes": "No due date assignment — periodic reminder",
                    "due": reminder_time.isoformat()
                }

                if no_due_title in existing_titles:
                    service.tasks().update(
                        tasklist=tasklist_id,
                        task=existing_titles[no_due_title]["id"],
                        body=task_body
                    ).execute()
                    summary["updated"].append(no_due_title)
                else:
                    service.tasks().insert(
                        tasklist=tasklist_id,
                        body=task_body
                    ).execute()
                    summary["no_due_tasks_created"].append(no_due_title)

    return summary
