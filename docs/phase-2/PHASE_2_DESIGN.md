# Phase 2: Canonical Project Integration Design (Final Clarifications)

## 1. Executive Summary
This document provides an evidence-based design for KayanOS Phase 2. The core objective is to integrate real-estate-specific data safely with the upstream ERPNext/BuildSuite `Project` and Frappe CRM (`CRM Deal`, `CRM Lead`). The proposed design relies on minimal, upgrade-safe `custom_fields` injections to bridge the relationships, coupled with a KayanOS-owned `RE Project Profile` to encapsulate domain-specific configurations. 

**Status:** IN PROGRESS — DISCOVERY & DESIGN ONLY (Not Approved for Implementation).

## 2. Phase 1 Acceptance Record
* **Phase 1 Status:** ACCEPTED
* **Acceptance Basis:** Explicit product-owner approval documented in the roadmap.

## 3. Verified Environment and App Versions
* Bench: `~/frappe-bench`, Site: `kayanos.localhost`
* frappe (16.34.0), erpnext (16.35.0), crm (2.0.0-dev), buildsuite_core (0.0.1)

## 4. Canonical Project Integration (1-to-1 Mapping)
* **Canonical Record:** The ERPNext/BuildSuite `Project` remains the ONLY project record. KayanOS will NOT duplicate this.
* **RE Project Profile (PROPOSED):** A custom KayanOS DocType that links exactly 1-to-1 with the canonical `Project`.
* **1-to-1 Enforcement Mechanism:**
  1. The `project` Link field in `RE Project Profile` will be marked as **Mandatory** and **Unique**. Frappe natively enforces uniqueness at the database schema level (UNIQUE constraint).
  2. **[NOT VERIFIED]** A Python `validate` controller hook on `RE Project Profile` will act as a secondary check to prevent duplicate creation. (Requires runtime testing during implementation).
* **Deletion Prevention:** By default, Frappe v16 natively throws a `LinkExistsError` when attempting to delete a document (e.g., `Project`) that is referenced by a `Link` field. **[NOT VERIFIED]** We will rely on this native referential integrity check but will define a specific duplicate-prevention and deletion-integrity test during implementation.

## 5. CRM Deal / Lead Relationship
* **CRM Lead:** Represents initial project interest.
* **CRM Deal:** Represents an active sales transaction.
* **Integration Strategy:** We will inject an optional custom link field (`kayanos_project`) into **BOTH** `CRM Lead` and `CRM Deal`. 
* **Lead-to-Deal Conversion:** **[NOT VERIFIED]** Frappe CRM has a conversion logic to turn a Lead into a Deal. We must test whether a custom field carries over natively. If it does not, a custom hook or map must be defined.
* **MVP Limitation:** One project per Lead/Deal. Multi-project interest is documented as a future consideration.

## 6. Operating Company & Project Ownership
* **Operating Company:** Explicitly defining an `operating_company` Link to `Company` in `RE Project Profile` is required. This explicitly handles multi-company environments without falling back to a global system default.
* **Ownership Classification:** 
  * `ownership_type` (Select: "Internal", "External"). Explicit distinction avoiding ambiguous empty fields.
  * `developer_type` (Select: "Customer", "Supplier", "Company").
  * `external_developer` (Dynamic Link based on `developer_type`). 
  * *Limitation Notes:* Customers and Suppliers are distinct ledgers in ERPNext. Dynamic Link provides flexibility, but accounting boundaries (A/R vs A/P) must be respected in Phase 6.

## 7. Clarifying Responsibilities and Distinctions
The `RE Project Profile` separates operational roles as independent capability flags. These flags dictate what KayanOS permits the company to do, but they are NOT legal contracts:
* **Sales Authorization (`sales_authorized`):** A boolean capability flag indicating whether the Operating Company is authorized to market/sell units. (Detailed sales mandates belong in Phase 5).
* **Construction Responsibility (`construction_responsible`):** A boolean capability flag indicating whether the Operating Company is acting as the general contractor. (Detailed construction scopes and contracts belong in later phases).

## 8. Proposed Fields and Relationships

### Target: `CRM Lead` & `CRM Deal` (Frappe CRM)
| Field | Purpose | Proposed Type | Required? | Reason |
| --- | --- | --- | --- | --- |
| `kayanos_project` | Canonical Project Ref | Link (`Project`) | No | Allows Sales to tie a lead/deal to a specific project. |

### Target: `RE Project Profile` (PROPOSED NEW IN KAYANOS)
| Field | Purpose | Proposed Type | Required? | Reason |
| --- | --- | --- | --- | --- |
| `project` | Canonical Project Ref | Link (`Project`) | Yes | The single source of truth. Must be **Unique**. |
| `operating_company`| KayanOS Company | Link (`Company`) | Yes | Supports Multi-Company clarity. |
| `ownership_type` | Internal vs External | Select | Yes | Avoids ambiguous blanks. |
| `developer_type` | Party Type | Select | No | Allows Customer, Supplier, or Company. |
| `external_developer` | External Owner | Dynamic Link | No | The actual owner entity. |
| `sales_authorized` | Marketing Rights | Check | No | Independent capability flag. |
| `construction_responsible`| Construction Rights | Check | No | Independent capability flag. |

## 9. Scenario-Based Validation Matrix
### Scenario A — Our Own Development
* **Operating Company:** Legal Entity A.
* **Ownership:** "Internal" (`external_developer` left blank). 
* **Role Flags:** `sales_authorized` = 1, `construction_responsible` = 1.
### Scenario B — External Developer Sales
* **Operating Company:** Legal Entity A.
* **Ownership:** "External" (`external_developer` linked to a Supplier/Customer). 
* **Role Flags:** `sales_authorized` = 1, `construction_responsible` = 0.
### Scenario C — External Construction Management
* **Operating Company:** Legal Entity A.
* **Ownership:** "External". 
* **Role Flags:** `sales_authorized` = 0, `construction_responsible` = 1.
### Scenario D — Mixed Engagement
* Both flags set dynamically per project.

## 10. Upgrade-Safety & Risks Analysis
* **Realistic Risks:** Upstream (Frappe/ERPNext/CRM) could change doctype names or introduce a core field named `kayanos_project`.
* **Mitigations:** We prefix custom fields with `kayanos_`. Custom fields are managed via `kayanos/hooks.py`, avoiding manual DB schema conflicts during migrations.

## 11. Acceptance Criteria for Implementation
1. `RE Project Profile` enforces a strict 1-to-1 relationship with `Project` (Duplicate creation fails, deletion integrity is proven).
2. Operating Company and Project Ownership (Internal vs External) are explicitly defined.
3. `CRM Lead` and `CRM Deal` optionally link to `Project`, and Lead-to-Deal conversion safely carries over the Project link (or handles it gracefully).
4. External developers can be assigned flexibly (Customer/Supplier/Company), respecting that these represent different ledgers.
5. Upstream apps remain unmodified in their source code.

## 12. Exact Evidence Sources
* `frappe.get_meta('Project').fields`
* `frappe.get_meta('CRM Deal').fields`
* `frappe.get_meta('CRM Lead').fields` (Verified during Discovery).
