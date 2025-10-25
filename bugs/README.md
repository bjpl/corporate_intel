# Bug Reports Directory

This directory contains all bug reports discovered during user testing.

## File Naming Convention

Bug reports should be named using the following format:
```
bug-YYYYMMDD-[short-description].md
```

**Examples:**
- `bug-20251024-password-validation.md`
- `bug-20251024-api-500-error.md`
- `bug-20251025-dashboard-loading.md`

## Bug ID Convention

Each bug should have a unique ID:
```
BUG-YYYYMMDD-##
```

**Examples:**
- `BUG-20251024-01` - First bug found on Oct 24, 2025
- `BUG-20251024-02` - Second bug found on Oct 24, 2025

## Creating a Bug Report

1. Copy the template from `../BUG_REPORT_TEMPLATE.md`
2. Create a new file in this directory with the naming convention above
3. Fill out all sections of the template
4. Save the file
5. Reference the bug in your testing notes

## Quick Create Command

```bash
# Create a new bug report
cp ../BUG_REPORT_TEMPLATE.md bugs/bug-$(date +%Y%m%d)-[description].md
```

## Bug Severity Levels

- **Critical**: App crashes, data loss, security vulnerability, system down
- **High**: Major feature broken, blocks workflows, no workaround
- **Medium**: Feature works but has issues, workaround available
- **Low**: Minor UI/UX issues, cosmetic problems, rare edge cases

## Bug Workflow

1. **Open**: Bug discovered and documented
2. **In Progress**: Bug is being investigated/fixed
3. **Fixed**: Fix has been applied
4. **Verified**: Fix has been tested and confirmed
5. **Closed**: Bug is resolved and closed
6. **Won't Fix**: Bug acknowledged but won't be fixed (with reason)

## Bug Tracking

Track all bugs in `../TESTING_NOTES.md` and reference them here.

Example:
```markdown
## Bugs Found
- BUG-20251024-01: Password validation allows weak passwords - High
  - File: bugs/bug-20251024-password-validation.md
  - Status: Fixed
  - Verified: 2025-10-25
```

## Viewing All Bugs

```bash
# List all bug reports
ls -la bugs/

# Count bugs by severity
grep -r "Severity: Critical" bugs/ | wc -l
grep -r "Severity: High" bugs/ | wc -l
grep -r "Severity: Medium" bugs/ | wc -l
grep -r "Severity: Low" bugs/ | wc -l

# List open bugs
grep -r "Status: Open" bugs/ -l
```

## Example Bug Report Files

Once you start testing, this directory will contain files like:
```
bugs/
├── README.md (this file)
├── bug-20251024-password-validation.md
├── bug-20251024-api-timeout.md
├── bug-20251025-dashboard-chart-error.md
└── bug-20251025-metric-calculation.md
```

## Important Notes

- Always reproduce a bug at least twice before filing
- Include detailed steps to reproduce
- Attach screenshots or logs when possible
- Assign appropriate severity
- Link related bugs
- Update status as bugs are fixed

## Getting Help

- Review the bug template: `../BUG_REPORT_TEMPLATE.md`
- Check testing guide: `../USER_TESTING_GUIDE.md`
- See testing checklist: `../USER_TESTING_CHECKLIST.md`

---

**Ready to start finding bugs? Copy the template and get testing!** 🐛🔍
