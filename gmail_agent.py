from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os.path
import pickle
import datetime
import smtplib
import ssl 
import json
from google import genai
import os
import re
#-----------------------------Definitions -----------------------------
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.modify'
]

port = 465 # For SSL
smtp_server = "smtp.gmail.com"
sender_email = "egmh998@gmail.com"
password = os.getenv("GMAIL_APP_PASSWORD")
if not password:
    raise ValueError("password not set in environment")
context = ssl.create_default_context()

#-----------------------------Credentials -----------------------------
def access_creds():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

creds = access_creds()
service = build('calendar', 'v3', credentials=creds)
g_service = build("gmail", "v1", credentials=creds)

#-----------------------------Email Functions -----------------------------
def send_email(subject, body, recipient_email): 
    email = f"Subject:{subject}\n\n{body}"

    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        try:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, email.encode("utf-8"))
            print("Email sent successfully!")
        except Exception as e:
            print(f"Error sending email: {e}")

def get_emails():
    results = g_service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        maxResults=10,
    ).execute()

    emails = []
    for messages in results.get("messages", []):
        msg = g_service.users().messages().get(
            userId="me",
            id=messages["id"],
            format="metadata",
            metadataHeaders = ["From", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        emails.append({
            "from": headers.get("From"),
            "subject": headers.get("Subject"),
            "date": headers.get("Date"),})
    if not emails:
        return "No emails found."
    output = []
    for i, email in enumerate(emails, 1):
        output.append(
            f"{i}. {email['subject']}\n"
            f"   From: {email['from']}\n"
            f"   Date: {email['date']}\n"
        )     
    return "\n".join(output)

def search_email(arguments):
    query = arguments["query"]
    results = g_service.users().messages().list(
    userId="me",
    q=query,
    maxResults=10   
    ).execute()
    messages = results.get("messages", [])
    if not messages:
        return "No emails found."
    return [
        {
            "message_id": m["id"],
            "thread_id": m["threadId"]
        }
        for m in messages
    ]

def reply_email(arguments):
    message_id = arguments["message_id"]
    body = arguments["body"]
    thread_id = arguments.get("thread_id", None)

    message = g_service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    if not thread_id:
        thread_id = message.get("threadId")

    headers = {
        h["name"]: h["value"] for h in message["payload"]["headers"]
    }
    sender = headers.get("From")
    subject = headers.get("Subject")

    import base64
    from email.mime.text import MIMEText
    reply = MIMEText(body)
    reply["To"] = sender
    reply["Subject"] = "Re:" + (subject or "")
    reply["In-Reply-To"] = message_id
    reply["References"] = message_id

    raw = base64.urlsafe_b64encode(reply.as_bytes()).decode()
    send_result = g_service.users().messages().send(
        userId="me",
        body={
            "raw": raw,
            "threadId": thread_id
        }
    ).execute()
    return "Reply sent!"

#--------------- Calendar Functions --------------------------

def view_calendar(service):
    current = datetime.datetime.utcnow().isoformat() + "Z"
    events_result = service.events().list(
        calendarId='primary', 
        timeMin=current,
        maxResults = 10, 
        singleEvents=True,
        orderBy='startTime'
        ).execute()
    events = events_result.get('items', [])
    if not events:
        print('No upcoming events found.')
    result = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        summary = event.get('summary', 'No summary')
        result.append(f"{start} - {summary}")
    return "\n".join(result)

def create_calendar(service, summary, description, location, start_time, end_time):
    new_event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time,
            'timeZone': 'Europe/London',},
        'end': {
            'dateTime': end_time,
            'timeZone': 'Europe/London',},
    }
    created_event = service.events().insert(
        calendarId='primary',
        body=new_event
    ).execute()

def validate_time(time_str):
    try:
        datetime.datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except Exception:
        raise ValueError(f"Invalid time format: {time_str}")

def make_new_event(event_details):
    try:
        summary = event_details.get("summary", "")
        description = event_details.get("description", "")
        location = event_details.get("location", "")
        start_time = event_details.get("start_time", "")
        end_time = event_details.get("end_time", "")

        start_time = start_time.split("[")[0]
        end_time = end_time.split("[")[0]

        if not start_time or not end_time:
            raise ValueError("Missing event time")

        validate_time(start_time)
        validate_time(end_time)

        create_calendar(service, summary, description, location, start_time, end_time)
        return f"Event created with summary: {summary}"
    except Exception as e:
        print(f"Error generating event: {e}")

#-----------------------------Agent Tools --------------------------
def send_email_tool(arguments):
    send_email(
        subject=arguments["subject"],
        body=arguments["body"],
        recipient_email=arguments["recipient_email"]
    )
    return "Email sent successfully."
    
def view_emails_tool(arguments):
    return get_emails()

def view_calendar_tool(arguments):
    return view_calendar(service)

def create_event_tool(arguments):
    return make_new_event(arguments)

def search_email_tool(arguments):
    result = search_email(arguments)
    return json.dumps(result) if isinstance(result, list) else result

def reply_email_tool(arguments):
    if "message_id" not in arguments:
        return "Error: message_id is required."
    return reply_email(arguments)

# AGENT 1 TOOLS (search, calendar, send email - NO reply)
TOOLS_AGENT_1 = {
    "send_email": send_email_tool,
    "view_emails": view_emails_tool,
    "view_calendar": view_calendar_tool,
    "create_event": create_event_tool,
    "search_email": search_email_tool,
}

# AGENT 2 TOOLS (reply only)
TOOLS_AGENT_2 = {
    "reply_email": reply_email_tool
}

#-----------------------------Agent 1 Function (Search, Calendar, Send) --------------------------
def agent_1(query):
    """First agent: searches emails and handles calendar/send tasks"""
    prompt = """My name is Egameh. You are my google assistant that selects tools for my python system.
    
    Available tools:

    - send_email
    - view_emails
    - view_calendar
    - create_event
    - search_email
    
    Return format:
    {
  "tools": [
    { "tool": "send_email", "arguments": {...} },
    { "tool": "search_email", "arguments": {...} }
    ]
    }

    Tool Rules: 
   1. send_email
    - Must include: recipient_email, subject, body
    - Extract the email address from the user's query if present
    - Generate a concise subject
    - Generate a natural email body
    - If recipient_email is missing, set it to ""

    2. view_emails
    - arguments must be {}

    3. view_calendar
    - arguments must be {}

    4. create_event
    - must include: summary, description, location, start_time, end_time 
    - location may be an empty string ""
    - start_time and end_time must be ISO 8601 format 
    (Timezone:'Europe/London'(+01:00 in summer, +00:00 in winter). Example: 2026-06-23T19:00:00+01:00)
    
    5. search_email:
    - Convert natural language into Gmail query syntax
    - Examples:
    "emails from John" → "from:john"
    "unread emails" → "is:unread"
    "Amazon emails" → "Amazon"

    General rules:
    - You may call tools in sequence when required
    - Do NOT include extra keys
    - Output ONLY the JSON file
    - Do not wrap the JSON in markdown.
    - Do not use ```json code blocks.
    """
    try:
        conversation_history = [
            {"role": "user", "content": f"{prompt}\n\nQuery: {query}"}
        ]
        
        chat = client.chats.create(model="models/gemini-2.5-pro")
        response = chat.send_message(
            f"{prompt}\n\nQuery: {query}",
            config={"response_mime_type": "application/json"}
        )
        
        conversation_history.append({
            "role": "assistant",
            "content": response.text
        })
        
        data = json.loads(response.text)
        tools = data.get("tools", [])
        tool_result = ""
        tool_name = None
        search_results = None
        
        for t in tools:
            tool_name = t["tool"]
            arguments = t["arguments"]
            if tool_name not in TOOLS_AGENT_1:
                return f"unknown tool: {tool_name}"
            tool = TOOLS_AGENT_1[tool_name]
            tool_result = tool(arguments)
            
            # Store search results for potential reply
            if tool_name == "search_email":
                search_results = tool_result
        
        iterations = 0
        max_iterations = 5
        
        while tool_name not in ["send_email", "create_event", "view_emails", "view_calendar"]:
            if iterations >= max_iterations:
                return "Error: Exceeded maximum tool iterations."
            iterations += 1

            conversation_history.append({
                "role": "user",
                "content": f"""Tool executed: {tool_name}
Result: {tool_result}

Based on this result, decide the next tool.

Rules:
- If no further tools are needed, return: {{"tools":[]}}
- Output only JSON"""
            })
            
            response = chat.send_message(
                f"""Tool executed: {tool_name}
Result: {tool_result}

Based on this result, decide the next tool.

Rules:
- If no further tools are needed, return: {{"tools":[]}}
- Output only JSON""",
                config={"response_mime_type": "application/json"}
            )
            
            conversation_history.append({
                "role": "assistant",
                "content": response.text
            })
            
            print(response.text)
            data = json.loads(response.text)
            next_tool = data.get("tools", [])
            
            if not next_tool:
                break
            
            t = next_tool[0]
            tool_name = t["tool"]
            arguments = t["arguments"]
            if tool_name not in TOOLS_AGENT_1:
                return f"unknown tool: {tool_name}"
            tool = TOOLS_AGENT_1[tool_name]
            tool_result = tool(arguments)
            
            if tool_name == "search_email":
                search_results = tool_result
        
        # Ask user if they want to reply
        if search_results and search_results != "No emails found.":
            print(f"\n📧 Found emails: {search_results}\n")
            user_wants_reply = input("Do you want me to reply to one of these? (yes/no): ").strip().lower()
            
            if user_wants_reply in ["yes", "y"]:
                return {
                    "status": "reply_requested",
                    "search_results": search_results
                }
        
        return tool_result
    
    except Exception as e:
        print(f"Error processing query: {e}")
        import traceback
        traceback.print_exc()
        return f"Failed to process query: {e}"


#-----------------------------Agent 2 Function (Reply Only) --------------------------
def agent_2(search_results):
    """Second agent: replies to emails using search results from Agent 1"""
    
    prompt = f"""My name is Egameh. You are my google assistant.

I found these emails:
{search_results}

The user wants to reply. First, refine and complete their message into a proper email response.

Available tools:
- reply_email

Tool Rules:
1. reply_email:
   - Extract message_id and thread_id from the search results above
   - Take the user's input and turn it into a complete, polished email message
   - Include: message_id, thread_id, body (as a complete message)

Return format:
{{
  "tools": [
    {{"tool": "reply_email", "arguments": {{"message_id": "...", "thread_id": "...", "body": "complete polished message here"}}}}
  ]
}}

Output ONLY the JSON."""

    try:
        # Ask user what they want to say
        reply_text = input("What would you like to reply with? ").strip()
        
        chat = client.chats.create(model="models/gemini-2.5-pro")
        
        full_prompt = f"""{prompt}

The user wants to reply with: "{reply_text}"

Now use reply_email with the first email found."""
        
        response = chat.send_message(
            full_prompt,
            config={"response_mime_type": "application/json"}
        )
        
        data = json.loads(response.text)
        tools = data.get("tools", [])
        
        for t in tools:
            tool_name = t["tool"]
            arguments = t["arguments"]
            if tool_name not in TOOLS_AGENT_2:
                return f"unknown tool: {tool_name}"
            tool = TOOLS_AGENT_2[tool_name]
            tool_result = tool(arguments)
            print(f"✅ {tool_result}")
            return tool_result
        
        return "Reply not sent"
    
    except Exception as e:
        print(f"Error in agent 2: {e}")
        import traceback
        traceback.print_exc()
        return f"Failed to reply: {e}"


#-----------------------------Main Entry Point --------------------------

# If Agent 1 found emails and user wants to reply, run Agent 2
if __name__ == "__main__":
    test_query = "Can you create a reminder to my calendar for tomorrow at 1 AM called 'Review Notes'."
    result_1 = agent_1(test_query)
    if isinstance(result_1, dict) and result_1.get("status") == "reply_requested":
        print("\n➡️  Running reply agent...\n")
        result_2 = agent_2(result_1["search_results"])
        print(result_2)
    else:
        print(result_1)
