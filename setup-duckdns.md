# DuckDNS Setup for LifeLine

## Quick Setup Steps:

1. **Create DuckDNS Account:**
   - Go to https://www.duckdns.org/
   - Sign in with your Google/GitHub account
   - This gives you access to free subdomains

2. **Create Your Subdomain:**
   - Choose a name like: `lifeline-yourname.duckdns.org`
   - Point it to your EC2 instance's public IP address
   - Copy your DuckDNS token (looks like: abcd1234-ef56-7890-abcd-123456789012)

3. **Update GitHub Secrets:**
   - Go to your GitHub repository
   - Settings → Secrets and variables → Actions
   - Update `EC2_HOSTNAME` to your new domain: `lifeline-yourname.duckdns.org`
   - Add a new secret `DUCKDNS_TOKEN` with your DuckDNS token

4. **Deploy:**
   - Push your code or manually trigger the GitHub Action
   - Your app will be available at: `https://lifeline-yourname.duckdns.org`

## Alternative Free DNS Services:
- **No-IP**: https://www.noip.com/ (30 hostnames free)
- **FreeDNS**: https://freedns.afraid.org/ (completely free)
- **Dynu**: https://www.dynu.com/ (4 hostnames free)

## Benefits:
- ✅ Completely free
- ✅ Trusted SSL certificates
- ✅ No browser security warnings
- ✅ Works immediately after setup
- ✅ Easy to share with friends
