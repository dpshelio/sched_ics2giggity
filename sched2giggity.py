import xml.etree.ElementTree as ET
import datetime

import requests
from ics import Calendar
from bs4 import BeautifulSoup

url = "https://stateofopencon2024.sched.com/all.ics"
c = Calendar(requests.get(url).text)


def get_speakers(url):
    page_req = requests.get(url)
    page = page_req.text
    soup = BeautifulSoup(page, "html.parser")
    persons = soup.findAll("div", {"class": "sched-person-session"})
    result = {person.find("h2").text: person.text for person in persons}
    return result


def seconds_to_hourformat(seconds):
    hours = int(seconds / 3600)
    minutes = int(seconds % 3600 / 60)
    return f"{hours}:{minutes}"


def name2slug(text):
    text.replace(':','').replace(',', '').replace('"', '')
    return '-'.join(text.split())


def extract_dates(events):
    first_event = min(events)
    last_event = max(events)
    output = list()
    for x in range((last_event.begin - first_event.begin).days + 1):
        start = (first_event.begin.datetime + datetime.timedelta(days=x))
        date_day = start.strftime('%Y-%m-%d')
        end = start - datetime.timedelta(hours=start.time().hour,
                                       minutes=start.time().minute) + datetime.timedelta(hours=23, minutes=59)
        output.append({'date': date_day,
                       'start': start,
                       'end': end})
    return output

events = list(c.timeline)
speaker_id = 0
uids = []
dates = extract_dates(events)
tracks = set(sum(map(lambda x: list(x.categories), events), []))
rooms = set(list(map(lambda x: x.location.split(',')[0], events)))

schedule = ET.Element('schedule')
version = ET.SubElement(schedule, 'version')
version.text = 'latest'

conference = ET.SubElement(schedule, 'conference')
acronym =  ET.SubElement(conference, 'acronym')
acronym.text = 'soocon24' # FIXME
title =  ET.SubElement(conference, 'title')
title.text = "State of Open Con 24"  # FIXME take it automatically from ics header - calname
subtitle =  ET.SubElement(conference, 'subtitle')
venue =  ET.SubElement(conference, 'venue')
venue.text = ', '.join(events[0].location.split(',')[1:]).strip()  # FIXME No really, but good for now.
city =  ET.SubElement(conference, 'city')
city.text = events[0].location.split(',')[-1].split()[0].strip()
start =  ET.SubElement(conference, 'start')
start.text = dates[0]['date']
end =  ET.SubElement(conference, 'end')
end.text = dates[-1]['date']
days = ET.SubElement(conference, 'days')
days.text = len(dates)
day_change = ET.SubElement(conference, 'day_change')
day_change.text = dates[0]["start"].strftime('00:00:00:')  # FIXME using midnight for now
timeslot_duration = ET.SubElement(conference, 'timeslot_duration')
timeslot_duration.text = "00:05:00"
base_url = ET.SubElement(conference, 'base_url')
base_url.text = '/'.join(url.split('/')[:-1])
time_zone_name = ET.SubElement(conference, 'time_zone_name')
time_zone_name.text = "Europe/London"  # FIXME how to extract it? we've got the city, maybe there's a tool for that

tracks = ET.SubElement(schedule, 'tracks')
for t in tracks:
    t_xml = ET.SubElement(tracks, 'track')
    t_xml.set('online_qa', 'true')
    t_xml.text = t
for day, day_prop in enumerate(dates, start=1):
    day_xml = ET.SubElement(schedule, 'day')
    day_xml.set('index', f"{day}")
    day_xml.set('date', day_prop["date"])
    day_xml.set('start', day_prop["start"])
    day_xml.set('end', day_prop["end"])
    for room in rooms:
        room_xml =  ET.SubElement(day_xml, 'room')
        room_xml.set('name', room)
        room_xml.set("slug", name2slug(room))
        for event in filter(lambda x: room in x.location and
                            day_prop["start"] < x.begin < day_prop["end"],
                            events):
            # if room in event.location and day_prop["start"] < event.begin < day_prop["end"]:
            speakers = get_speakers(event.url)

            event_xml = ET.SubElement(room_xml, 'event')
            event_xml.set('guid', event.uid)
            date_xml = ET.SubElement(event_xml, 'date')
            date_xml.text = event.begin
            start_xml = ET.SubElement(event_xml, 'start')
            start_xml.text = event.begin.strftime("%H:%M")
            duration_xml = ET.SubElement(event_xml, 'duration')
            duration_xml = seconds_to_hourformat(event.duration.total_seconds())
            room_xml = ET.SubElement(event_xml, 'room')
            room_xml.text = room
            slug_xml = ET.SubElement(event_xml, 'slug')
            slug_xml.text = name2slug(event.name)
            url_xml = ET.SubElement(event_xml, 'url')
            url_xml.text = event.url
            title_xml = ET.SubElement(event_xml, 'title')
            title_xml.text = event.name
            subtitle_xml = ET.SubElement(event_xml, 'subtitle')
            track_xml = ET.SubElement(event_xml, 'track')
            track_xml.text = list(event.categories)[0]
            type_xml = ET.SubElement(event_xml, 'type')
            type_xml.text = list(event.categories)[0]
            language_xml = ET.SubElement(event_xml, 'language')
            language_xml.text = 'en'
            abstract_xml = ET.SubElement(event_xml, 'abstract')
            abstract_xml.text = event.description
            description_xml = ET.SubElement(event_xml, 'description')
            description_xml.text = "".join(speakers.values())
            feedback_xml = ET.SubElement(event_xml, 'feedback')
            feedback_xml.text = event.url
            persons_xml = ET.SubElement(event_xml, 'persons')
            attachments_xml = ET.SubElement(event_xml, 'attachments')
            links_xml = ET.SubElement(event_xml, 'links')
            for speaker in speakers:
                person_xml = ET.SubElement(persons_xml, 'person')
                person_xml.set('id', speaker_id)
                person_xml.text = speaker
                speaker_id += 1
            link_xml = ET.SubElement(links_xml, 'link')
            link_xml.set('href', event.url)
            link_xml.text = "Session page"
            # elements.remove(element)  # This is bad, but how could I do it to don't iterate on all?


breakpoint()
ET.indent(schedule)
with open("soocon24.xml", "wb") as f:
    f.write(ET.tostring(schedule, encoding="unicode"))


