import datetime
import os
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from openai import OpenAI

def format_list(v):
  if v == None or len(v) == 0:
    return ''
  output = ''
  for element in v:
    output += element
    output += ', '
  if output == '':
    return output
  else:
    return output[:-2]

def get_gpt_summary(description):
  if False:
    return 'dont waste money' # Not to use up my GPT balance.
  else:
    client = OpenAI(
      api_key = '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'
    )
    completion = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=[
        {"role": "system", "content": "Great. Suppose you are a doctor, and want to describe the patient (but do not use first-person). Like, 'Patient ... blah blah blah. He/she is ... years old and blah and need...'. Only pick interesting things to say very concisely. Two sentences max and very very concise."},
        {"role": "user", "content": f"Describe the patient. {description} Suppose you are a doctor, and want to describe the patient (but do not use first-person). Like, 'Patient ... blah blah blah. He/she is ... years old and blah and need...'. Only pick interesting things to say very concisely. Two sentences max and very very concise."}
      ]
    )
    return completion.choices[0].message.content.strip()

def get_gpt_reason(description, est_diff):
  if est_diff == 0:
    return ''
  elif est_diff > 0:
    client = OpenAI(
      api_key = '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'
    )
    completion = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=[
        {"role": "system", "content": "You are helping me with the case."},
        {"role": "user", "content": f"We use AI to estimate the time difference between surgery. The operation is early for {abs(est_diff)} because of what? Give one sentence to justify it, one very short sentence, based upon this description, DO NOT MENTION THE ESTIMATED DIFFERENCE, JUST STATE THE REASON. {description}"}
      ]
    )
    return completion.choices[0].message.content.strip()
  else:
    client = OpenAI(
      api_key = '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'
    )
    completion = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=[
        {"role": "system", "content": "You are helping me with the case."},
        {"role": "user", "content": f"We use AI to estimate the time difference between surgery. The operation is delayed for {abs(est_diff)} because of what? Give one sentence to justify it, one very short sentence, based upon this description, DO NOT MENTION THE ESTIMATED DIFFERENCE, JUST STATE THE REASON. {description}"}
      ]
    )
    return completion.choices[0].message.content.strip()



class Schedule:
  SCOPES = ['https://www.googleapis.com/auth/calendar']

  def __init__(self):
    self.creds = None
    self.service = self.authenticate_google_calendar()

  def authenticate_google_calendar(self):
    """Authenticate and create a service object for Google Calendar API."""
    if os.path.exists("token.json"):
      self.creds = Credentials.from_authorized_user_file("token.json", self.SCOPES)

    if not self.creds or not self.creds.valid:
      if self.creds and self.creds.expired and self.creds.refresh_token:
        self.creds.refresh(Request())
      else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", self.SCOPES)
        self.creds = flow.run_local_server(port=0)

      with open("token.json", "w") as token:
        token.write(self.creds.to_json())

    return build("calendar", "v3", credentials=self.creds)

  def get_calendar_id_by_name(self, calendar_name):
    """Get the calendar ID for a given calendar name."""
    calendar_list = self.service.calendarList().list().execute()
    for calendar_entry in calendar_list['items']:
      if calendar_entry['summary'] == calendar_name:
        return calendar_entry['id']
    return None

  def get_events(self, max_results=10):
    """Get the upcoming 'max_results' events on the user's calendar."""
    try:
      now = datetime.datetime.utcnow().isoformat() + "Z"
      events_result = (
        self.service.events().list(
          calendarId='primary', 
          timeMin=now, 
          maxResults=max_results, 
          singleEvents=True,
          orderBy='startTime'
        ).execute()
      )
      return events_result.get("items", [])
    except HttpError as error:
      print(f"An error occurred: {error}")
      return None

  def add_event(self, event):
    """Add an event to the calendar."""
    try:
      event = self.service.events().insert(calendarId='primary', body=event).execute()
      print(f"Event created: {event.get('htmlLink')}")
      return event
    except HttpError as error:
      print(f"An error occurred: {error}")
      return None

  def add_medical_event(self, calendar_name, procedure_name, field, cpt_code, diagnosis, icd10_code, physician, start_time, end_time, equipments=None, comorbidities=None, anesthesia=None, description=None, est_diff=0):
    """
    Add a medical event to the calendar.

    Args:
        procedure_name (str): Name of the medical procedure.
        cpt_code (str): CPT code associated with the procedure.
        diagnosis (str): Diagnosis information.
        icd10_code (str): ICD9 code for the diagnosis.
        physician (str): Name of the attending physician.
        start_time (str): Start time of the event in RFC3339 format.
        end_time (str): End time of the event in RFC3339 format.
    """
    calendar_id = self.get_calendar_id_by_name(calendar_name)
    if not calendar_id:
      print(f"Calendar named '{calendar_name}' not found.")
      return None

    event = {
      'summary': procedure_name,
      'description': f"{get_gpt_summary(description)}\n\n"
                     f"{get_gpt_reason(description, est_diff)}"
                     f"<b>Field:</b> {field}\n"
                     f"<b>CPT Code:</b> {cpt_code}\n"
                     f"<b>Diagnosis:</b> {diagnosis}\n"
                     f"<b>ICD9 Code:</b> {icd10_code}\n"
                     f"<b>Equipments:</b> {format_list(equipments)}\n"
                     f"<b>Comorbidities:</b> {format_list(comorbidities)}\n"
                     f"<b>Anesthesia:</b> {anesthesia}\n",
      'start': {'dateTime': start_time},
      'end': {'dateTime': end_time},
      'attendees': [{'email': f"{physician}@example.com"}],
    }

    try:
        created_event = self.service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"Medical event created: {created_event.get('htmlLink')}")
        return created_event
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def print_events(events):
  for event in events:
    start = event["start"].get("dateTime", event["start"].get("date"))
    print(start, event["summary"])

if __name__ == "__main__":
  scheduler = Schedule()
  events = scheduler.get_events()

  print_events(events)

  scheduler.add_medical_event(
      calendar_name="OR 1",
      procedure_name="Sacrospinous Ligament Fixation",
      cpt_code="57282",
      diagnosis="Vaginal Vault Prolapse",
      icd10_code="618.5",
      physician="ja2890710",
      start_time="2024-03-15T09:00:00-07:00",
      end_time="2024-03-15T11:00:00-07:00"
  )

