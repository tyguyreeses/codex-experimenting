import requests
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from dateutil.parser import parse
from zoneinfo import ZoneInfo

from settings import CANVAS_BASE_URL, CANVAS_API_TOKEN

MOUNTAIN_TZ = ZoneInfo("America/Denver")

@dataclass
class Assignment:
    name: str
    course_name: str
    due_at: Optional[datetime]

class CanvasClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {CANVAS_API_TOKEN}"
        })

    def get_courses(self) -> list:
        """Fetch all active courses with pagination."""
        url = f"{CANVAS_BASE_URL}/api/v1/courses"
        params = {"enrollment_state": "active", "per_page": 100}
        all_courses = []

        while url:
            r = self.session.get(url, params=params)
            r.raise_for_status()
            all_courses.extend(r.json())
            url = r.links.get('next', {}).get('url')
            params = None  # only needed for first request
        return all_courses

    def get_assignments_for_course(self, course_id: int) -> list:
        """Fetch all assignments (including external/LTI) for a course with pagination."""
        url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments"
        params = {
            "per_page": 100,
            "include[]": ["submission_types", "all_dates"]
        }
        all_assignments = []

        while url:
            r = self.session.get(url, params=params)
            r.raise_for_status()
            all_assignments.extend(r.json())
            url = r.links.get('next', {}).get('url')
            params = None  # only needed for first request
        return all_assignments

    def canvas_to_mountain(self, due_utc: Optional[datetime]) -> Optional[datetime]:
        """Convert Canvas UTC datetime to Mountain Time (DST-aware)."""
        if due_utc is None:
            return None
        if due_utc.tzinfo is None:
            due_utc = due_utc.replace(tzinfo=ZoneInfo("UTC"))
        return due_utc.astimezone(MOUNTAIN_TZ)

    def get_all_assignments(self) -> List[Assignment]:
        """Fetch all assignments across all courses, convert to Mountain Time, and sort."""
        results: List[Assignment] = []

        for course in self.get_courses():
            course_name = course.get("name", "Unknown Course")

            for a in self.get_assignments_for_course(course["id"]):
                due_at = parse(a["due_at"]) if a.get("due_at") else None
                due_at_local = self.canvas_to_mountain(due_at)

                results.append(
                    Assignment(
                        name=a["name"],
                        course_name=course_name,
                        due_at=due_at_local
                    )
                )

        # Sort by due date, using a timezone-aware max for assignments without a due date
        results.sort(key=lambda x: x.due_at or datetime.max.replace(tzinfo=MOUNTAIN_TZ))
        return results
