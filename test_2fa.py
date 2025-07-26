import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Load credentials from environment
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
verify_sid = os.getenv("TWILIO_VERIFY_SERVICE_SID")

client = Client(account_sid, auth_token)

# Replace with your test phone number in E.164 format (e.g., +12345678900)
phone_number = input("Enter your phone number (E.164): ")

# Step 1: Send verification code
verification = client.verify.services(verify_sid).verifications.create(to=phone_number, channel='sms')
print(f"Status: {verification.status} (OTP sent to {phone_number})")

# Step 2: Prompt for code
otp_code = input("Enter the OTP you received: ")

# Step 3: Check the verification code
check = client.verify.services(verify_sid).verification_checks.create(to=phone_number, code=otp_code)
print(f"Verification check status: {check.status}")

if check.status == "approved":
    print("✅ Success: 2FA complete!")
else:
    print("❌ Failed: Invalid code.")
