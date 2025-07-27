from twilio.rest import Client
import os
from twilio.rest import Client
from dotenv import load_dotenv
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)
message = client.messages.create(
  messaging_service_sid='MG4c367cc6b146a8b8215fb3a389f4108d',
  body='Hello mate 👋',
  to='+19728858576'
)
print(message.sid)