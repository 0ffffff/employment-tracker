# employment tracker

A CLI tool for tracking job applications. Supports multiple resumes, job updates, etc.

## Installation

If you don't have `uv` installed, this script will also install that for you.
```bash
curl -fsSL https://0ffffff.github.io/install.sh | bash
```

Your data lives locally in `~/.track/`, created automatically from installation.

## Usage

```bash
# Resumes
track add-resume "2027-default" ./resume.pdf
# -> Registered resume #1 as latest.

# Applications (latest resume if -r omitted; status ghost; applied_date today)
track add "Acme SWE Intern"
track add "Globex Data Intern" -r "2027-default"

# Status update (ID or fuzzy role_text >=85; confirm unless -f)
track update 1 interviewing
track update "Acme SWE Intern" i -f

# Lists (human: 5-row preview; --all for full table; JSON: full set)
track list
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
| `u` | `update` |

## Updates

I'll probably be adding functionality to delete resumes/applications and other QoL changes soon. Also on the list is data analytics, so being able to see how jobless you are :>
