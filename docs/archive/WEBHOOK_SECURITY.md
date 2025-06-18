# 🔒 Webhook Test Security

## Problem
Real webhook test files contain sensitive data:
- Actual MAM torrent URLs with IDs
- Real download links
- Potentially identifying torrent information

## Solution ✅

### 📁 Production Tests (Safe for Git)
- `tests/test_mam_integration.py` - Uses example/placeholder data
- `tests/test_metadata_workflow.py` - Uses mock scenarios
- ✅ Safe to commit to git repositories

### 🔧 Real Testing (Local Only)
For testing with actual webhook data:

1. **Copy the template**:
   ```bash
   cp tests/test_mam_integration.py test_mam_integration_real.py
   ```

2. **Replace example data** in `test_mam_integration_real.py`:
   ```python
   # Replace this:
   'url': 'https://www.myanonamouse.net/t/EXAMPLE123'
   
   # With real MAM URL:
   'url': 'https://www.myanonamouse.net/t/1234567'
   ```

3. **Run real test locally**:
   ```bash
   python test_mam_integration_real.py
   ```

### 🛡️ Protection via .gitignore
Real webhook files are automatically excluded:
```gitignore
# Real webhook test files (contain actual MAM URLs/torrent IDs)
test_*_real.py
test_real_*.py
*_real_webhook*.py
webhook_payload_real*.json
```

## ✅ Benefits
- **Git Safe**: Production tests use placeholder data
- **Full Testing**: Real tests work locally with actual data
- **No Leaks**: Real MAM URLs never committed to git
- **Easy Setup**: Simple copy/edit process for real testing

## 🎯 Usage
- **CI/CD**: Runs safe example tests
- **Development**: Copy template for real data testing
- **Production**: All sensitive data stays local
