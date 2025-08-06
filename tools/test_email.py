#!/usr/bin/env python3
"""
Email Testing Script for ThyWill Production

This script tests email sending capabilities from the production web host.
It supports multiple email providers and configuration methods.

Usage:
    python tools/test_email.py --to recipient@example.com
    python tools/test_email.py --to recipient@example.com --provider gmail
    python tools/test_email.py --config  # Interactive configuration
    python tools/test_email.py --test-all  # Test all common configurations
"""

import argparse
import os
import smtplib
import ssl
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import getpass
import sys

# Common SMTP configurations
SMTP_CONFIGS = {
    'gmail': {
        'host': 'smtp.gmail.com',
        'port': 587,
        'use_tls': True,
        'auth_required': True,
        'note': 'Requires App Password, not regular password'
    },
    'outlook': {
        'host': 'smtp-mail.outlook.com',
        'port': 587,
        'use_tls': True,
        'auth_required': True,
        'note': 'Works with outlook.com, hotmail.com, live.com'
    },
    'yahoo': {
        'host': 'smtp.mail.yahoo.com',
        'port': 587,
        'use_tls': True,
        'auth_required': True,
        'note': 'Requires App Password'
    },
    'sendgrid': {
        'host': 'smtp.sendgrid.net',
        'port': 587,
        'use_tls': True,
        'auth_required': True,
        'note': 'Username: apikey, Password: your API key'
    },
    'mailgun': {
        'host': 'smtp.mailgun.org',
        'port': 587,
        'use_tls': True,
        'auth_required': True,
        'note': 'Use postmaster@your-domain.mailgun.org as username'
    },
    'local': {
        'host': 'localhost',
        'port': 25,
        'use_tls': False,
        'auth_required': False,
        'note': 'Local mail server (sendmail, postfix, etc.)'
    },
    'cpanel': {
        'host': 'mail.yourdomain.com',
        'port': 587,
        'use_tls': True,
        'auth_required': True,
        'note': 'Replace yourdomain.com with your actual domain'
    }
}

def get_host_info():
    """Get information about the current host."""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Try to get external IP
        try:
            import urllib.request
            external_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
        except:
            external_ip = "Unable to determine"
        
        return {
            'hostname': hostname,
            'local_ip': local_ip,
            'external_ip': external_ip
        }
    except Exception as e:
        return {'error': str(e)}

def test_smtp_connection(host, port, use_tls=True, timeout=10):
    """Test basic SMTP connection without authentication."""
    try:
        print(f"Testing connection to {host}:{port}...")
        
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=timeout)
            server.starttls(context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(host, port, timeout=timeout)
        
        response = server.noop()
        server.quit()
        
        print(f"✅ Connection successful: {response}")
        return True
        
    except smtplib.SMTPConnectError as e:
        print(f"❌ Connection failed: {e}")
        return False
    except smtplib.SMTPServerDisconnected as e:
        print(f"❌ Server disconnected: {e}")
        return False
    except socket.timeout:
        print(f"❌ Connection timeout after {timeout} seconds")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def send_test_email(host, port, username, password, from_email, to_email, use_tls=True):
    """Send a test email."""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = f"ThyWill Email Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Get host information
        host_info = get_host_info()
        
        body = f"""
This is a test email from ThyWill production server.

Email Configuration Test Results:
- SMTP Host: {host}:{port}
- TLS Enabled: {use_tls}
- Authentication: {'Yes' if username else 'No'}
- Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Server Information:
- Hostname: {host_info.get('hostname', 'Unknown')}
- Local IP: {host_info.get('local_ip', 'Unknown')}
- External IP: {host_info.get('external_ip', 'Unknown')}

If you received this email, email sending is working correctly!

--
ThyWill Email Test System
        """.strip()
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect and send
        print(f"Connecting to {host}:{port}...")
        if use_tls:
            server = smtplib.SMTP(host, port)
            server.starttls(context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(host, port)
        
        if username and password:
            print("Authenticating...")
            server.login(username, password)
        
        print(f"Sending email to {to_email}...")
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        
        print(f"✅ Email sent successfully!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        return False
    except smtplib.SMTPRecipientsRefused as e:
        print(f"❌ Recipients refused: {e}")
        return False
    except smtplib.SMTPServerDisconnected as e:
        print(f"❌ Server disconnected: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def interactive_config():
    """Interactive email configuration."""
    print("\n=== Interactive Email Configuration ===")
    
    print("\nAvailable providers:")
    for i, (name, config) in enumerate(SMTP_CONFIGS.items(), 1):
        print(f"{i}. {name.title()} - {config['host']}:{config['port']} - {config['note']}")
    
    try:
        choice = input(f"\nSelect provider (1-{len(SMTP_CONFIGS)}) or 'c' for custom: ").strip()
        
        if choice.lower() == 'c':
            host = input("SMTP Host: ").strip()
            port = int(input("SMTP Port (587): ").strip() or "587")
            use_tls = input("Use TLS? (y/n) [y]: ").strip().lower() != 'n'
            config_name = "custom"
        else:
            provider_names = list(SMTP_CONFIGS.keys())
            config_name = provider_names[int(choice) - 1]
            config = SMTP_CONFIGS[config_name]
            host = config['host']
            port = config['port']
            use_tls = config['use_tls']
            
            if config_name == 'cpanel':
                host = input(f"Enter your domain for mail.yourdomain.com [{host}]: ").strip() or host
        
        # Get credentials
        auth_required = input("Authentication required? (y/n) [y]: ").strip().lower() != 'n'
        if auth_required:
            username = input("Username/Email: ").strip()
            password = getpass.getpass("Password: ")
        else:
            username = password = None
        
        from_email = input(f"From email [{username if username else 'test@example.com'}]: ").strip()
        from_email = from_email or username or 'test@example.com'
        
        to_email = input("To email: ").strip()
        if not to_email:
            print("❌ To email is required")
            return
        
        return {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'from_email': from_email,
            'to_email': to_email,
            'use_tls': use_tls,
            'config_name': config_name
        }
        
    except (ValueError, IndexError, KeyboardInterrupt):
        print("\n❌ Invalid input or cancelled")
        return None

def main():
    parser = argparse.ArgumentParser(description='Test email sending from ThyWill production')
    parser.add_argument('--to', help='Recipient email address')
    parser.add_argument('--from', dest='from_email', help='Sender email address')
    parser.add_argument('--provider', choices=SMTP_CONFIGS.keys(), help='Email provider')
    parser.add_argument('--host', help='SMTP host')
    parser.add_argument('--port', type=int, help='SMTP port')
    parser.add_argument('--username', help='SMTP username')
    parser.add_argument('--password', help='SMTP password')
    parser.add_argument('--no-tls', action='store_true', help='Disable TLS')
    parser.add_argument('--config', action='store_true', help='Interactive configuration')
    parser.add_argument('--test-connection', action='store_true', help='Test connection only')
    parser.add_argument('--test-all', action='store_true', help='Test all provider connections')
    
    args = parser.parse_args()
    
    print("ThyWill Email Test Script")
    print("========================")
    
    # Show host information
    host_info = get_host_info()
    print(f"Running on: {host_info.get('hostname', 'Unknown')}")
    print(f"Local IP: {host_info.get('local_ip', 'Unknown')}")
    print(f"External IP: {host_info.get('external_ip', 'Unknown')}")
    print()
    
    if args.test_all:
        print("Testing connections to all providers...")
        for name, config in SMTP_CONFIGS.items():
            print(f"\n--- Testing {name.title()} ---")
            test_smtp_connection(config['host'], config['port'], config['use_tls'])
        return
    
    if args.config:
        config = interactive_config()
        if not config:
            return
    else:
        # Command line configuration
        if args.provider:
            provider_config = SMTP_CONFIGS[args.provider]
            host = args.host or provider_config['host']
            port = args.port or provider_config['port']
            use_tls = not args.no_tls and provider_config['use_tls']
        else:
            if not args.host:
                print("❌ Either --provider or --host is required")
                return
            host = args.host
            port = args.port or 587
            use_tls = not args.no_tls
        
        config = {
            'host': host,
            'port': port,
            'username': args.username,
            'password': args.password,
            'from_email': args.from_email or args.username or 'test@thywill.app',
            'to_email': args.to,
            'use_tls': use_tls,
            'config_name': args.provider or 'custom'
        }
    
    # Test connection first
    print(f"Testing {config['config_name']} configuration...")
    if not test_smtp_connection(config['host'], config['port'], config['use_tls']):
        print("❌ Connection test failed. Email sending will likely fail.")
        if input("Continue anyway? (y/n): ").strip().lower() != 'y':
            return
    
    if args.test_connection:
        print("✅ Connection test completed.")
        return
    
    if not config['to_email']:
        print("❌ Recipient email address is required for sending test email")
        return
    
    # Prompt for password if not provided
    if config['username'] and not config['password']:
        config['password'] = getpass.getpass("Password: ")
    
    # Send test email
    print(f"\nSending test email...")
    success = send_test_email(
        config['host'],
        config['port'],
        config['username'],
        config['password'],
        config['from_email'],
        config['to_email'],
        config['use_tls']
    )
    
    if success:
        print(f"\n✅ Email test completed successfully!")
        print(f"Check {config['to_email']} for the test email.")
        
        # Output environment variables for .env file
        print(f"\n=== Environment Variables for .env ===")
        print(f"SMTP_HOST={config['host']}")
        print(f"SMTP_PORT={config['port']}")
        print(f"SMTP_USE_TLS={'true' if config['use_tls'] else 'false'}")
        if config['username']:
            print(f"SMTP_USERNAME={config['username']}")
            print(f"SMTP_PASSWORD={config['password']}")
        print(f"SMTP_FROM_EMAIL={config['from_email']}")
    else:
        print(f"\n❌ Email test failed. Check the configuration and try again.")

if __name__ == "__main__":
    main()