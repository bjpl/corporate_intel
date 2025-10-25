# Bug Report Template

Copy this template to create new bug reports. Save as: `bugs/bug-YYYY-MM-DD-[short-description].md`

---

# Bug: [Short, Descriptive Title]

**Bug ID**: BUG-[YYYYMMDD]-[##] (e.g., BUG-20251024-01)
**Date Reported**: YYYY-MM-DD
**Reported By**: [Your Name]
**Status**: Open / In Progress / Fixed / Closed / Won't Fix
**Severity**: Critical / High / Medium / Low

---

## Summary
[One or two sentences describing the bug]

---

## Environment
- **OS**: [e.g., Ubuntu 22.04, macOS 14, Windows 11]
- **Browser**: [e.g., Chrome 119, Firefox 120] (if applicable)
- **Python Version**: [e.g., 3.11.5]
- **API Version**: [e.g., v1]
- **Database**: [e.g., PostgreSQL 15.3]
- **Commit Hash**: [e.g., abc123]
- **Branch**: [e.g., main, claude/user-testing-setup-011CUSdTMeS1Yrs6YmHtSNC8]

---

## Steps to Reproduce

1. [First step]
2. [Second step]
3. [Third step]
4. [And so on...]

**Example:**
1. Navigate to http://localhost:8000/api/v1/docs
2. Click on "POST /api/v1/auth/register"
3. Enter email: "test@example.com" and password: "123"
4. Click "Execute"

---

## Expected Behavior
[What you expected to happen]

**Example:**
The API should return a 400 Bad Request with a validation error message stating "Password must be at least 8 characters long."

---

## Actual Behavior
[What actually happened]

**Example:**
The API returns a 500 Internal Server Error with message "Server encountered an unexpected condition."

---

## Screenshots/Videos
[Attach screenshots, screen recordings, or paste images here]

**Screenshots:**
- [Describe screenshot 1]
- [Describe screenshot 2]

**Screen Recording:**
- [Link to video or attach file]

---

## Logs/Error Messages

### API Logs
```
[Paste relevant API logs here]
```

### Browser Console Errors (if applicable)
```javascript
// Paste JavaScript console errors here
```

### Database Logs (if applicable)
```
[Paste relevant database logs here]
```

### Stack Trace
```python
# Paste full stack trace here
Traceback (most recent call last):
  File "...", line X, in function_name
    ...
```

---

## Impact

### User Impact
- **Who is affected?**: [All users / Admin users / Specific user types]
- **How many users?**: [Estimate: All / Many / Some / Few]
- **Frequency**: [Always / Often / Sometimes / Rarely]
- **Workaround available?**: [Yes/No - describe if yes]

### Business Impact
- [ ] Blocks critical functionality
- [ ] Causes data loss or corruption
- [ ] Security vulnerability
- [ ] Performance degradation
- [ ] Poor user experience
- [ ] Minor inconvenience

**Description:**
[Explain the business/user impact in 2-3 sentences]

---

## Severity Classification

### Critical
- [ ] Application crashes or is completely unusable
- [ ] Data loss or corruption occurs
- [ ] Security vulnerability that exposes sensitive data
- [ ] System is down or inaccessible

### High
- [ ] Major feature doesn't work as intended
- [ ] Blocks important user workflows
- [ ] No workaround available
- [ ] Affects many users

### Medium
- [ ] Feature works but has significant issues
- [ ] Workaround is available but inconvenient
- [ ] Affects some users
- [ ] Performance issues that don't block usage

### Low
- [ ] Minor UI/UX issue
- [ ] Cosmetic problem
- [ ] Typo or formatting issue
- [ ] Rare edge case
- [ ] Affects very few users

---

## Root Cause Analysis (if known)

### Likely Cause
[Your hypothesis about what's causing the bug]

### Relevant Code
**File**: `src/path/to/file.py:123`
```python
# Paste relevant code snippet here
def problematic_function():
    # This line might be the issue
    result = some_operation()
```

### Related Issues
- Related to Bug #XYZ: [Link or description]
- May be caused by recent change in commit: [hash]

---

## Suggested Fix (optional)
[If you have ideas about how to fix this, describe them here]

**Example:**
```python
# Instead of:
if password:
    validate_password(password)

# Should be:
if password and len(password) >= 8:
    validate_password(password)
else:
    raise ValueError("Password must be at least 8 characters long")
```

---

## Additional Context

### Related Documentation
- [Link to relevant documentation]
- [Link to API spec]
- [Link to design document]

### Similar Issues
- GitHub Issue #123
- Previous Bug Report: BUG-20251020-03

### Testing Notes
- [Any additional information that might help debug]
- [Relevant test data]
- [Configuration specifics]

---

## Reproducibility

- [ ] Reproduced 100% of the time
- [ ] Reproduced most of the time (>50%)
- [ ] Reproduced sometimes (<50%)
- [ ] Only reproduced once
- [ ] Cannot reproduce

**Attempts**: Reproduced X out of Y attempts

---

## Fix Verification (to be filled after fix)

### Fix Applied
- **Date Fixed**: YYYY-MM-DD
- **Fixed By**: [Name]
- **Commit**: [hash]
- **Pull Request**: #[number]

### Verification Steps
1. [Step to verify fix]
2. [Step to verify fix]
3. [Confirm bug no longer occurs]

### Verified By
- [ ] Original reporter verified
- [ ] QA team verified
- [ ] Automated test added

**Verification Date**: YYYY-MM-DD
**Verified By**: [Name]

---

## Notes
[Any additional notes, comments, or discussion]

---

## Checklist

Before submitting this bug report:
- [ ] Reproduced the bug at least twice
- [ ] Checked if bug already reported
- [ ] Filled all required sections
- [ ] Attached screenshots/logs
- [ ] Assigned appropriate severity
- [ ] Tagged relevant team members (if applicable)

---

## Tags/Labels
`authentication` `api` `database` `ui` `performance` `security` `data-quality`

---

## Example Bug Report

Here's a filled-out example:

---

# Bug: Password Validation Allows Weak Passwords

**Bug ID**: BUG-20251024-01
**Date Reported**: 2025-10-24
**Reported By**: Test User
**Status**: Open
**Severity**: High

## Summary
The user registration endpoint accepts passwords shorter than 8 characters, which violates the stated security policy and allows users to create weak passwords.

## Environment
- **OS**: Ubuntu 22.04
- **Browser**: Chrome 119
- **Python Version**: 3.11.5
- **API Version**: v1
- **Commit Hash**: 89cdea7

## Steps to Reproduce
1. Send POST request to http://localhost:8000/api/v1/auth/register
2. Use email: "test@example.com"
3. Use password: "123" (only 3 characters)
4. Submit the request

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"123","full_name":"Test User"}'
```

## Expected Behavior
The API should return a 422 Validation Error with message: "Password must be at least 8 characters long and contain uppercase, lowercase, and numbers."

## Actual Behavior
The API returns 201 Created and successfully creates the user account with the weak password.

## Screenshots/Videos
[Screenshot showing successful registration with "123" as password]

## Logs/Error Messages

### API Logs
```
INFO: POST /api/v1/auth/register - 201 Created
User created: test@example.com
```

No error logged - validation was not triggered.

## Impact

### User Impact
- **Who is affected?**: All new users
- **How many users?**: Potentially all registrations
- **Frequency**: Always (100% reproducible)
- **Workaround available?**: No (security policy not enforced)

### Business Impact
- [x] Security vulnerability
- [x] Blocks critical functionality (security requirement)
- [ ] Causes data loss or corruption
- [ ] Poor user experience

**Description:**
This is a security issue that allows users to create accounts with weak passwords, making accounts vulnerable to brute force attacks. This violates security best practices and may fail compliance requirements.

## Severity Classification
- [ ] Critical
- [x] High - Security vulnerability that should be fixed before production
- [ ] Medium
- [ ] Low

## Root Cause Analysis

### Likely Cause
The password validation in `src/auth/schemas.py` is missing or not being applied to the registration endpoint.

### Relevant Code
**File**: `src/auth/schemas.py:15`
```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str  # No validation here!
    full_name: str
```

Should have Pydantic validators or use a custom validator function.

## Suggested Fix

```python
from pydantic import validator
import re

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v
```

## Additional Context
- Security policy documented in: docs/security-requirements.md
- OWASP password guidelines: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html

## Reproducibility
- [x] Reproduced 100% of the time
- [ ] Reproduced most of the time
- [ ] Reproduced sometimes
- [ ] Only reproduced once

**Attempts**: Reproduced 5 out of 5 attempts

## Notes
This should be fixed before any production deployment. Also need to add automated tests to prevent regression.

## Tags/Labels
`authentication` `security` `validation` `high-priority`

---
