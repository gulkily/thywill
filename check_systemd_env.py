#!/usr/bin/env python3
"""
Script to help debug systemd .env file loading issues
"""
import os
import subprocess
import pwd

print("=== Systemd Environment Debug ===")

# Get current user info
current_user = pwd.getpwuid(os.getuid()).pw_name
home_dir = os.path.expanduser("~")
print(f"Current user: {current_user}")
print(f"Home directory: {home_dir}")
print(f"Current working directory: {os.getcwd()}")

# Check possible .env file locations
possible_env_paths = [
    ".env",  # relative to current directory
    "./thywill/.env",  # if running from parent directory
    f"{home_dir}/.env",  # in home directory
    f"{home_dir}/thywill/.env",  # in thywill subdirectory
    "/home/thywill/thywill/.env",  # absolute path from systemd service
]

print("\n=== Checking .env file locations ===")
for path in possible_env_paths:
    exists = os.path.exists(path)
    abs_path = os.path.abspath(path) if exists else "N/A"
    print(f"{path}: {'EXISTS' if exists else 'NOT FOUND'}")
    if exists:
        print(f"  Absolute path: {abs_path}")
        try:
            with open(path, 'r') as f:
                lines = f.readlines()
            token_lines = [l.strip() for l in lines if 'INVITE_TOKEN_EXPIRATION_HOURS' in l]
            if token_lines:
                print(f"  INVITE_TOKEN_EXPIRATION_HOURS line: {token_lines[0]}")
            else:
                print("  No INVITE_TOKEN_EXPIRATION_HOURS found in file")
        except Exception as e:
            print(f"  Error reading file: {e}")
    print()

print("=== Systemd Service Information ===")
try:
    # Check if thywill service exists and get its status
    result = subprocess.run(['systemctl', 'status', 'thywill'], 
                          capture_output=True, text=True, timeout=10)
    print("Systemd service status:")
    print(result.stdout)
    if result.stderr:
        print("Stderr:", result.stderr)
except Exception as e:
    print(f"Could not get systemd status: {e}")

try:
    # Try to get the service file content
    result = subprocess.run(['systemctl', 'cat', 'thywill'], 
                          capture_output=True, text=True, timeout=10)
    print("\nSystemd service file content:")
    print(result.stdout)
    if result.stderr:
        print("Stderr:", result.stderr)
except Exception as e:
    print(f"Could not get systemd service file: {e}")

print("\n=== Current Environment Variables ===")
invite_hours = os.getenv("INVITE_TOKEN_EXPIRATION_HOURS")
print(f"INVITE_TOKEN_EXPIRATION_HOURS: {invite_hours}")
print(f"PORT: {os.getenv('PORT', 'not set')}")
print(f"ANTHROPIC_API_KEY: {'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}")

# Show all environment variables with TOKEN, HOUR, or starting with INVITE
print("\nRelevant environment variables:")
for key, value in sorted(os.environ.items()):
    if any(word in key.upper() for word in ['TOKEN', 'HOUR', 'INVITE', 'PORT']):
        print(f"  {key}={value}")