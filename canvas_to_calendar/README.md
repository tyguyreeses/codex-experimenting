# Course Due Dates Scanner

This project scans my current courses from Canvas

## How it works
1. Connects to Canvas
2. Fetches courses
3. Fetches assignments and their due dates for each course
4. Connects to Google Calendar
5. Removes duplicate tasks
6. Imports each task one day before the due date

## Setup
```bash
pip install -r requirements.txt
python main.py
