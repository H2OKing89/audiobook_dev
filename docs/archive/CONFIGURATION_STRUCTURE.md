# 📁 Configuration File Structure

## Overview
All configuration files are organized in the `config/` directory for better organization and security.

## Files Structure

```
config/
├── config.yaml                    # Main application configuration
├── config.yaml.example           # Template for main config
├── mam_config.json               # MAM credentials (create from example)
└── mam_config.json.example       # Template for MAM config
```

## Configuration Setup

### 1. Main Configuration
- **File**: `config/config.yaml`
- **Contains**: Rate limits, API endpoints, notifications, security settings
- **Status**: ✅ Already configured and working

### 2. MAM Configuration (Optional)
- **File**: `config/mam_config.json`
- **Contains**: MAM login credentials, browser settings
- **Status**: ❌ Needs to be created for full MAM functionality

## Setting Up MAM Configuration

### Quick Setup
```bash
python setup_mam_config.py
```
This creates `config/mam_config.json` from the template.

### Manual Setup
1. Copy the example:
   ```bash
   cp config/mam_config.json.example config/mam_config.json
   ```

2. Edit `config/mam_config.json` and add your credentials:
   ```json
   {
     "username": "your_mam_username",
     "password": "your_mam_password",
     ...
   }
   ```

## Security Notes

### Git Ignore Protection
The following files are automatically excluded from git:
- `config/mam_config.json` (contains credentials)
- `mam_cookies.json` (contains session data)
- `config/config.yaml` (may contain API keys)

### Safe Files (Templates)
These are safe to commit:
- `config/config.yaml.example`
- `config/mam_config.json.example`

## Current Status

✅ **Main config**: Working with 30s rate limiting  
❌ **MAM config**: Not set up (using Audible fallback)  
✅ **Rate limiting**: Properly configured  
✅ **Security**: Credentials protected from git  

## Next Steps

1. **For basic functionality**: Current setup works perfectly with Audible fallback
2. **For enhanced functionality**: Set up MAM config to enable ASIN extraction and Audnex metadata
3. **For production**: Consider using environment variables for sensitive data

The system works great without MAM config, but adding it unlocks richer metadata and chapter information!
