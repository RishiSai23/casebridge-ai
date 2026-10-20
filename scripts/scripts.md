# Scripts Directory (`scripts/`)

## A. Purpose
The `scripts/` directory hosts repository maintenance, automation, CI verification, and developer utility scripts that support CaseBridge AI development, code quality, and documentation synchronization.

## B. Directory tree
```
scripts/
├── scripts.md                 # Navigation documentation for the scripts directory
└── validate_navigation.py     # Automated validation script for AGENTS.md, progress.md, and directory documentation
```

## C. File inventory
| File | Responsibility |
|---|---|
| `scripts.md` | Documents the scripts directory structure, responsibilities, and execution conventions. |
| `validate_navigation.py` | Automated audit script that checks existence, required sections, file inventories, and link validity for all repository navigation documents. |

## D. Subdirectory inventory
There are currently no subdirectories in `scripts/`.

## E. Relationships and dependencies
- `validate_navigation.py` audits all directory Markdown files, [AGENTS.md](../AGENTS.md), and [progress.md](../progress.md).
- Scripts in this directory run against the standard Python runtime without requiring third-party library installations beyond the standard library.

## F. Development and verification
Execute the validator from the repository root:
```powershell
python scripts/validate_navigation.py
```

## G. Maintenance notes
- All scripts in this directory must be executable with standard Python 3.10+ without heavy external dependencies where possible.
- Any newly added script must be listed in the File inventory above and have its purpose documented.
