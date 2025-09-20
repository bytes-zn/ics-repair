# ICS Repair 🛠️

A Python utility to repair and sanitize problematic iCalendar (`.ics`) files, making them compliant for import into modern calendar clients like Outlook, Google Calendar, and Apple Calendar.

This script was born out of the need to clean up messy calendar exports, especially from legacy systems that produce non-standard or malformed `.ics` files. It targets common issues that cause duplicate entries, broken recurring events, and import failures.

---

## The Problem It Solves

Many applications export calendar data in ways that violate the iCalendar standard (RFC 5545). This can lead to a variety of frustrating issues, including:

-   **Duplicate Events**: Importing a single file creates multiple copies of every event.
-   **Broken Event Series**: A recurring meeting appears as dozens of separate, individual appointments instead of a single series.
-   **Import Errors**: The calendar client outright rejects the file due to structural errors.
-   **Data Mismatches**: Subtle errors, like mixing full-day event dates with specific timestamps, cause exceptions and duplicates.

This script is designed to automatically fix these specific problems.

---

## Features ✨

-   **Fixes Multiple `VCALENDAR` Blocks**: Correctly parses files that improperly contain multiple `BEGIN:VCALENDAR` sections, merging them into one valid calendar.
-   **Unifies Recurring Event UIDs**: Identifies events that belong to the same recurring series and assigns them a single, consistent `UID`. This is the key to making Outlook and other clients recognize them as one series.
-   **Intelligent Deduplication**: After processing, it ensures that only unique event instances are saved in the final file.
-   **Handles Data Inconsistencies**: Robustly handles mixed `date` and `datetime` types that often cause `RECURRENCE-ID` errors.
-   **Automatic Backups**: Never lose your original data. The script automatically creates a `.backup` copy of each file it modifies.
-   **Batch Processing**: Run it on a single `.ics` file or an entire folder of them.

---

## Requirements

-   Python 3.6+
-   The `icalendar` Python library

You can install the required library using pip:
```shell
pip install icalendar
```

---

## Usage 🚀

The script is run from the command line and accepts a single argument: the path to an `.ics` file or a directory containing `.ics` files.

### To process a single file:
```shell
python ics_repair.py /path/to/your/calendar.ics
```

### To process all `.ics` files in a folder:
The script will scan the specified folder and process every `.ics` file it finds. The search is **not** recursive (it will not go into sub-folders).

```shell
python ics_repair.py /path/to/your/folder/
```

The script will log its progress to the console, informing you which files are being processed, when backups are created, and when files are successfully overwritten with the cleaned version.

---

## How It Works

The script follows a simple but effective four-step process for each file:

1.  **Chunk & Parse**: It first reads the raw file and splits it into valid `VCALENDAR` blocks. This immediately solves the issue of multiple calendars concatenated into one file. Each block is then safely parsed.
2.  **Group & Unify**: All events from all chunks are collected and grouped into "series" based on their core properties (summary, location, duration). It then finds the "master" event for each series (the one with the recurrence rule, `RRULE`) and applies its `UID` to all other events in that group.
3.  **Deduplicate & Merge**: A new, clean `Calendar` object is created. The script carefully adds each processed event, ensuring no exact duplicates (based on `UID` and start time) make it into the final version.
4.  **Backup & Write**: Finally, it creates a `.backup` of the original file and then overwrites it with the newly generated, clean iCalendar data.

---

## License

This project is licensed under the MIT License.