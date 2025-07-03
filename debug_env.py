#!/usr/bin/env python3
"""
Debug script to check environment variable loading in production
"""
import os
from dotenv import load_dotenv

print("=== Environment Debug ===")

# Check current working directory
print(f"Current working directory: {os.getcwd()}")

# Check if .env file exists
env_file = ".env"
env_exists = os.path.exists(env_file)
print(f".env file exists: {env_exists}")

if env_exists:
    print(f".env file path: {os.path.abspath(env_file)}")

# Try loading .env
print("\nLoading .env file...")
load_dotenv()

# Check what we get for the invite token expiration
invite_hours_env = os.getenv("INVITE_TOKEN_EXPIRATION_HOURS")
print(f"INVITE_TOKEN_EXPIRATION_HOURS from environment: {invite_hours_env}")

# Calculate what TOKEN_EXP_H would be
TOKEN_EXP_H = int(os.getenv("INVITE_TOKEN_EXPIRATION_HOURS", "12"))
print(f"TOKEN_EXP_H calculated value: {TOKEN_EXP_H}")

# Check a few other important variables
print("\nOther environment variables:")
print(f"PORT: {os.getenv('PORT', 'not set')}")
print(f"ANTHROPIC_API_KEY: {'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}")

# Show current environment variables that contain "TOKEN" or "HOUR"
print("\nAll environment variables containing TOKEN or HOUR:")
for key, value in os.environ.items():
    if "TOKEN" in key.upper() or "HOUR" in key.upper():
        print(f"  {key}={value}")