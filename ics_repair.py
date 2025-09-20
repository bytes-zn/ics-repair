#!/usr/bin/env python3

import sys
import logging
import shutil
from pathlib import Path
from typing import List
from collections import defaultdict
from datetime import date, datetime, timedelta
from icalendar import Calendar, Event

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)


def read_file_chunks(file_path: Path) -> List[bytes]:
    try:
        with file_path.open('rb') as f:
            raw = f.read()
    except IOError as e:
        log.error(f"Could not read file: {file_path} - {e}")
        return []

    chunks = []
    marker = b'BEGIN:VCALENDAR'
    end_marker = b'END:VCALENDAR'
    start = 0

    while True:
        idx = raw.find(marker, start)
        if idx == -1:
            break
        end = raw.find(end_marker, idx)
        if end == -1:
            log.warning(f"File {file_path.name} has a VCALENDAR block without a closing tag.")
            break
        
        chunk = raw[idx:end + len(end_marker)]
        chunks.append(chunk)
        start = end + len(end_marker)

    if not chunks:
        log.warning(f"No VCALENDAR blocks found in {file_path.name}.")
    return chunks

def parse_chunks(chunks: List[bytes], filename: str) -> List[Calendar]:
    calendars = []
    for i, chunk in enumerate(chunks, start=1):
        try:
            cal = Calendar.from_ical(chunk)
            calendars.append(cal)
        except Exception as e:
            log.error(f"Chunk {i} in '{filename}' could not be parsed: {e}")
    return calendars

def series_key(ev: Event) -> tuple:
    summary = str(ev.get('SUMMARY', '')).strip()
    location = str(ev.get('LOCATION', '')).strip()
    duration = None

    dtstart_prop = ev.get('DTSTART')
    dtend_prop = ev.get('DTEND')

    if dtstart_prop and dtend_prop:
        dtstart = dtstart_prop.dt
        dtend = dtend_prop.dt

        is_start_date = isinstance(dtstart, date) and not isinstance(dtstart, datetime)
        is_end_date = isinstance(dtend, date) and not isinstance(dtend, datetime)

        try:
            if is_start_date and not is_end_date:
                dtstart = datetime.combine(dtstart, datetime.min.time(), tzinfo=dtend.tzinfo)
            elif not is_start_date and is_end_date:
                dtend = datetime.combine(dtend, datetime.min.time(), tzinfo=dtstart.tzinfo)
            
            duration = dtend - dtstart
        except Exception as e:
            log.warning(f"Could not calculate duration for event '{summary}': {e}")
            duration = timedelta(0)

    return (summary, location, duration)

def process_calendars(calendars: List[Calendar]) -> Calendar:
    if not calendars:
        return None

    merged = Calendar()
    
    first_cal = calendars[0]
    for key, value in first_cal.property_items():
        if key.upper() not in ('VEVENT', 'VTODO', 'VJOURNAL', 'VFREEBUSY', 'VTIMEZONE', 'VALARM'):
            merged.add(key, value)

    groups = defaultdict(list)
    all_events = []
    for cal in calendars:
        for component in cal.walk('VEVENT'):
            if isinstance(component, Event):
                all_events.append(component)

    for ev in all_events:
        groups[series_key(ev)].append(ev)

    final_events = []
    for key, ev_list in groups.items():
        master = None
        for ev in ev_list:
            if 'RRULE' in ev:
                master = ev
                break
        
        if master is None:
            master = ev_list[0]
        
        uid = master.get('UID')
        if not uid:
            summary, location, duration = key
            uid_base = f"{summary}-{location}-{duration}".replace(' ', '_').lower()
            uid = f"{uid_base}@fixed.by.script"
            master['UID'] = uid

        for ev in ev_list:
            ev['UID'] = uid
            final_events.append(ev)
    
    added_events = set()
    for ev in final_events:
        if not ev.get('DTSTART'):
            log.warning(f"Skipping event '{ev.get('SUMMARY')}' because it has no DTSTART.")
            continue
            
        recurrence_id = ev.get('RECURRENCE-ID')
        if recurrence_id:
            event_signature_date = recurrence_id.dt.isoformat()
        else:
            event_signature_date = ev.get('DTSTART').dt.isoformat()

        event_signature = (ev.get('UID'), event_signature_date)
        
        if event_signature not in added_events:
            merged.add_component(ev)
            added_events.add(event_signature)

    return merged

def process_file(file_path: Path):
    log.info(f"Processing file: {file_path.name}")
    chunks = read_file_chunks(file_path)
    if not chunks: return

    calendars = parse_chunks(chunks, file_path.name)
    if not calendars:
        log.error(f"No valid calendar blocks found in {file_path.name}.")
        return

    fixed_cal = process_calendars(calendars)
    
    if not fixed_cal:
        log.error(f"Could not create calendar object for {file_path.name}.")
        return

    try:
        backup_path = file_path.with_suffix(file_path.suffix + '.backup')
        shutil.copy2(file_path, backup_path)
        log.info(f"Backup created: {backup_path.name}")
    except Exception as e:
        log.error(f"Could not create backup for {file_path.name}: {e}")
        return

    try:
        with file_path.open('wb') as f:
            f.write(fixed_cal.to_ical(sorted=True))
        log.info(f"File successfully overwritten: {file_path.name}")
    except Exception as e:
        log.error(f"Could not write repaired file {file_path.name}: {e}")

def process_folder(folder_path: Path):
    if not folder_path.is_dir():
        log.error(f"{folder_path} is not a directory.")
        return

    log.info(f"Processing folder: {folder_path}")
    found_files = False
    for entry in folder_path.iterdir():
        if entry.is_file() and entry.suffix.lower() == '.ics':
            found_files = True
            process_file(entry)
    
    if not found_files:
        log.warning(f"No .ics files found in folder {folder_path}.")

def main():
    if len(sys.argv) != 2:
        print("Usage: python ics_repair.py <path/to/file.ics> or <path/to/folder>")
        sys.exit(1)

    target = Path(sys.argv[1]).expanduser().resolve()
    if not target.exists():
        log.error(f"The specified path does not exist: {target}")
        sys.exit(1)

    if target.is_file():
        if target.suffix.lower() != '.ics':
            log.error("The specified file is not an .ics file.")
            sys.exit(1)
        process_file(target)
    elif target.is_dir():
        process_folder(target)
    else:
        log.error(f"{target} is neither a valid file nor a folder.")
        sys.exit(1)

if __name__ == "__main__":
    main()