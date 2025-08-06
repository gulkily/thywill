# Email Deliverability Setup for thywill.live

## Current Status
✅ Local SMTP working on localhost:25  
✅ Sending from admin@thywill.live  
❓ Need SPF/DKIM records for better delivery  

## Step 1: Check Current DNS Records

```bash
# Check existing SPF record
dig TXT thywill.live | grep spf

# Check DKIM record (if any)
dig TXT default._domainkey.thywill.live
```

## Step 2: Set Up SPF Record

Add this TXT record to your DNS:

**DNS Record:**
```
Type: TXT
Name: @ (or thywill.live)
Value: v=spf1 ip4:37.60.241.75 ~all
```

**What this means:**
- `v=spf1` - SPF version 1
- `ip4:37.60.241.75` - Allow your server IP to send email
- `~all` - Soft fail for other IPs (recommended)

## Step 3: Generate DKIM Keys

On your server:

```bash
# Install opendkim tools
sudo apt update && sudo apt install opendkim-tools

# Create directory for keys
sudo mkdir -p /etc/opendkim/keys/thywill.live

# Generate DKIM key pair
sudo opendkim-genkey -t -s default -d thywill.live -D /etc/opendkim/keys/thywill.live

# View the public key for DNS
sudo cat /etc/opendkim/keys/thywill.live/default.txt
```

## Step 4: Add DKIM DNS Record

The `default.txt` file will show something like:
```
default._domainkey.thywill.live IN TXT "v=DKIM1; h=sha256; k=rsa; p=MIGfMA0GCSqG..."
```

Add this as a TXT record:
```
Type: TXT
Name: default._domainkey
Value: v=DKIM1; h=sha256; k=rsa; p=MIGfMA0GCSqG...
```

## Step 5: Configure Postfix with DKIM

```bash
# Install and configure OpenDKIM
sudo apt install opendkim postfix-opendkim

# Configure OpenDKIM
sudo nano /etc/opendkim.conf
```

Add these lines:
```
Domain                  thywill.live
KeyFile                 /etc/opendkim/keys/thywill.live/default.private
Selector                default
```

```bash
# Configure Postfix to use DKIM
sudo nano /etc/postfix/main.cf
```

Add these lines:
```
# DKIM
milter_default_action = accept
milter_protocol = 2
smtpd_milters = local:opendkim/opendkim.sock
non_smtpd_milters = local:opendkim/opendkim.sock
```

```bash
# Restart services
sudo systemctl restart opendkim postfix
```

## Step 6: Add DMARC Record (Optional but Recommended)

Add this TXT record:
```
Type: TXT
Name: _dmarc
Value: v=DMARC1; p=quarantine; rua=mailto:admin@thywill.live
```

## Step 7: Test Email Delivery

```bash
# Test again after DNS propagation (wait 10-60 minutes)
python tools/test_email.py --from admin@thywill.live --to your-external-email@gmail.com --host localhost --port 25 --no-tls
```

## Step 8: Verify DNS Records

Check your setup:
```bash
# Check SPF
dig TXT thywill.live

# Check DKIM  
dig TXT default._domainkey.thywill.live

# Check DMARC
dig TXT _dmarc.thywill.live
```

## Quick DNS Summary

Add these 3 TXT records to thywill.live DNS:

1. **SPF:** `@ → v=spf1 ip4:37.60.241.75 ~all`
2. **DKIM:** `default._domainkey → v=DKIM1; h=sha256; k=rsa; p=...` 
3. **DMARC:** `_dmarc → v=DMARC1; p=quarantine; rua=mailto:admin@thywill.live`

## Alternative: Skip DKIM Setup

If DKIM setup is too complex, just add the SPF record - it will significantly improve delivery by itself.

The SPF record alone tells receiving servers that your IP (37.60.241.75) is authorized to send email for thywill.live.