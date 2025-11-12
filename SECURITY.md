# Security Policy

## Supported Versions

Currently supported versions of PySDL:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of PySDL seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Reporting Process

**Please do not report security vulnerabilities through public GitHub/GitLab issues.**

Instead, please report them via email to:
- **Email**: shenning_00@yahoo.com
- **Subject Line**: [SECURITY] PySDL Vulnerability Report

### What to Include

Please include the following information in your report:
- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability, including how an attacker might exploit it

### What to Expect

- **Acknowledgment**: You should receive an acknowledgment within 48 hours
- **Initial Assessment**: We will send an initial assessment within 5 business days
- **Updates**: We will keep you informed of progress towards a fix
- **Public Disclosure**: We will coordinate public disclosure with you

### Safe Harbor

We support safe harbor for security researchers who:
- Make a good faith effort to avoid privacy violations, data destruction, and service disruption
- Only interact with accounts you own or with explicit permission from the account holder
- Do not exploit a security issue you discover for any reason

## Security Considerations

PySDL is designed with the following security considerations:

### No External Dependencies
- PySDL has zero external dependencies
- Minimal attack surface from third-party code

### No Network Operations
- Core library performs no network I/O
- Applications control all external communication

### Type Safety
- Comprehensive type hints throughout
- mypy type checking in CI/CD
- Reduces runtime type errors

### Input Validation
- ValidationError raised for invalid inputs
- Process and signal type checking
- Timer parameter validation

### Best Practices for Users

When using PySDL in your applications:

1. **Validate External Inputs**: Always validate data from external sources before creating signals
2. **Limit Signal Data**: Don't include sensitive data in signal payloads unless encrypted
3. **Process Isolation**: Use separate SdlSystem instances for security boundaries
4. **Error Handling**: Properly handle ValidationError and other exceptions
5. **Logging**: Be cautious about logging sensitive signal data

## Known Limitations

- PySDL is single-threaded (asyncio event loop)
- No built-in authentication or authorization
- No built-in encryption for signal data
- Applications must implement their own security controls

## Security Updates

Security updates will be released as patch versions and announced via:
- GitLab release notes
- CHANGELOG.md updates
- Email notification to reporters

---

Thank you for helping keep PySDL and its users safe!
