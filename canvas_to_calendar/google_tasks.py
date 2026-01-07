from datetime import timedelta, time
from zoneinfo import ZoneInfo
from typing import Iterable
import os
import pickle
import logging

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

from canvas_client import Assignment, MOUNTAIN_TZ

SCOPES = ["https://www.googleapis.com/auth/tasks"]

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


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
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return tasks


def delete_tasks_by_title(service, titles, tasklist_id="@default"):
    """
    Delete any existing tasks that match titles in the provided list.
    """
    tasks = get_existing_tasks(service, tasklist_id)
    title_set = set(titles)
    deleted = []
    for task in tasks:
        if "title" in task and task["title"] in title_set:
            try:
                service.tasks().delete(tasklist=tasklist_id, task=task["id"]).execute()
                logging.info(f"Deleted existing task: {task['title']}")
                deleted.append(task["title"])
            except HttpError as e:
                logging.warning(f"Failed to delete '{task['title']}': {e}")
    return deleted


def export_assignments_to_tasks(assignments: Iterable[Assignment]):
    """
    Export assignments to Google Tasks.
    Deletes existing tasks with matching names, then inserts fresh tasks.
    """
    service = get_tasks_service()
    tasklist_id = "@default"

    # Collect all titles to delete
    titles_to_delete = []

    # Standard assignments
    for a in assignments:
        course_short = a.course_name.split("-")[0].strip()
        titles_to_delete.append(f"{course_short} — {a.name}")

        if not a.due_at:
            # For no-due-date assignments, also prepare the 4 reminder titles
            dated_assignments = [d for d in assignments if d.due_at]
            if dated_assignments:
                earliest_due = min(d.due_at for d in dated_assignments)
                for i in range(4):
                    reminder_title = f"{course_short} — {a.name} — Reminder {i+1}"
                    titles_to_delete.append(reminder_title)

    # Delete all existing tasks with these titles
    logging.info("Deleting any existing tasks with matching titles...")
    delete_tasks_by_title(service, titles_to_delete, tasklist_id)

    summary = {
        "created": [],
        "no_due_tasks_created": []
    }

    # Determine earliest assignment for no-due-date reminders
    dated_assignments = [a for a in assignments if a.due_at]
    earliest_due = min(a.due_at for a in dated_assignments) if dated_assignments else None

    # Insert all tasks fresh
    for a in assignments:
        course_short = a.course_name.split("-")[0].strip()
        title = f"{course_short} — {a.name}"

        if a.due_at:
            due_local = normalize_due_time(a.due_at)
            reminder_time = (due_local - timedelta(days=1)).replace(hour=8, minute=0)

            task_body = {
                "title": title,
                "notes": f"Due: {due_local.strftime('%Y-%m-%d %H:%M %Z')}",
                "due": reminder_time.isoformat()
            }
            service.tasks().insert(tasklist=tasklist_id, body=task_body).execute()
            logging.info(f"Created task: {title}")
            summary["created"].append(title)

        else:
            # No-due-date assignments (extra credit, practice, etc.)
            if not earliest_due:
                logging.info(f"Skipping no-due-date assignment '{title}' because no dated assignments exist.")
                continue

            for i in range(4):
                reminder_time = (earliest_due + timedelta(days=30 * i)).replace(hour=8, minute=0)
                no_due_title = f"{title} — Reminder {i+1}"
                task_body = {
                    "title": no_due_title,
                    "notes": "No due date assignment — periodic reminder",
                    "due": reminder_time.isoformat()
                }
                service.tasks().insert(tasklist=tasklist_id, body=task_body).execute()
                logging.info(f"Created no-due-date task: {no_due_title}")
                summary["no_due_tasks_created"].append(no_due_title)

    return summary
