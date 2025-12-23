# 🤝 Contributing to Audiobook Automation

Thank you for your interest in contributing! This guide will help you get started with contributing to the Audiobook Automation System.

## 🌟 Ways to Contribute

### 🐛 Bug Reports

- Report bugs through GitHub Issues
- Include detailed reproduction steps
- Provide system information and logs
- Check existing issues before creating new ones

### 💡 Feature Requests

- Suggest new features or improvements
- Explain the use case and benefit
- Consider implementation complexity
- Discuss with maintainers first for major features

### 📝 Documentation

- Improve existing documentation
- Add missing documentation
- Fix typos and formatting
- Translate documentation

### 💻 Code Contributions

- Fix bugs and implement features
- Improve performance and reliability
- Add tests for new functionality
- Follow coding standards

## 🛠️ Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub first
git clone https://github.com/YOUR_USERNAME/audiobook-automation.git
cd audiobook-automation
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If it exists

# Install pre-commit hooks
pre-commit install
```

### 3. Configure for Development

```bash
# Copy example configs
cp config/config.yaml.example config/config.yaml
cp .env.example .env

# Configure for development
# Edit config.yaml to set:
# server.debug: true
# metadata.rate_limit_seconds: 30  # Faster testing
```

### 4. Run Tests

```bash
# Run the test suite
python tests/test_metadata_workflow.py
python tests/test_mam_integration.py

# Run specific tests
python test_mam_login.py
python test_audnex_direct.py
```

## 📋 Development Guidelines

### Code Style

- Follow PEP 8 Python style guide
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Use type hints where helpful

### Testing

- Write tests for new features
- Ensure existing tests pass
- Test with real data when possible
- Include edge cases in tests
- Document test scenarios

### Security

- Never commit sensitive data (tokens, passwords)
- Validate all user inputs
- Use parameterized queries for database operations
- Follow security best practices
- Report security issues privately

### Documentation

- Update documentation for new features
- Include code examples in docs
- Keep README up to date
- Document configuration changes
- Use clear, concise language

## 🔄 Development Workflow

### 1. Create Feature Branch

```bash
# Create branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write clean, focused commits
- Test your changes thoroughly
- Update documentation as needed
- Ensure code follows style guidelines

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with clear message
git commit -m "feat: add new metadata source integration

- Add support for LibriVox API
- Include rate limiting for new source
- Update configuration documentation
- Add tests for new functionality"
```

### 4. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
# Include description of changes
# Link related issues
# Request review from maintainers
```

## 🧪 Testing Guidelines

### Test Categories

#### Unit Tests

- Test individual functions and classes
- Mock external dependencies
- Fast execution
- High coverage of core logic

#### Integration Tests

- Test component interactions
- Use real configurations
- Test with sample data
- Verify workflows end-to-end

#### System Tests

- Test full system functionality
- Use real external APIs (carefully)
- Test with production-like data
- Verify performance characteristics

### Test Organization

```
tests/
├── test_metadata_workflow.py     # Core workflow tests
├── test_mam_integration.py       # MAM integration tests
└── unit/                         # Unit tests by module
    ├── test_config.py
    ├── test_database.py
    └── test_security.py
```

### Running Tests

```bash
# Run all production tests
python tests/test_metadata_workflow.py
python tests/test_mam_integration.py

# Run development/debug tests
python test_mam_login.py
python test_audnex_direct.py

# Run with pytest (if configured)
pytest tests/
```

## 🏗️ Architecture Guidelines

### Module Organization

- Keep modules focused and cohesive
- Use clear interfaces between modules
- Minimize dependencies between modules
- Follow separation of concerns

### Configuration Management

- Use YAML for main configuration
- Use environment variables for secrets
- Provide example configurations
- Validate configuration on startup

### Error Handling

- Use appropriate exception types
- Log errors with context
- Provide helpful error messages
- Graceful degradation when possible

### Performance Considerations

- Respect API rate limits
- Cache expensive operations
- Use async operations where beneficial
- Monitor resource usage

## 📦 Release Process

### Version Management

- Use semantic versioning (major.minor.patch)
- Tag releases in git
- Maintain CHANGELOG.md
- Document breaking changes

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Configuration examples current
- [ ] Security review completed
- [ ] Performance testing done
- [ ] Breaking changes documented

## 🐛 Debugging Tips

### Common Issues

- **Import errors**: Check virtual environment activation
- **Config errors**: Verify file format and required fields
- **Database issues**: Check file permissions and locks
- **API timeouts**: Verify network connectivity and rate limits

### Debugging Tools

```bash
# Enable debug logging
# Set in config.yaml: server.debug: true

# View real-time logs
tail -f logs/audiobook_requests.log

# Check database state
sqlite3 db.sqlite ".tables"

# Test individual components
python -c "from src.config import load_config; print(load_config())"
```

### Development Helpers

```bash
# Quick restart during development
pkill -f "python.*main.py" && python src/main.py

# Reset database for testing
rm db.sqlite && python src/db.py

# Test configuration
python -c "from src.config import validate_config; validate_config()"
```

## 📞 Getting Help

### Before Asking for Help

1. Check existing documentation
2. Search closed issues and PRs
3. Try debugging steps above
4. Prepare minimal reproduction case

### Where to Get Help

- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - Questions and community help
- **Documentation** - Comprehensive guides and references

### Providing Good Reports

Include:

- Clear description of issue or goal
- Steps to reproduce problem
- Expected vs actual behavior
- System information (OS, Python version)
- Relevant log excerpts (without secrets)
- Configuration details (sanitized)

## 🎯 Contribution Ideas

### Good First Issues

- Fix typos in documentation
- Improve error messages
- Add configuration validation
- Write additional tests
- Improve logging output

### Advanced Contributions

- Add new metadata sources
- Implement new notification channels
- Improve web interface
- Add performance monitoring
- Enhance security features

## 📜 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow project guidelines
- Report inappropriate behavior

Thank you for contributing to the Audiobook Automation System! Your contributions help make this tool better for everyone.
