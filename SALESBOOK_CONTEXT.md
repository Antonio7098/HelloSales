# Salesbook Onboarding Module — Context

## What this branch adds
- Multi-step onboarding flow (4 steps: identity → industry → challenges → goals)
- Salesbook CRUD (chapters, objections, VP stack)
- Google Sheets webhook sync for lead capture
- Frontend UI in frontend-draft/

## Branch: feature/Oliviercontribution
## Author: Olivier (HelloSalesGreki)
## For review by: Anto — May 3rd meeting

## Architecture decisions
- Uses scaffold_module.py for backend module creation
- Follows existing async SQLAlchemy patterns
- All new routes registered via existing entrypoints/http pattern
- Frontend built in frontend-draft/ (not frontend/)
- Design system: IBM Plex Mono, black/white, no color decoration
