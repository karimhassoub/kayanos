# KayanOS Development Roadmap

## Project Phases and Approval Gates (Mandatory Approval Gates)

| Phase | Description | Status |
|---|---|---|
| **Phase 0** | Foundation & Operations (Setup Frappe v16, Dashboard) | `ACCEPTED` |
| **Phase 1** | Core & Integration Readiness (Audit, Map, Shared Infra) | `ACCEPTED` |
| **Phase 2** | Canonical Project Integration (Link CRM to BuildSuite Project) | `VALIDATION` |
| **Phase 3** | Real Estate Domain (Property/Unit modeling) | `NOT STARTED` |
| **Phase 4** | CRM & Sales Integration (Link Opportunity to Unit/Project) | `NOT STARTED` |
| **Phase 5** | Booking, Contracts & Payment Plans | `NOT STARTED` |
| **Phase 6** | ERPNext & BuildSuite Financial Integration (Invoicing, Ledger) | `NOT STARTED` |
| **Phase 7** | Customer Support & Ticketing (Helpdesk integration) | `NOT STARTED` |
| **Phase 8** | Customer Portal & APIs | `NOT STARTED` |
| **Phase 9** | Production Readiness (Security, Upgrade Safety, Backup) | `NOT STARTED` |

## Architecture & Integration Decisions
1. **Projects**: `Project` DocType from BuildSuite/ERPNext will be the single source of truth. No duplicate project entities in KayanOS.
2. **Sales**: Frappe CRM `CRM Deal` and `CRM Lead` will be used. They will be linked to the KayanOS units.
3. **Customizations**: Any modifications to ERPNext, CRM, or BuildSuite DocTypes must be Upgrade-safe via Custom Fields or Property Setters in KayanOS.

## Quality Gates
- **G1**: Integration Map approved, audit documented.
- **G2**: Opportunity correctly links to existing Project without duplicates.
- **G3**: BuildSuite Project can have units attached and availability tracked.
- **G4**: Lead to Opportunity to Unit assignment tested end-to-end.
- **G5**: Booking and contract flow generates correct statuses without overlapping.
- **G6**: Financial documents generated match ERPNext accounting correctly.
- **G7**: Helpdesk ticket linked correctly to unit/customer.
- **G8**: Customer Portal securely displays isolated data.
- **G9**: Successful installation/upgrade testing on a clean site.
