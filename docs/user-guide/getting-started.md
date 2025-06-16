# 🚀 Getting Started with Audiobook Automation

Welcome to your new audiobook automation system! This guide will get you up and running quickly.

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.8+** installed on your system
- **SQLite** (usually included with Python)
- **Git** for cloning the repository
- **A web browser** for accessing the interface

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/kingpaging/audiobook-automation.git
cd audiobook-automation
```

### 2. Set Up Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the System

Copy the example configuration:

```bash
cp config/config.yaml.example config/config.yaml
```

Edit `config/config.yaml` with your preferred settings. See the [Configuration Guide](configuration.md) for detailed options.

### 5. Initialize the Database

```bash
python src/db.py
```

### 6. Start the Application

```bash
python src/main.py
```

The web interface will be available at `http://localhost:8000` (or your configured port).

## 🎯 First Steps

### 1. Access the Web Interface

Open your browser and navigate to `http://localhost:8000`. You should see the beautiful audiobook automation homepage with Quentin's mascot!

### 2. Test the System

- Click **"Request Audiobook"** to submit a test request
- Check the **"Browse Requests"** page to see your submission
- Try the approval/rejection workflow

### 3. Set Up Notifications

Configure your preferred notification method in `config/config.yaml`:

- **Discord** - For Discord server notifications
- **Gotify** - For self-hosted push notifications
- **Ntfy** - For simple push notifications
- **Pushover** - For mobile push notifications

See the [Notifications Guide](notifications.md) for detailed setup instructions.

## 🔧 Basic Configuration

Here's a minimal configuration to get started:

```yaml
# config/config.yaml
server:
  host: "0.0.0.0"
  port: 8000
  debug: false

database:
  path: "db.sqlite"

notifications:
  enabled: true
  # Configure your preferred notification service
  discord:
    enabled: false
    webhook_url: ""
  
security:
  token_expiry_hours: 24
  max_requests_per_hour: 10
```

## 🌐 Web Interface Tour

### Home Page
- **Clean, modern design** with animated elements
- **Quick action buttons** for common tasks
- **System status** and information

### Request Audiobook
- **Simple form** for submitting requests
- **Validation** to ensure quality submissions
- **Instant feedback** on submission status

### Browse Requests
- **Organized list** of all requests
- **Filtering and sorting** options
- **Status tracking** for each request

### Approval/Rejection Pages
- **Beautiful, engaging interfaces** with personality
- **Clear feedback** for users
- **Automatic redirects** and notifications

## 🛠️ Common Tasks

### Adding a New Request

1. Navigate to the home page
2. Click **"Request Audiobook"**
3. Fill out the form with book details
4. Submit and wait for approval notification

### Checking Request Status

1. Go to **"Browse Requests"**
2. Find your request in the list
3. Check the status column
4. Click for more details if needed

### Configuring Notifications

1. Edit `config/config.yaml`
2. Enable your preferred notification service
3. Add the required credentials/URLs
4. Restart the application
5. Test with a sample request

## 🔍 Troubleshooting

### Common Issues

**Port Already in Use**
```bash
# Change the port in config/config.yaml
server:
  port: 8001
```

**Database Errors**
```bash
# Reinitialize the database
rm db.sqlite
python src/db.py
```

**Permission Errors**
```bash
# Check file permissions
chmod +x src/*.py
```

### Getting Help

- Check the [Troubleshooting Guide](troubleshooting.md)
- Review the logs in the `logs/` directory
- Open an issue on GitHub with:
  - Your configuration (remove sensitive data)
  - Error messages from logs
  - Steps to reproduce the issue

## 🎉 Next Steps

Now that you're up and running:

1. **[Configure Notifications](notifications.md)** - Set up your preferred notification method
2. **[Customize the Interface](../development/architecture.md)** - Learn about customization options
3. **[Set Up Integrations](../api/webhooks.md)** - Connect with external services
4. **[Explore Advanced Features](configuration.md)** - Dive deeper into configuration options

## 📞 Support

Need help? Here's how to get support:

- **Documentation** - Check the relevant guide in this docs folder
- **GitHub Issues** - Report bugs or request features
- **Configuration Help** - See the [Configuration Reference](../api/config-reference.md)

---

**Happy automating!** 🤖✨
