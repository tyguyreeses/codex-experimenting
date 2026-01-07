"""
Scan current courses for all assignment due dates and print them.

Currently implemented for Canvas LMS.
Adapt the API calls if you use a different LMS.
"""

import requests
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from dateutil.parser import parse

from settings import CANVAS_BASE_URL, CANVAS_API_TOKEN

# =========================
# MODELS
# =========================

@dataclass
class Assignment:
    name: str
    course_name: str
    due_at: Optional[datetime]

# =========================
# CANVAS CLIENT
# =========================

class CanvasClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {CANVAS_API_TOKEN}"
        })

    def get_courses(self) -> list:
        url = f"{CANVAS_BASE_URL}/api/v1/courses"
        params = {"enrollment_state": "active"}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_assignments_for_course(self, course_id: int) -> list:
        url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_all_assignments(self) -> List[Assignment]:
        assignments: List[Assignment] = []

        for course in self.get_courses():
            course_name = course.get("name", "Unknown Course")
            course_id = course["id"]

            for a in self.get_assignments_for_course(course_id):
                due_at = parse(a["due_at"]) if a.get("due_at") else None

                assignments.append(
                    Assignment(
                        name=a["name"],
                        course_name=course_name,
                        due_at=due_at
                    )
                )

        assignments.sort(key=lambda x: x.due_at or datetime.max)
        return assignments

# =========================
# MAIN
# =========================

def main():
    client = CanvasClient()
    assignments = client.get_all_assignments()

    if not assignments:
        print("No assignments found.")
        return

    print("\nUpcoming Due Dates")
    print("-" * 60)

    for a in assignments:
        due = a.due_at.strftime("%Y-%m-%d %H:%M") if a.due_at else "No due date"
        print(f"{due:20} | {a.course_name} | {a.name}")

if __name__ == "__main__":
    main()
