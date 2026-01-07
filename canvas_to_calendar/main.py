from canvas_client import CanvasClient
from google_tasks import export_assignments_to_tasks

def main():
    canvas = CanvasClient()
    assignments = canvas.get_all_assignments()

    if len(assignments) == 0:
        print("No current assignments found")
        return

    print("Fetched assignments:")
    for a in assignments:
        due_str = a.due_at.strftime("%Y-%m-%d %H:%M %Z") if a.due_at else "No due date"
        print(f"{a.course_name} — {a.name} | Due: {due_str}")

    try:
        summary = export_assignments_to_tasks(assignments)
        print("\nGoogle Tasks export summary:")
        if summary["created"]:
            print(f"Created tasks ({len(summary['created'])}):")
            for t in summary["created"]:
                print(f"  - {t}")
        if summary["updated"]:
            print(f"Updated tasks ({len(summary['updated'])}):")
            for t in summary["updated"]:
                print(f"  - {t}")
        if summary["no_due_tasks_created"]:
            print(f"No due date reminders created ({len(summary['no_due_tasks_created'])}):")
            for t in summary["no_due_tasks_created"]:
                print(f"  - {t}")

        print("\nTasks successfully exported to Google Tasks.")
    except Exception as e:
        print(f"Error exporting tasks: {e}")


if __name__ == "__main__":
    main()
