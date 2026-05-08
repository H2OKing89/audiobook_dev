# 📚 Audiobook Automation Documentation

Welcome to the comprehensive documentation for the Audiobook Automation System! This documentation is organized to help both users and developers understand, use, and contribute to the system.

## Quick Start

New to the system? Start here:

1. [Getting Started](user-guide/getting-started.md) - Installation and basic setup
2. [Configuration](user-guide/configuration.md) - Configure the system for your needs
3. [Web Interface](user-guide/web-interface.md) - Using the web UI

## Documentation Structure

### 🎯 User Guide (`user-guide/`)

Documentation for end users who want to use the audiobook automation system.

- **[Getting Started](user-guide/getting-started.md)** - Installation, setup, and first run
- **[Configuration](user-guide/configuration.md)** - Configuration options and examples
- **[Web Interface](user-guide/web-interface.md)** - Using the web UI for approvals and monitoring
- **[Notifications](user-guide/notifications.md)** - Setting up Discord, Pushover, etc.
- **[Troubleshooting](user-guide/troubleshooting.md)** - Common issues and solutions

### 🛠️ Development (`development/`)

Documentation for developers who want to understand, modify, or contribute to the codebase.

- **[Architecture](development/architecture.md)** - System architecture and design overview
- **[Security](development/SECURITY.md)** - Security considerations and best practices
- **[Testing](development/testing.md)** - Testing strategies, test suite, and guidelines
- **[Contributing](development/contributing.md)** - How to contribute to the project

### 🔌 API Reference (`api/`)

Technical API documentation for integrations and advanced usage.

- **[REST API](api/rest-api.md)** - HTTP API endpoints and examples
- **[Configuration Reference](api/config-reference.md)** - Complete configuration options

## 🎯 Key Features Documented

### ✅ Core System

- **Audiobook Request Processing** - Automated processing of audiobook requests
- **MAM Integration** - MyAnonaMouse scraping and ASIN extraction
- **Metadata Enrichment** - Audnex and Audible metadata fetching
- **Web Interface** - Modern approval/rejection interface
- **Security** - CSRF protection, rate limiting, input validation

### ✅ Advanced Features

- **Rate Limiting** - Configurable API rate limiting (30s test, 120s production)
- **Fallback Systems** - Multiple metadata sources with intelligent fallbacks
- **Notification Systems** - Discord, Pushover, Gotify, NTFY support
- **Webhook Integration** - Autobrr and other webhook sources

## 📊 System Status

- ✅ **Production Ready** - All core features tested and working
- ✅ **Security Audited** - Comprehensive security testing completed
- ✅ **Well Tested** - Full test suite with real data validation
- ✅ **Documented** - Complete documentation for users and developers

## 🔗 External Resources

- **MyAnonaMouse** - Primary torrent source for audiobooks
- **Audnex API** - Rich audiobook metadata and chapter information
- **Audible API** - Fallback metadata source

## 📁 Archive

Historical development documentation and implementation logs are stored in `archive/` for reference but are not part of the current documentation.

---

**Last Updated**: May 6, 2026
**System Version**: Production v1.0

- [Database Schema](api/database.md) - Database structure
- [Configuration Reference](api/config-reference.md) - Complete configuration options

## 🚀 Quick Links

- **[Installation Guide](user-guide/getting-started.md#installation)** - Get up and running quickly
- **[Configuration Examples](user-guide/configuration.md#examples)** - Common configuration scenarios
- **[API Documentation](api/rest-api.md)** - For developers integrating with the system
- **[Troubleshooting](user-guide/troubleshooting.md)** - When things go wrong

## 🤖 About This System

This audiobook automation system was built by Quentin with the philosophy of "maximum automation, minimum manual intervention." It handles:

- **Automated Approval Workflows** - Smart request processing
- **Multi-platform Notifications** - Discord, Gotify, Ntfy, Pushover
- **Security-First Design** - Token-based authentication, CSP compliance
- **Modern Web Interface** - Beautiful, responsive UI with personality
- **Comprehensive Logging** - Detailed audit trails and debugging

## 📝 Documentation Standards

All documentation in this project follows these standards:

- **Clear Structure** - Organized sections with logical flow
- **Practical Examples** - Real-world usage scenarios
- **Up-to-date** - Regularly maintained and current
- **Accessible** - Written for both beginners and experts
- **Searchable** - Well-indexed with consistent terminology

**Need help?** Check the [troubleshooting guide](user-guide/troubleshooting.md) or open an issue on GitHub!
