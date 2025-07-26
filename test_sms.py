from twilio.rest import Client
account_sid = 'ACc8131e14d6d03ece7885f9a9778411e6'
auth_token = 'a68dffdf8f3c99e7960fbbea06fdafa9'
client = Client(account_sid, auth_token)
message = client.messages.create(
  messaging_service_sid='MG4c367cc6b146a8b8215fb3a389f4108d',
  body='Hello mate 👋',
  to='+19728858576'
)
print(message.sid)