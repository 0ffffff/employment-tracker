# employment tracker

A CLI tool for tracking job applications. Supports multiple resumes, job updates, etc.

## Installation

If you don't have `uv` installed, this script will also install that for you.
```bash
curl -fsSL https://0ffffff.github.io/install.sh | bash
```

Your data lives locally in `~/.track/`, created automatically from installation. The applications are stored in a SQLite database, while your resumes are copied from the path you provide as reference when running `track add-resume`. If there's a new update, just rerun the install script; your current data will be saved.

## Usage

```bash
# Resumes
track add-resume "2027-default" ./resume.pdf
# -> Registered resume #1 as latest.
track add-resume "default-2" ./resume-2.pdf
# -> Registered resume #2 as latest.
track set-latest-resume "2027-default"
# Switches default resume back to "2027-default"

# Applications
# Attaches latest resume with default status of "ghost" (no reply)
track add "Acme SWE Intern"
# Associate a specific registered resume to this application
track add "Globex Data Intern" -r "2027-default"

# Status updates
# Update via application ID
track update 1 interviewing
# or by name (supports fuzzy matching; identifiers are case-insensitive)
track update "Acme SWE Intern" i -f

# Lists (human: 5-row preview; --all for full table; JSON: full set)
track list
track list google
track list --json --status i
track list-resume --json --all
```

Statuses that are currently available: `ghost`/`g`, `reject`/`r`, `interviewing`/`i`, `offer`/`o`, `accepted`/`a`

You can also use subcommand aliases:

| Alias | Command |
|-------|---------|
| `a` | `add` |
| `ar` | `add-resume` |
| `ls` | `list` |
| `lr` | `list-resume` |
| `slr` | `set-latest-resume` |
| `u` | `update` |

## Updates

- [ ] delete resume functionality
- [ ] delete applications functionality
- [ ] various QoL improvements
- [ ] colored output
- [ ] data analytics (e.g. view your application/job stats)
- [ ] export data to csv, json, etc.
