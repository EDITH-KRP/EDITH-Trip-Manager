# EDITH-TRIP MANAGER

## Product Requirements Document (PRD)

**Document Version:** 2.0 (Complete Specification)  
**Product Type:** Private, Cloud-Hosted Web Application  
**Target Users:** Closed group of four friends (One Administrator/Organizer and three Group Members)  
**Primary Currency:** Indian Rupee (INR - ₹)  
**Status:** Approved & Finalized for Implementation  

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Problem Statement](#2-problem-statement)
3. [Goals and Success Criteria](#3-goals-and-success-criteria)
4. [Users, Roles, and Permission Matrix](#4-users-roles-and-permission-matrix)
5. [Functional Requirements](#5-functional-requirements)
   - [5.1 Savings Kitty (Group Fund Management)](#51-savings-kitty-group-fund-management)
   - [5.2 Kitty Split (Shared Trip Expenses)](#52-kitty-split-shared-trip-expenses)
   - [5.3 Common Kitty Expenses & Disbursements](#53-common-kitty-expenses--disbursements)
   - [5.4 Trip Planner & Itinerary Management](#54-trip-planner--itinerary-management)
   - [5.5 Dashboard & Overview](#55-dashboard--overview)
   - [5.6 Notification System](#56-notification-system)
6. [Access Control and Privacy Architecture](#6-access-control-and-privacy-architecture)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Technical Architecture](#8-technical-architecture)
   - [8.1 Technology Stack](#81-technology-stack)
   - [8.2 Project Structure](#82-project-structure)
   - [8.3 Database Collections Overview](#83-database-collections-overview)
9. [Key Business Rules & Accounting Invariants](#9-key-business-rules--accounting-invariants)
10. [Scope and Phased Release Plan](#10-scope-and-phased-release-plan)
11. [Out of Scope for Version 1](#11-out-of-scope-for-version-1)
12. [Core Acceptance Criteria](#12-core-acceptance-criteria)
13. [Risks, Failure Modes, and Mitigations](#13-risks-failure-modes-and-mitigations)
14. [System Assumptions & Baseline Parameters](#14-system-assumptions--baseline-parameters)
15. [Resolved Architectural & Operational Decisions](#15-resolved-architectural--operational-decisions)
16. [Implementation Status & Progress Baseline](#16-implementation-status--progress-baseline)
17. [Product Definition & Guiding Architectural Principles](#17-product-definition--guiding-architectural-principles)
18. [Detailed Database Schemas & Data Models](#18-detailed-database-schemas--data-models)
19. [Comprehensive REST API Specifications](#19-comprehensive-rest-api-specifications)
20. [Mathematical Models, Split Algorithms & Financial Integrity](#20-mathematical-models-split-algorithms--financial-integrity)
    - [20.1 Integer Minor-Unit Currency Representation](#201-integer-minor-unit-currency-representation)
    - [20.2 Deterministic Expense Splitting & Remainder Allocation](#202-deterministic-expense-splitting--remainder-allocation)
    - [20.3 Minimum Cash Flow Settlement Simplification Algorithm](#203-minimum-cash-flow-settlement-simplification-algorithm)
    - [20.4 Kitty Accounting Invariant & Reconciliation Formula](#204-kitty-accounting-invariant--reconciliation-formula)
21. [User Interface & Frontend Screen Specifications](#21-user-interface--frontend-screen-specifications)
22. [Indian DLT & SMS Gateway Integration Specifications](#22-indian-dlt--sms-gateway-integration-specifications)
23. [Security Architecture & Access Control Implementation](#23-security-architecture--access-control-implementation)
24. [Comprehensive Test Plan & Verification Matrix](#24-comprehensive-test-plan--verification-matrix)
25. [Cloud Infrastructure, Deployment & DevOps Runbook](#25-cloud-infrastructure-deployment--devops-runbook)
26. [Engineering Roadmap, Milestones & Definition of Done](#26-engineering-roadmap-milestones--definition-of-done)

---

## 1. Product Overview

**EDITH-TRIP MANAGER** is an exclusive, private web application engineered for a close-knit group of four friends to systematically save funds over a multi-month period, coordinate a complex multi-destination journey, record shared trip expenses with granular split configurations, and settle peer balances with absolute mathematical transparency.

The platform is designed around five interconnected modules:

1. **Savings Kitty:** Tracks mandatory recurring monthly contributions, submission of payment references (UTR), administrative verification, aggregate group savings progress against a predetermined financial target, authorized disbursements, and periodic bank/cash reconciliation.
2. **Kitty Split:** Manages day-to-day shared expenses paid out-of-pocket by individual members during the trip. Supports equal, exact, and percentage splits, dynamic balance calculations, and multi-party debt minimization settlements.
3. **Trip Planner:** Manages a chronological itinerary of up to 20 stops/destinations, tracking arrival/departure dates and times, transport arrangements, lodging confirmations, geo-coordinates/maps, and collaborative notes.
4. **Administration & Audit:** Provides the group administrator with fine-grained control over member accounts, contribution policies, target configurations, ledger adjustments, and an immutable log of all financial and system events.
5. **Notifications:** Delivers high-priority reminders, verification updates, and expense alerts directly to member phones via standard transactional SMS conforming to Indian regulatory standards.

> **Operational Boundary:** EDITH-TRIP MANAGER is an informational and accounting ledger. It tracks, verifies, and calculates financial movements. It does **not** operate as a payment gateway, mobile wallet, or custodian of fiat funds, nor does it initiate automated bank-to-bank transfers.

---

## 2. Problem Statement

Organizing a long-term group trip among close friends typically suffers from operational fragmentation:
- **Spreadsheet Degradation:** Spreadsheets become corrupt, lack strict data validation, suffer from accidental formula overwrites, and do not provide granular field-level privacy.
- **Privacy vs. Group Progress Conflict:** Group members want to know if the group is on track to hit its total savings goal, but individuals often desire privacy regarding their personal payment dates, delays, or temporary arrears.
- **Double-Counting and Ledger Pollution:** When common kitty funds are intermingled with personal out-of-pocket advances (e.g., one person paying for a group meal using cash disbursed from the kitty versus using their personal credit card), traditional tools (like Splitwise) frequently duplicate debt or skew balances.
- **Unclear Settlement Pathways:** After dozens of ad-hoc shared expenses across multiple destinations, resolving multi-party debts results in circular transactions, confusion, and awkward interpersonal friction.
- **Loss of Itinerary Context:** Trip details (flight numbers, hotel check-ins, reservations) are scattered across chat threads, lost in messaging archives, and detached from trip budgeting.

EDITH-TRIP MANAGER resolves these pain points by offering a single, authoritative, secure, and privacy-preserving platform tailored specifically to group savings and trip logistics.

---

## 3. Goals and Success Criteria

| Goal | Success Criteria | Measurement Metric |
| :--- | :--- | :--- |
| **Savings Transparency** | All members can see total verified kitty collections and overall progress toward the group goal in real time. | 100% real-time dashboard accuracy reflecting verified transactions. |
| **Individual Privacy** | Strict isolation of individual savings records. A member cannot inspect another member's contribution timing, submission history, or payment references. | 0% cross-user unauthorized data leakage via API or UI (enforced by backend tests). |
| **Expense Accuracy** | Every shared trip expense has an explicit payer, defined participants, and a verified mathematical split summing to the total. | Sum of splits strictly equals total expense down to the exact paisa (0 tolerance). |
| **Elimination of Double-Counting** | Clear mechanical separation between Kitty Disbursements and Personal Shared Expenses. Kitty expenses never generate individual member debts. | 0 instances of kitty disbursements reflected in personal peer-to-peer balance matrices. |
| **Trip Logistics Coordination** | The administrator can maintain up to 20 ordered trip stops with complete transit and accommodation context accessible to all members. | Full itinerary accessible on mobile web in under 2 seconds. |
| **Zero-Trust Access Security** | Access is strictly restricted to the four designated members. Zero public registration, zero open endpoints. | 100% of data endpoints gated behind Cloudflare Access and Argon2/JWT authentication. |
| **Reliable Communication** | Timely SMS notifications delivered to Indian mobile numbers for dues, verifications, and itinerary updates. | SMS delivery confirmation logged via gateway webhooks within 60 seconds of trigger. |
| **Auditability & Accountability** | Every financial action (contribution verification, disbursement, expense split, settlement confirmation, adjustment) produces an immutable audit record. | 100% traceable audit logs with actor ID, timestamp, and before/after state diffs. |

### Initial Financial Baseline

| Parameter | Value | Configuration Type |
| :--- | :--- | :--- |
| **Active Members** | 4 members (1 Admin, 3 Members) | Fixed in v1 |
| **Monthly Contribution per Member** | ₹2,000 (Two Thousand Indian Rupees) | Configurable by Admin |
| **Savings Duration** | 12 Calendar Months | Configurable by Admin |
| **Total Group Target** | ₹96,000 (Ninety-Six Thousand Indian Rupees) | Derived (₹2,000 × 4 × 12) |

$$\text{Group Target} = \text{Members} \times \text{Monthly Contribution} \times \text{Duration} = 4 \times ₹2,000 \times 12 = ₹96,000$$

---

## 4. Users, Roles, and Permission Matrix

The system enforces a strict Role-Based Access Control (RBAC) model across three distinct functional roles:

1. **Administrator (`admin`):** The primary coordinator and system owner.
2. **Group Member (`member`):** The three participating group members.
3. **Kitty Custodian (`custodian`):** A functional designation assigned to one member (may be the Administrator or another member) who physically manages the bank account or cash holding the collected kitty.

### Role & Permission Matrix

| Feature / Action | Anonymous | Group Member | Kitty Custodian | Administrator |
| :--- | :---: | :---: | :---: | :---: |
| Authenticate / Login | Yes | Yes | Yes | Yes |
| View Group Total Kitty & Target Progress | No | Yes | Yes | Yes |
| View Own Contribution History & Dues | No | Yes | Yes | Yes |
| Submit Own Contribution Proof / UTR | No | Yes | Yes | Yes |
| View Other Members' Contribution Histories | No | **No** | **No** | **Yes** |
| Verify / Reject Submitted Contributions | No | No | Optional Flag | **Yes** |
| Record Kitty Disbursements (Common Expenses) | No | No | No | **Yes** |
| Perform Balance Reconciliation & Ledger Adjustments | No | No | View/Confirm | **Yes** |
| Create Shared Trip Expense (Paid by Self) | No | Yes | Yes | Yes |
| View All Shared Trip Expenses & Split Breakdowns | No | Yes | Yes | Yes |
| Reverse / Edit Shared Expense (Self-Created) | No | Yes (Pending) | Yes (Pending) | **Yes (Any)** |
| View Net Balances & Suggested Settlements | No | Yes | Yes | Yes |
| Propose Debt Settlement Payment | No | Yes | Yes | Yes |
| Confirm Received Settlement Payment | No | Yes (If Creditor) | Yes (If Creditor) | **Yes** |
| View Multi-Destination Trip Itinerary | No | Yes | Yes | Yes |
| Create, Edit, Reorder Itinerary Stops | No | No | No | **Yes** |
| Invite Members, Reset Passwords, Edit Group Rules | No | No | No | **Yes** |
| View System Audit Logs | No | No | No | **Yes** |

---

## 5. Functional Requirements

### 5.1 Savings Kitty (Group Fund Management)

The Savings Kitty module governs the collection, tracking, and management of recurring savings.

| Requirement ID | Requirement Description | Priority | Enforcement Mechanism |
| :--- | :--- | :---: | :--- |
| **KIT-01** | System must allow Admin to configure monthly contribution amount (default: ₹2,000) and duration (default: 12 months). | Must | Admin API / Settings collection |
| **KIT-02** | System must automatically generate monthly contribution schedules for all active members upon group initialization or monthly rollover. | Must | Automated background scheduler |
| **KIT-03** | System must track contribution states across: `pending`, `submitted`, `verified`, `rejected`. | Must | State machine validation |
| **KIT-04** | Members must be able to submit payment records containing: Payment Date, 12-digit UTR/Transaction Reference, and optional payment proof receipt. | Must | Member contribution submission endpoint |
| **KIT-05** | Admin must be able to verify submitted contributions after confirming fund receipt with the Custodian. | Must | Admin verification endpoint |
| **KIT-06** | Total group savings displayed on the dashboard must strictly sum **only** `verified` contributions plus/minus authorized ledger adjustments. | Must | MongoDB aggregation pipeline |
| **KIT-07** | Members must have access only to their own contribution timeline and payment details. Backend must enforce this restriction at the database query level. | Must | FastAPI route authorization dependency |
| **KIT-08** | Group-level monthly collection progress must display aggregate count of verified contributions (e.g., "3 of 4 paid this month") without identifying who has or has not paid. | Must | Scrubbed aggregate view |
| **KIT-09** | System must record kitty disbursements for common group prepayments (e.g., hotel advances, train bookings) detailing: Amount, Date, Category, Recipient, Purpose, and Authorizing Admin. | Must | Kitty disbursement ledger |
| **KIT-10** | System must support periodic physical reconciliation between recorded kitty balance and the Custodian's actual bank/cash balance, logging any variances. | Must | Custodian reconciliation workflow |
| **KIT-11** | Any correction, reversal, or manual balance adjustment must require an explicit reason and generate an immutable audit log entry. | Must | Audit interceptor |
| **KIT-12** | System must support triggering monthly contribution reminder SMS messages 3 days prior to the due date and on the due date. | Should | DLT-compliant SMS integration |

#### Contribution Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Pending : Monthly Cycle Rollover
    Pending --> Submitted : Member Submits Payment (UTR Reference)
    Submitted --> Verified : Admin Verifies Receipt with Custodian
    Submitted --> Rejected : Admin Rejects (Invalid UTR / Funds Not Received)
    Rejected --> Submitted : Member Re-Submits Corrected Details
    Verified --> Reversed : Admin Reversal (Compensating Ledger Entry)
    Reversed --> [*]
    Verified --> [*]
```

---

### 5.2 Kitty Split (Shared Trip Expenses)

The Kitty Split module governs personal out-of-pocket shared expenses incurred by members during travel.

| Requirement ID | Requirement Description | Priority | Enforcement Mechanism |
| :--- | :--- | :---: | :--- |
| **EXP-01** | Any authenticated member can record a shared trip expense specifying: Date, Description, Category, Total Amount (in paise), Payer, and Participants. | Must | Expense creation route |
| **EXP-02** | System must allow selecting any single member as the payer (default: current logged-in user). | Must | Payer validation |
| **EXP-03** | System must allow multi-selection of participants who share in the expense (subset of group or all 4 members). | Must | Participant array validation |
| **EXP-04** | System must support **Equal Split**: Even division among selected participants, deterministically allocating remainder paise. | Must | Division algorithm |
| **EXP-05** | System must support **Exact Amount Split**: Custom explicit amount per participant, with validation that $\sum \text{Shares} = \text{Total Amount}$. | Must | Sum validation check |
| **EXP-06** | System must support **Percentage Split**: Custom percentage per participant, with validation that $\sum \text{Percentages} = 100.00\%$. | Must | Percentage validation check |
| **EXP-07** | System must calculate real-time net balances for all members: $\text{Net} = \text{Total Incurred} - \text{Total Owed}$. | Must | Net balance engine |
| **EXP-08** | System must generate a simplified settlement plan using the Minimum Cash Flow algorithm to minimize peer-to-peer transactions. | Must | Settlement solver |
| **EXP-09** | System must allow a debtor to record a proposed settlement payment to a creditor with reference details. | Must | Settlement proposition workflow |
| **EXP-10** | Balances must only update after the receiving creditor (or Admin) explicitly confirms receipt of the settlement payment. | Must | Two-phase settlement confirmation |
| **EXP-11** | Full expense modification and reversal history must be maintained. Expenses cannot be hard-deleted once saved. | Must | Soft-delete / Reversal ledger |

#### Expense Split Mathematical Example

Suppose Member A pays ₹4,000 for a shared safari jeep trip, shared equally among all 4 members (A, B, C, D):

$$\text{Share per person} = \frac{₹4,000}{4} = ₹1,000$$

| Member | Expense Cost Share | Amount Paid Out-of-Pocket | Net Position ($\text{Paid} - \text{Share}$) | Financial Meaning |
| :---: | :---: | :---: | :---: | :--- |
| **Member A** | ₹1,000 | ₹4,000 | **+₹3,000** | Creditor (Owed ₹3,000) |
| **Member B** | ₹1,000 | ₹0 | **-₹1,000** | Debtor (Owes ₹1,000) |
| **Member C** | ₹1,000 | ₹0 | **-₹1,000** | Debtor (Owes ₹1,000) |
| **Member D** | ₹1,000 | ₹0 | **-₹1,000** | Debtor (Owes ₹1,000) |

---

### 5.3 Common Kitty Expenses & Disbursements

When an expense is funded directly from the physical Kitty pool (e.g., flight booking, hotel deposit, vehicle hire advance), it follows the **Kitty Disbursement** pathway.

#### Separation Rules:
1. **Direct Ledger Impact:** A Kitty Disbursement decrements the group's verified kitty balance directly.
2. **Zero Peer Debt:** It does **not** create any individual peer-to-peer debts in Kitty Split.
3. **No Double-Counting:** An expense paid from the Kitty must never be entered into the Kitty Split module unless an individual member personally paid an additional out-of-pocket supplement.
4. **Authorization:** Only the Administrator can record or authorize a Kitty Disbursement, providing receipts and vendor information.

| Transaction Event | Kitty Balance Impact | Personal Split Balance Impact |
| :--- | :---: | :---: |
| Member submits ₹2,000 monthly contribution (Verified) | **+₹2,000** | No Change |
| Member pays ₹4,000 out-of-pocket for shared dinner | No Change | **Recalculated in Kitty Split** |
| Kitty pays ₹15,000 advance for group villa rental | **-₹15,000** | **No Change (Zero Personal Debt)** |

---

### 5.4 Trip Planner & Itinerary Management

The Trip Planner provides a structured, multi-destination timeline for the journey.

| Requirement ID | Requirement Description | Priority |
| :--- | :--- | :---: |
| **TRP-01** | Support defining overall trip details: Title, Master Dates, Trip Description, Cover Details. | Must |
| **TRP-02** | Support up to 20 ordered stops/destinations in a single itinerary. | Must |
| **TRP-03** | Each stop must capture: Destination/City Name, Stop Sequence Number, Arrival Datetime, Departure Datetime, Transportation Mode (Flight, Train, Private Van, Rental Car, Ferry), Transport Booking Reference, Accommodation Name, Check-in/Check-out, Address, Google Maps link, and Notes. | Must |
| **TRP-04** | Admin can add, edit, delete, and dynamically reorder stops (drag-and-drop or sequence number update). | Must |
| **TRP-05** | All 4 members have real-time read access to the full itinerary and booking references. | Must |
| **TRP-06** | System highlights the currently active stop based on the user's local system time during the trip. | Should |

---

### 5.5 Dashboard & Overview

The Dashboard serves as the central command center for each authenticated user upon logging in:

1. **Executive Kitty Summary:**
   - Total Verified Group Savings (₹) vs. Group Target (₹96,000).
   - Visual Progress Bar with percentage completion.
   - Current Month's Collection Pulse (e.g., "3 of 4 Contributions Verified").
2. **Personal Contribution Status Badge:**
   - Current Month Due Date.
   - Status Indicator: `Pending Submission`, `Submitted (Awaiting Verification)`, `Verified`, or `Overdue`.
   - Action Button: "Submit Payment Proof" (direct modal trigger).
3. **Trip Countdown & Snapshot:**
   - Days remaining until Trip Departure.
   - Total planned destinations (e.g., "6 stops planned").
   - Next destination teaser with dates.
4. **Kitty Split Net Position:**
   - Personal net position highlighted in Green (+₹X to receive) or Red (-₹Y to pay).
   - Direct button to "View Settlement Plan" or "Record Expense".
5. **Recent Activity Feed:**
   - 5 most recent verified transactions, added expenses, or itinerary updates.

---

### 5.6 Notification System

Notifications provide urgent, reliable alerts via standard Indian Transactional SMS (complying with DLT regulations):

| Trigger Event | Recipient | SMS Template Purpose | Channel |
| :--- | :--- | :--- | :---: |
| Monthly Contribution Due (T-3 days & T-0) | Unpaid Group Members | Payment reminder with amount & custodian UPI ID | SMS |
| Contribution Verified | Contributing Member | Confirmation of credited contribution | SMS |
| Contribution Rejected | Contributing Member | Notification of rejection with admin reason | SMS |
| New Shared Expense Logged | All Expense Participants | Notification of new expense and individual share | SMS |
| Settlement Proposed | Creditor Member | Notification that peer has sent settlement payment | SMS |
| Settlement Confirmed | Debtor Member | Confirmation that settlement has cleared | SMS |
| Itinerary Modified | All Group Members | Alert regarding schedule or lodging change | SMS |

---

## 6. Access Control and Privacy Architecture

The system operates under a **Zero-Trust & Strict Isolation** paradigm:

1. **No Public Registration:** The system has no self-registration or signup page. Accounts are provisioned solely by the Administrator.
2. **Perimeter Defense (Cloudflare Zero Trust / Access):** The application domain is protected behind Cloudflare Access, restricting ingress to the verified email addresses of the four members before requests reach the application server.
3. **Application Authentication:** Independent JWT-based bearer authentication using Argon2id password hashing. Tokens carry member ID and role claims with 30-minute access token lifespans and 7-day refresh tokens.
4. **Field-Level Data Privacy (Backend Enforced):**
   - The database query for contributions filters out other members' records unless the requesting user holds the `admin` role.
   - The API response model (`ContributionResponse`) strictly strips private data (such as bank reference numbers, upload proofs, and payment timestamps) from non-admin endpoints.
5. **Session Security:** Strict HTTPS enforcement, HTTP-only SameSite cookies for refresh tokens, and rate-limiting on sensitive endpoints (e.g., login attempts capped at 5 per minute per IP).

---

## 7. Non-Functional Requirements

| Metric / Category | Specification | Verification Method |
| :--- | :--- | :--- |
| **Security & Cryptography** | Argon2id password hashing (Memory: 64MB, Iterations: 3, Parallelism: 4). HS256/RS256 JWT tokens with cryptographic salt. | Automated security unit tests. |
| **Financial Precision** | Zero floating-point arithmetic. All monetary values stored and calculated as 64-bit integer minor units (paise: ₹1.00 = 100 paise). | Unit test suite with rounding edge cases. |
| **API Response Time** | $\le 200\text{ ms}$ for 95th percentile ($p95$) of standard read/write API requests under typical load. | Benchmark load tests. |
| **Dashboard Load Time** | Initial dashboard render complete in $< 1.5\text{ seconds}$ on standard 4G mobile connections. | Chrome Lighthouse performance audit. |
| **Client Usability** | Fully responsive web UI supporting viewport widths from 360px (mobile) to 1920px (desktop) without horizontal clipping. | Cross-device testing (Chrome, Safari iOS, Android). |
| **Availability Target** | 99.5% uptime during active savings months; 99.9% uptime during the active travel period. | Uptime monitoring ping service. |
| **Data Backup & Durability** | Automated daily MongoDB Atlas snapshots with point-in-time recovery enabled. Retained for 30 days. | Simulated disaster recovery drill. |
| **Audit Immutability** | Financial transactions cannot be modified in-place or deleted. All adjustments require compensating transactions. | Database schema constraints & audit middleware. |

---

## 8. Technical Architecture

### 8.1 Technology Stack

```mermaid
graph TD
    User([User Browser / Mobile]) -->|HTTPS / WSS| CF[Cloudflare Access & CDN]
    CF -->|Authenticated Proxy| NGINX[Reverse Proxy / Static File Server]
    NGINX -->|Static Assets| Frontend[HTML5 / Modern CSS / Vanilla ES6 JavaScript]
    NGINX -->|API Proxy :8000| Backend[Python 3.12 + FastAPI App]
    Backend -->|PyMongo / Motor| DB[(MongoDB Atlas Cloud Replica Set)]
    Backend -->|HTTPS REST| SMSGateway[Indian DLT SMS Gateway Fast2SMS/Gupshup]
    Backend -->|In-Process / Cron| Scheduler[APScheduler Background Jobs]
```

| Layer | Chosen Technology | Rationale |
| :--- | :--- | :--- |
| **Frontend** | HTML5, Vanilla JavaScript (ES6+), Modern CSS3 | Zero bundle build step, lightweight, blazing fast on mobile devices, trivial to maintain and modify without complex toolchains. |
| **Backend API** | Python 3.12 + FastAPI + Pydantic v2 | High-performance asynchronous execution, strict type validation, automatic OpenAPI interactive documentation, rapid development. |
| **Database** | MongoDB Atlas (M0 / M10 Dedicated Replica Set) | Flexible document schema for multi-destination trip stops, atomic document-level operations, native JSON compatibility. |
| **Authentication** | Argon2id + PyJWT | Industry-standard password hashing resilience against GPU brute-force attacks; stateless scalable JWT tokens. |
| **Access Gateway** | Cloudflare Access (Zero Trust) | Pre-application perimeter defense eliminating bot scraping, DDoS, and unapproved IP access. |
| **Task Scheduler** | APScheduler (Advanced Python Scheduler) | In-process cron triggers for automated contribution generation and reminder dispatches. |
| **SMS Gateway** | Fast2SMS / Msg91 (DLT Registered) | Direct compliance with TRAI regulations, high deliverability across Indian telecom operators. |

---

### 8.2 Project Structure

```text
EDITH-TRIP-MANAGER/
├── frontend/
│   ├── index.html                 # Single page application shell
│   ├── css/
│   │   ├── main.css               # Core styling, CSS variables & typography
│   │   ├── dashboard.css          # Executive dashboard component styles
│   │   ├── kitty.css              # Savings kitty ledger & contribution matrix
│   │   ├── expenses.css           # Kitty split and balance settlement styles
│   │   └── trips.css              # Itinerary timeline & stop cards
│   └── js/
│       ├── app.js                 # App initialization, routing & state store
│       ├── api.js                 # Fetch client wrapper with JWT token handling
│       ├── auth.js                # Auth state management & login handlers
│       ├── kitty.js               # Savings kitty UI controller
│       ├── expenses.js            # Expense splitting UI controller
│       ├── trips.js               # Trip planner timeline UI controller
│       └── admin.js               # Admin console & audit log viewer
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application initialization & middleware
│   ├── config.py                  # Pydantic BaseSettings & environment loader
│   ├── database.py                # MongoDB async connection & index manager
│   ├── security.py                # Argon2 hashing, JWT generation & verification
│   ├── dependencies.py            # RBAC guards & current_user dependencies
│   ├── models/                    # Pydantic domain models & schemas
│   │   ├── user.py
│   │   ├── group.py
│   │   ├── contribution.py
│   │   ├── kitty_transaction.py
│   │   ├── expense.py
│   │   ├── settlement.py
│   │   ├── trip.py
│   │   ├── notification.py
│   │   └── audit.py
│   ├── routes/                    # REST API route handlers
│   │   ├── auth.py
│   │   ├── admin.py
│   │   ├── kitty.py
│   │   ├── expenses.py
│   │   ├── settlements.py
│   │   ├── trips.py
│   │   └── notifications.py
│   └── services/                  # Business logic & accounting engine
│       ├── accounting.py          # Integer math, split calculation, debt solver
│       ├── sms.py                 # DLT SMS client & webhook dispatcher
│       ├── scheduler.py           # Monthly contribution rollover jobs
│       └── audit.py               # Audit trail recorder
├── tests/
│   ├── conftest.py                # Pytest fixtures & mock database
│   ├── test_auth.py               # Auth & RBAC boundary tests
│   ├── test_accounting.py         # Split math & debt minimization tests
│   ├── test_kitty.py              # Kitty ledger & reconciliation tests
│   ├── test_expenses.py           # Shared expense lifecycle tests
│   └── test_privacy.py            # Field-level privacy isolation tests
├── scripts/
│   ├── seed_initial_group.py      # Seed 4 members and initial settings
│   └── backup_database.sh         # Automated mongodump script
├── Dockerfile                     # Multi-stage production container build
├── docker-compose.yml             # Orchestration for local development
├── requirements.txt               # Pinned Python dependencies
├── .env.example                   # Environment configuration template
└── README.md                      # Operational and deployment guide
```

---

### 8.3 Database Collections Overview

The database uses 12 purpose-built collections:

1. `users`: Stores member credentials, roles, masked contact info, and profile metadata.
2. `groups`: Stores group configuration, monthly targets, currency, and designated custodian ID.
3. `memberships`: Associates users with groups and tracks active membership states.
4. `contributions`: Monthly individual contribution obligations, submissions, and verification records.
5. `kitty_transactions`: Master ledger of all funds entering or exiting the collective Kitty pool.
6. `expenses`: Master records for personal out-of-pocket shared trip expenses.
7. `expense_splits`: Individual cost allocations per member for each shared expense.
8. `settlements`: Peer-to-peer repayment proposals and two-phase receipt confirmations.
9. `trips`: High-level trip entities, destination counts, and dates.
10. `trip_stops`: Ordered stops (1 to 20) with transit and lodging metadata.
11. `notifications`: Audit log of all outgoing SMS alerts, DLT template IDs, and delivery statuses.
12. `audit_logs`: Immutable security and financial audit trail capturing actor, action, and state diffs.

---

## 9. Key Business Rules & Accounting Invariants

1. **Fixed Group Ceiling:** Exactly 4 active member accounts are supported in Version 1.
2. **Singular Authority:** Exactly one user possesses the `admin` role, holding sole authority over group settings, stop reordering, and contribution verifications.
3. **Physical Custodian Accountability:** The designated Custodian holds physical custody of funds; all recorded kitty transactions must reflect verified bank deposits or authorized physical withdrawals.
4. **Conditional Recognition of Funds:** Unverified submissions (`pending`, `submitted`, `rejected`) **never** increment the kitty balance.
5. **Strict Ledger Segregation:** Personal expenses entered in Kitty Split **never** affect the Kitty balance. Kitty Disbursements **never** affect personal split balances.
6. **Zero Float Accuracy:** All currency figures are stored as integers representing paise ($1\text{ INR} = 100\text{ paise}$). Binary floating-point representation (`float`) is strictly prohibited in financial pipelines.
7. **Complete Remainder Exhaustion:** In an equal split with indivisible odd paise, remainder paise are allocated sequentially to participants such that:
   $$\sum_{i=1}^{k} \text{Share}_i = \text{Total Amount}$$
8. **Conservative Settlements:** Proposed settlements do not alter net balance calculations until the recipient confirms receipt or the administrator approves the reconciliation.
9. **Zero In-Place Deletions:** Financial documents (contributions, expenses, disbursements) cannot be deleted. Corrections must be executed via compensating reversal records.
10. **Backend Privacy Invariant:** API responses for group members must systematically strip other members' contribution payment references, dates, and statuses.

---

## 10. Scope and Phased Release Plan

```mermaid
gantt
    title EDITH-TRIP MANAGER Implementation Roadmap
    dateFormat  YYYY-MM-DD
    section Phase 1: Core Foundation
    Auth & RBAC Architecture       :done, p1_1, 2026-11-01, 7d
    Trip Planner & Basic UI        :done, p1_2, 2026-11-08, 7d
    section Phase 2: Accounting Engine
    Integer Math & Split Algorithms:active, p2_1, 2026-11-15, 6d
    Kitty Ledger & Reconciliation  :p2_2, after p2_1, 8d
    Audit Trail Engine             :p2_3, after p2_2, 5d
    section Phase 3: DLT & SMS
    TRAI DLT Template Registration :p3_1, 2026-12-04, 5d
    SMS Gateway Webhooks & Logic   :p3_2, after p3_1, 6d
    section Phase 4: Cloud Hardening
    Cloudflare Zero Trust Gate     :p4_1, 2026-12-15, 5d
    MongoDB Atlas & Docker Prod    :p4_2, after p4_1, 5d
    section Phase 5: Verification
    End-to-End Simulation Tests   :p5_1, 2026-12-25, 7d
    Production Go-Live             :milestone, 2026-12-31, 1d
```

- **Phase 1 — Core Foundation:** Authentication, user management, basic responsive UI shell, and multi-stop trip planner.
- **Phase 2 — Kitty Accounting Engine:** Monthly contribution generator, UTR verification workflow, personal split engine with integer math, debt settlement solver, and audit logger.
- **Phase 3 — DLT SMS Integration:** SMS provider client, approved template registration, automated background reminder triggers, and delivery status tracking.
- **Phase 4 — Cloud Infrastructure & Hardening:** Docker containerization, MongoDB Atlas deployment, Cloudflare Zero Trust setup, and automated database backups.
- **Phase 5 — End-to-End Validation & Sign-Off:** Comprehensive 4-member simulation testing, edge case verification, and final production sign-off.

---

## 11. Out of Scope for Version 1

To maintain strict security, low operational overhead, and swift time-to-production, the following capabilities are explicitly declared out of scope for Version 1:

1. **Direct In-App Banking / Payment Gateway (PG):** No direct integration with Razorpay, Cashfree, or UPI payment gateways. Funds move via external UPI apps; EDITH-TRIP MANAGER serves strictly as the verification ledger.
2. **Automated Bank Account Scraping:** No Open Banking / Account Aggregator integration.
3. **Public Registration / Multi-Tenancy:** The application is hard-coded for a single group of four users. No multi-tenant group creation.
4. **Automated Travel Booking:** No live GDS/OTA API integrations for auto-booking flights, trains (IRCTC), or hotels.
5. **WhatsApp Business API:** Excluded due to high recurring Meta conversation costs and compliance hurdles; ordinary DLT-compliant Indian transactional SMS is selected instead.
6. **Native Mobile App Builds:** No standalone iOS/Android native apps (Swift/Kotlin/React Native). The platform is deployed as a responsive Progressive Web App (PWA).

---

## 12. Core Acceptance Criteria

| ID | Test Scenario | Execution Step | Expected Result | Pass/Fail Criteria |
| :---: | :--- | :--- | :--- | :--- |
| **AC-01** | Full Monthly Contribution Cycle | All 4 members submit ₹2,000 UTR; Admin approves all 4. | Group Kitty increases by exactly ₹8,000; Dashboard progress bar advances. | Kitty Total matches ₹8,000.00; All 4 show verified. |
| **AC-02** | Unverified Contribution Isolation | Member B submits UTR for ₹2,000; Admin does not verify. | Total verified Kitty remains unchanged; Member B sees "Submitted". | Kitty Total reflects 0 increase from Member B. |
| **AC-03** | Cross-Member Privacy Enforcement | Member C attempts to call `/api/v1/kitty/contributions` for Member A. | HTTP 403 Forbidden or filtered response excluding Member A's records. | 0 personal records of Member A exposed to Member C. |
| **AC-04** | 3-Way Uneven Split Precision | Member A pays ₹100.00 split equally among A, B, and C. | Shares: ₹33.34, ₹33.33, ₹33.33. Sum strictly equals ₹100.00 (10,000 paise). | Zero unaccounted paise. |
| **AC-05** | Kitty Disbursement Isolation | Admin logs ₹5,000 Kitty payment for train tickets. | Kitty balance decreases by ₹5,000.00; Zero personal debts created in Kitty Split. | Kitty Split net balances remain exactly unchanged. |
| **AC-06** | Two-Phase Settlement Flow | Member B owes Member A ₹1,000; B records settlement; A confirms. | B's debt is cleared only **after** A clicks Confirm. Prior to confirmation, debt remains pending. | Balances update strictly upon confirmation event. |
| **AC-07** | Trip Timeline Sequence Integrity | Admin adds 5 stops and reorders Stop 5 to Position 2. | Itinerary displays stops in new sequence (1, 2, 3, 4, 5) with dates validated. | Display matches sequence numbers strictly. |
| **AC-08** | Unauthorized Access Attempt | Unauthenticated client attempts direct GET on `/api/v1/kitty/summary`. | HTTP 401 Unauthorized returned immediately. | Ingress blocked without JWT. |
| **AC-09** | Ledger Correction Auditability | Admin reverses an errant ₹2,000 contribution. | Original entry marked `reversed`; Compensating entry logged; Audit log records actor, timestamp, reason. | Unbroken audit trail in `audit_logs`. |

---

## 13. Risks, Failure Modes, and Mitigations

| Risk & Failure Mode | Severity | Probability | Concrete Technical Mitigation |
| :--- | :---: | :---: | :--- |
| **Erroneous Contribution Approval** | High | Low | Dual-check workflow: Admin verifies against Custodian's live bank statement. Reversal workflow creates compensating ledger entry with mandatory reason. |
| **Physical vs. Recorded Kitty Discrepancy** | High | Medium | Built-in Reconciliation Module: Custodian performs monthly balance audit. Any delta triggers an automated `adjustment` transaction with mandatory documentation. |
| **Duplicate Expense Submission** | Medium | Medium | Client-side idempotency keys (UUIDv4) sent on POST requests; Backend unique index on `(group_id, payer_id, amount, date_minute)`. |
| **Data Privacy Leakage** | Critical | Low | Pydantic response filtering + database query filtering by `current_user.id`. Automated unit tests specifically asserting non-admin privacy boundaries. |
| **SMS Delivery Blackout** | Medium | Medium | Automated retry mechanism with exponential backoff (3 attempts); Dashboard displays persistent web alerts so SMS failure does not block user awareness. |
| **Database Corruption / Instance Loss** | Critical | Very Low | MongoDB Atlas automated 24-hour snapshot retention + offsite daily encrypted mongodump script to S3-compatible cold storage. |
| **Rounding Accumulation Errors** | High | Low | Use of 64-bit integer paise throughout application. Explicit remainder redistribution algorithm ensures zero lost paise across any split configuration. |

---

## 14. System Assumptions & Baseline Parameters

1. **Closed User Community:** Exactly 4 individuals who know each other and have agreed to the shared financial goals.
2. **Fixed Monthly Cadence:** Monthly contribution generation occurs on the 1st day of each calendar month at 00:00:00 IST.
3. **Grace Period & Due Dates:** Monthly contributions are due by the 10th day of each calendar month.
4. **Primary Banking Conduit:** Custodian maintains an active, zero-balance or dedicated bank account linked to an Indian UPI handle (VPA) for group fund consolidation.
5. **Regulatory Compliance:** SMS notifications adhere to the Telecom Commercial Communications Customer Preference Regulations (TCCCPR), 2018, operating under registered transactional/service implicit DLT templates.
6. **Single Trip Target:** Version 1 manages one primary master trip containing up to 20 destinations.

---

## 15. Resolved Architectural & Operational Decisions

The following definitive architectural decisions have been resolved and approved for implementation:

### Decision 1: Contribution Verification Authority
- **Resolution:** The **Administrator** possesses sole verification authority in the system. The Custodian receives automated system notifications upon submission and can flag discrepancies, but only the Administrator triggers the official status change to `verified`.
- **Rationale:** Centralizing write authorization prevents race conditions, conflicting approvals, and split-brain states between Admin and Custodian.

### Decision 2: Contribution Evidence Protocol
- **Resolution:** A valid **12-digit Bank/UPI Transaction Reference (UTR) number is mandatory** for all contribution submissions. Image screenshot upload is optional.
- **Rationale:** UTR numbers provide an immutable, unique, and search-indexed transaction key that can be directly verified against the Custodian's bank statement without relying on fragile OCR processing. A unique index on `utr_reference` prevents accidental double-submission of the same payment.

### Decision 3: Kitty Fund Custody & Interest Handling
- **Resolution:** Funds will be held in a dedicated, high-yield digital bank savings account managed by the designated Custodian. Any bank interest earned will be credited semi-annually as an authorized `interest_credit` Kitty Adjustment, reducing group overhead. Cash on hand during travel will be capped at ₹5,000 for emergency petty expenses.
- **Rationale:** Eliminates commingling of personal and group funds, provides clean PDF bank statements for reconciliation, and captures yield on the accumulating ₹96,000 balance.

### Decision 4: Member Privacy & Phone Number Masking
- **Resolution:** Member phone numbers are encrypted at rest using AES-256 and masked in the UI (e.g., `+91 98XXX XX123`). Only the Administrator can view full contact details in the Admin Console. Individual contribution histories are strictly hidden from peers.
- **Rationale:** Preserves interpersonal comfort and privacy while allowing the automated backend to dispatch SMS notifications.

### Decision 5: Account Recovery Protocol
- **Resolution:** Self-service password reset is disabled. The Administrator can issue a single-use, cryptographically generated, time-limited (15-minute expiry) password reset link or temporary password delivered out-of-band to the member's registered phone number.
- **Rationale:** With only four known users, eliminating open password reset endpoints closes the primary attack vector for credential-stuffing and account takeover without adding expensive transactional email infrastructure.

---

## 16. Implementation Status & Progress Baseline

| Subsystem | Component | Implementation Status | Next Action |
| :--- | :--- | :---: | :--- |
| **Core Framework** | FastAPI Backend Architecture | **Implemented** | Refactor models to Pydantic v2 schemas |
| **Authentication** | JWT Bearer & Argon2id Hashing | **Implemented** | Add refresh token rotation & rate-limiting |
| **Administration** | Member & Group Settings API | **Implemented** | Integrate UTR duplicate validation |
| **Trip Planner** | Multi-Stop Timeline & Reordering | **Implemented** | Add active-stop time-based highlighting |
| **Kitty Split** | Equal / Exact / Percentage Splits | **Implemented** | Standardize integer paise arithmetic |
| **Settlement Solver** | Minimum Cash Flow Algorithm | **Implemented** | Add two-phase creditor confirmation |
| **Savings Kitty** | Monthly Rollover & UTR Ledger | **Pending Phase 2** | Build scheduler & verification queue |
| **Reconciliation** | Custodian Audit & Adjustment Flow | **Pending Phase 2** | Implement reconciliation ledger API |
| **Audit Engine** | Full Event Diff Logging | **Pending Phase 2** | Implement FastAPI audit middleware |
| **SMS Integration** | Indian DLT Gateway Client | **Pending Phase 3** | Register templates & webhook handler |
| **Cloud Gate** | Cloudflare Access Perimeter | **Pending Phase 4** | Configure zero-trust access policy |

---

## 17. Product Definition & Guiding Architectural Principles

**EDITH-TRIP MANAGER is a private, high-integrity group savings and trip logistics engine—not a payment wallet, public travel platform, or banking intermediary.**

### Core Architectural Principles:
1. **Financial Immutability:** Never overwrite or hard-delete financial history. All adjustments must be executed via auditable, compensating transactions.
2. **Absolute Numerical Precision:** Never use binary floating-point (`float`) for monetary operations. Always utilize 64-bit integer paise.
3. **Zero-Trust Access & Privacy by Design:** Never rely on client-side UI visibility to enforce security. Backend API routes must enforce strict role checks and field-level data scrubbing.
4. **Clean Operational Separation:** Never mix collective Kitty disbursements with personal peer-to-peer split expenses.

---

## 18. Detailed Database Schemas & Data Models

All document models are defined with Pydantic v2 schemas and persisted in MongoDB.

```mermaid
erDiagram
    USERS ||--o{ MEMBERSHIPS : has
    GROUPS ||--o{ MEMBERSHIPS : includes
    GROUPS ||--o{ CONTRIBUTIONS : tracks
    USERS ||--o{ CONTRIBUTIONS : submits
    GROUPS ||--o{ KITTY_TRANSACTIONS : records
    GROUPS ||--o{ EXPENSES : incurs
    USERS ||--o{ EXPENSES : pays
    EXPENSES ||--|{ EXPENSE_SPLITS : divides
    USERS ||--o{ EXPENSE_SPLITS : owes
    GROUPS ||--o{ SETTLEMENTS : resolves
    USERS ||--o{ SETTLEMENTS : sends
    USERS ||--o{ SETTLEMENTS : receives
    GROUPS ||--o{ TRIPS : plans
    TRIPS ||--|{ TRIP_STOPS : contains
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ AUDIT_LOGS : performs
```

### 18.1 Collection: `users`
Stores user authentication credentials, role assignments, and profile metadata.

```json
{
  "_id": "ObjectId",
  "email": "user@example.com",
  "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$...",
  "full_name": "Prajwal Sharma",
  "phone_number": "+919876543210",
  "role": "admin", // "admin" | "member"
  "is_custodian": true,
  "is_active": true,
  "created_at": "2026-11-06T20:00:00Z",
  "updated_at": "2026-11-06T20:00:00Z"
}
```
- **Indexes:**
  - `email`: Unique Index (`{"email": 1}`, `unique=True`)
  - `phone_number`: Unique Index (`{"phone_number": 1}`, `unique=True`)

### 18.2 Collection: `groups`
Stores group configurations, savings targets, and financial policies.

```json
{
  "_id": "ObjectId",
  "name": "Edith Grand Expedition 2027",
  "currency": "INR",
  "monthly_target_per_member": 200000, // 2000.00 INR stored as paise
  "duration_months": 12,
  "target_total_amount": 9600000, // 96000.00 INR stored as paise
  "custodian_user_id": "ObjectId('user_id')",
  "admin_user_id": "ObjectId('user_id')",
  "start_date": "2026-12-01T00:00:00Z",
  "status": "active", // "active" | "completed" | "archived"
  "created_at": "2026-11-06T20:00:00Z"
}
```

### 18.3 Collection: `memberships`
Associates users with groups and defines group-specific settings.

```json
{
  "_id": "ObjectId",
  "group_id": "ObjectId('group_id')",
  "user_id": "ObjectId('user_id')",
  "role": "member", // "admin" | "member"
  "is_custodian": false,
  "joined_at": "2026-11-06T20:00:00Z",
  "status": "active" // "active" | "suspended"
}
```
- **Indexes:**
  - Compound Unique: `{"group_id": 1, "user_id": 1}`, `unique=True`

### 18.4 Collection: `contributions`
Individual monthly contribution obligations and payment submissions.

```json
{
  "_id": "ObjectId",
  "group_id": "ObjectId('group_id')",
  "user_id": "ObjectId('user_id')",
  "month_index": 1, // 1 to 12
  "cycle_month": "2026-12", // YYYY-MM
  "due_date": "2026-12-10T23:59:59Z",
  "amount_due": 200000, // in paise
  "amount_paid": 200000, // in paise (null if pending)
  "utr_reference": "432109876543", // 12-digit bank reference (null if pending)
  "proof_url": "https://storage.local/proofs/m1_u2.jpg", // optional
  "status": "verified", // "pending" | "submitted" | "verified" | "rejected" | "reversed"
  "submitted_at": "2026-12-05T14:30:00Z",
  "verified_at": "2026-12-05T18:00:00Z",
  "verified_by": "ObjectId('admin_user_id')",
  "rejection_reason": null,
  "created_at": "2026-12-01T00:00:00Z"
}
```
- **Indexes:**
  - Compound Unique: `{"group_id": 1, "user_id": 1, "month_index": 1}`, `unique=True`
  - Sparse Index on UTR: `{"utr_reference": 1}`, `unique=True`, `sparse=True`
  - Query Filter: `{"group_id": 1, "status": 1}`

### 18.5 Collection: `kitty_transactions`
Master financial ledger for collective group fund movements.

```json
{
  "_id": "ObjectId",
  "group_id": "ObjectId('group_id')",
  "transaction_type": "contribution_credit", // "contribution_credit" | "disbursement" | "adjustment" | "interest_credit"
  "amount": 200000, // positive integer in paise
  "balance_after": 200000, // running balance in paise
  "category": "monthly_contribution", // "hotel_advance" | "transport" | "activity" | "adjustment"
  "description": "Monthly savings contribution verified for Month 1",
  "reference_id": "ObjectId('contribution_id')", // ID of linked contribution or receipt
  "authorized_by": "ObjectId('admin_user_id')",
  "recipient": "Group Kitty",
  "receipt_url": null,
  "is_reversal": false,
  "reversal_of_id": null,
  "created_at": "2026-12-05T18:00:00Z"
}
```
- **Indexes:**
  - `{"group_id": 1, "created_at": -1}`

### 18.6 Collection: `expenses`
Personally incurred shared trip expenses.

```json
{
  "_id": "ObjectId",
  "group_id": "ObjectId('group_id')",
  "trip_id": "ObjectId('trip_id')",
  "payer_id": "ObjectId('user_id')",
  "description": "Scuba Diving & Equipment Rental",
  "category": "activities", // "food" | "stay" | "transport" | "activities" | "misc"
  "total_amount": 1200000, // 12,000.00 INR in paise
  "expense_date": "2027-01-15T10:30:00Z",
  "split_method": "equal", // "equal" | "exact" | "percentage"
  "receipt_url": null,
  "status": "active", // "active" | "reversed"
  "created_at": "2027-01-15T11:00:00Z",
  "created_by": "ObjectId('user_id')"
}
```
- **Indexes:**
  - `{"group_id": 1, "expense_date": -1}`
  - `{"payer_id": 1}`

### 18.7 Collection: `expense_splits`
Granular cost breakdown per participant for each personal expense.

```json
{
  "_id": "ObjectId",
  "expense_id": "ObjectId('expense_id')",
  "group_id": "ObjectId('group_id')",
  "user_id": "ObjectId('user_id')",
  "share_amount": 300000, // 3,000.00 INR in paise
  "percentage": 25.0, // optional metadata for percentage splits
  "created_at": "2027-01-15T11:00:00Z"
}
```
- **Indexes:**
  - `{"expense_id": 1, "user_id": 1}`, `unique=True`
  - `{"group_id": 1, "user_id": 1}`

### 18.8 Collection: `settlements`
Peer-to-peer debt settlements.

```json
{
  "_id": "ObjectId",
  "group_id": "ObjectId('group_id')",
  "debtor_id": "ObjectId('user_id')", // Person paying
  "creditor_id": "ObjectId('user_id')", // Person receiving
  "amount": 300000, // in paise
  "payment_method": "UPI",
  "utr_reference": "987654321012",
  "status": "confirmed", // "proposed" | "confirmed" | "rejected"
  "proposed_at": "2027-01-16T18:00:00Z",
  "confirmed_at": "2027-01-16T19:30:00Z",
  "confirmed_by": "ObjectId('creditor_user_id')",
  "notes": "Cleared safari expense balance"
}
```
- **Indexes:**
  - `{"group_id": 1, "status": 1}`
  - `{"debtor_id": 1, "creditor_id": 1}`

### 18.9 Collection: `trips`
Master trip record.

```json
{
  "_id": "ObjectId",
  "group_id": "ObjectId('group_id')",
  "title": "Himachal & Ladakh Odyssey 2027",
  "description": "14-day overland mountain expedition across 6 destinations.",
  "start_date": "2027-06-01T00:00:00Z",
  "end_date": "2027-06-15T23:59:59Z",
  "total_stops": 6,
  "status": "planning", // "planning" | "active" | "completed"
  "created_by": "ObjectId('admin_user_id')",
  "created_at": "2026-11-06T20:00:00Z"
}
```

### 18.10 Collection: `trip_stops`
Ordered stops/destinations within the trip.

```json
{
  "_id": "ObjectId",
  "trip_id": "ObjectId('trip_id')",
  "group_id": "ObjectId('group_id')",
  "stop_number": 1, // 1 to 20 (strict ordering)
  "destination_name": "Manali Old Town",
  "arrival_datetime": "2027-06-02T10:00:00Z",
  "departure_datetime": "2027-06-04T08:00:00Z",
  "transport_mode": "Private 4x4 Tempo Traveler",
  "transport_details": "Vehicle: Force Traveler HP-01-A-1234. Driver: Rakesh (+919816012345)",
  "accommodation_name": "Cedar Heights Cottage",
  "accommodation_details": "2 Deluxe Wooden Cottages booked. Booking Ref: CH-9082",
  "google_maps_url": "https://maps.google.com/?q=Cedar+Heights+Manali",
  "notes": "Acclimatization day. Check tire pressures before Rohtang Pass departure.",
  "created_at": "2026-11-06T20:00:00Z",
  "updated_at": "2026-11-06T20:00:00Z"
}
```
- **Indexes:**
  - Compound Unique: `{"trip_id": 1, "stop_number": 1}`, `unique=True`

### 18.11 Collection: `notifications`
Transactional SMS communication history.

```json
{
  "_id": "ObjectId",
  "recipient_user_id": "ObjectId('user_id')",
  "phone_number": "+919876543210",
  "dlt_template_id": "1107168920192837465",
  "template_name": "EDT_REMINDER_01",
  "message_body": "EDITH TRP: Dear Prajwal, reminder for Dec-26 Kitty contribution of Rs 2000. Due by 10-Dec. Pay via UPI.",
  "status": "delivered", // "queued" | "sent" | "delivered" | "failed"
  "provider_message_id": "FAST2SMS-98231-A",
  "provider_response": {"status": "success"},
  "error_message": null,
  "sent_at": "2026-12-07T09:00:00Z",
  "created_at": "2026-12-07T09:00:00Z"
}
```
- **Indexes:**
  - `{"recipient_user_id": 1, "created_at": -1}`

### 18.12 Collection: `audit_logs`
Immutable record of all state mutations.

```json
{
  "_id": "ObjectId",
  "actor_user_id": "ObjectId('admin_user_id')",
  "action": "verify_contribution",
  "resource_type": "contributions",
  "resource_id": "ObjectId('contribution_id')",
  "previous_state": {"status": "submitted", "utr_reference": "432109876543"},
  "new_state": {"status": "verified", "verified_by": "ObjectId('admin_user_id')"},
  "ip_address": "198.51.100.42",
  "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4)",
  "timestamp": "2026-12-05T18:00:00Z"
}
```
- **Indexes:**
  - `{"resource_type": 1, "resource_id": 1}`
  - `{"timestamp": -1}`

---

## 19. Comprehensive REST API Specifications

All endpoints are prefixed with `/api/v1` and require standard JSON payloads. All protected routes require a valid HTTP Bearer JWT token (`Authorization: Bearer <token>`).

### 19.1 Authentication (`/auth`)

| Endpoint | Method | Auth | Description | Request Body | Response (Success) |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/auth/login` | `POST` | Public | Authenticate user & issue tokens | `{"email": "...", "password": "..."}` | `200 OK` + `{"access_token": "...", "token_type": "bearer", "user": {...}}` |
| `/auth/refresh` | `POST` | Refresh | Refresh expired access token | Empty (Cookie / Header) | `200 OK` + `{"access_token": "..."}` |
| `/auth/me` | `GET` | User | Get current logged-in profile | None | `200 OK` + User details object |
| `/auth/change-password` | `POST` | User | Update own password | `{"old_password": "...", "new_password": "..."}` | `200 OK` + `{"message": "Password updated"}` |
| `/auth/logout` | `POST` | User | Revoke active session | Empty | `200 OK` + `{"message": "Logged out"}` |

### 19.2 Administration & Group Management (`/admin`)

| Endpoint | Method | Auth | Description | Request Body / Parameters | Response (Success) |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/admin/users` | `GET` | Admin | List all 4 members with status | None | `200 OK` + Array of User objects |
| `/admin/users/{id}/reset-password` | `POST` | Admin | Issue one-time password reset token | None | `200 OK` + `{"temp_token": "...", "expires_at": "..."}` |
| `/admin/group/settings` | `GET` | Admin | Get group target configurations | None | `200 OK` + Group configuration object |
| `/admin/group/settings` | `PUT` | Admin | Update monthly target or dates | `{"monthly_target": 250000, "duration": 12}` | `200 OK` + Updated Group object |
| `/admin/audit-logs` | `GET` | Admin | Query filterable audit trail | `?limit=50&resource_type=contributions` | `200 OK` + Array of AuditLog objects |

### 19.3 Savings Kitty Module (`/kitty`)

| Endpoint | Method | Auth | Description | Request Body / Parameters | Response (Success) |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/kitty/summary` | `GET` | User | Get total verified savings & progress | None | `200 OK` + `{"total_verified_paise": 4800000, "target_paise": 9600000, "progress_pct": 50.0}` |
| `/kitty/contributions/my` | `GET` | User | Get current user's 12-month records | None | `200 OK` + Array of User's Contributions |
| `/kitty/contributions/all` | `GET` | Admin | Get full matrix of all 4 members | None | `200 OK` + 48 Contribution records |
| `/kitty/contributions/{id}/submit` | `POST` | User | Submit UTR reference & proof | `{"utr_reference": "432109876543", "proof_url": "..."}` | `200 OK` + Updated Contribution (`submitted`) |
| `/kitty/contributions/{id}/verify` | `PUT` | Admin | Approve & credit contribution | Empty | `200 OK` + Updated Contribution (`verified`) |
| `/kitty/contributions/{id}/reject` | `PUT` | Admin | Reject submitted contribution | `{"reason": "UTR not found in bank statement"}` | `200 OK` + Updated Contribution (`rejected`) |
| `/kitty/disbursements` | `POST` | Admin | Log common expense from Kitty | `{"amount_paise": 500000, "category": "stay", "description": "Villa advance", "recipient": "Homestay"}` | `201 Created` + KittyTransaction object |
| `/kitty/reconcile` | `POST` | Admin | Record physical bank reconciliation | `{"actual_bank_paise": 4300000, "notes": "Statement audit"}` | `200 OK` + Reconciliation status & variance |

### 19.4 Kitty Split — Shared Expenses (`/expenses`)

| Endpoint | Method | Auth | Description | Request Body / Parameters | Response (Success) |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/expenses` | `GET` | User | List all shared trip expenses | `?trip_id=...` | `200 OK` + Array of Expense objects with splits |
| `/expenses` | `POST` | User | Record new personal shared expense | `{"payer_id": "...", "total_amount": 400000, "split_method": "equal", "participants": ["id1", "id2"], "description": "Dinner"}` | `201 Created` + Expense object with splits |
| `/expenses/{id}` | `GET` | User | Get details of a single expense | None | `200 OK` + Expense object |
| `/expenses/{id}/reverse` | `POST` | Admin/Payer | Reverse expense with audit record | `{"reason": "Entered duplicate amount"}` | `200 OK` + `{"message": "Expense reversed"}` |
| `/balances` | `GET` | User | Get net balances for all members | None | `200 OK` + `{"balances": [{"user_id": "...", "net_paise": 150000}]}` |
| `/settlements/suggested` | `GET` | User | Get simplified settlement plan | None | `200 OK` + Array of suggested transfers |
| `/settlements/propose` | `POST` | User | Record settlement payment | `{"creditor_id": "...", "amount": 100000, "utr_reference": "..."}` | `201 Created` + Settlement object (`proposed`) |
| `/settlements/{id}/confirm` | `PUT` | Creditor/Admin| Confirm settlement payment | Empty | `200 OK` + Settlement object (`confirmed`) |

### 19.5 Multi-Destination Trip Planner (`/trips`)

| Endpoint | Method | Auth | Description | Request Body / Parameters | Response (Success) |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/trips` | `GET` | User | Get master trip details & stops | None | `200 OK` + Trip object with embedded stops |
| `/trips/{id}/stops` | `POST` | Admin | Add new stop (up to 20) | `{"destination_name": "Kaza", "stop_number": 3, "arrival": "...", "transport_mode": "..."}` | `201 Created` + TripStop object |
| `/trips/{id}/stops/{stop_id}` | `PUT` | Admin | Update details of a stop | Stop fields JSON | `200 OK` + Updated TripStop object |
| `/trips/{id}/stops/{stop_id}` | `DELETE` | Admin | Remove a stop & re-sequence | None | `200 OK` + `{"message": "Stop deleted"}` |
| `/trips/{id}/stops/reorder` | `PUT` | Admin | Reorder stop sequence | `{"stop_order": ["stop_id_3", "stop_id_1", "stop_id_2"]}` | `200 OK` + Reordered stops array |

### 19.6 Notifications & SMS (`/notifications`)

| Endpoint | Method | Auth | Description | Request Body | Response (Success) |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/notifications/history` | `GET` | Admin | View SMS dispatch audit log | `?limit=50` | `200 OK` + Array of Notification logs |
| `/notifications/send-reminder`| `POST`| Admin | Trigger manual dues reminder | `{"month_index": 1, "user_id": "..."}` | `200 OK` + Dispatch result |
| `/notifications/webhook` | `POST` | Public/IP-Restricted | Gateway delivery receipt callback | Gateway JSON payload | `200 OK` + `{"status": "received"}` |

---

## 20. Mathematical Models, Split Algorithms & Financial Integrity

### 20.1 Integer Minor-Unit Currency Representation

All financial calculations strictly utilize 64-bit signed integers representing **paise** ($1\text{ INR} = 100\text{ paise}$).
- ₹2,000.00 is stored as `200000`
- ₹0.01 is stored as `1`
- Floating-point representations (`float`, `double`) are banned from database storage, API schemas, and calculation functions.

```python
# Conversion Utility Standard
def rupees_to_paise(rupees: float | str) -> int:
    from decimal import Decimal, ROUND_HALF_UP
    return int((Decimal(str(rupees)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def paise_to_rupees_str(paise: int) -> str:
    sign = "-" if paise < 0 else ""
    abs_paise = abs(paise)
    rupees = abs_paise // 100
    cents = abs_paise % 100
    return f"{sign}₹{rupees:,}.{cents:02d}"
```

---

### 20.2 Deterministic Expense Splitting & Remainder Allocation

When dividing an expense among $k$ participants where the total amount in paise $T$ is not cleanly divisible by $k$, integer division yields a quotient and a remainder:

$$q = \lfloor T / k \rfloor, \quad r = T \pmod k$$

Where $0 \le r < k$. To ensure that $\sum_{i=1}^{k} \text{Share}_i = T$ exactly down to the last paisa:
- The first $r$ participants receive a share of $q + 1$ paise.
- The remaining $k - r$ participants receive a share of $q$ paise.
- Participants are ordered deterministically by their static user ID string to eliminate non-deterministic assignment.

#### Python Implementation:

```python
def calculate_equal_split(total_paise: int, participant_ids: list[str]) -> dict[str, int]:
    if not participant_ids:
        raise ValueError("Participant list cannot be empty.")
    
    # Sort IDs deterministically
    sorted_participants = sorted(participant_ids)
    k = len(sorted_participants)
    q = total_paise // k
    r = total_paise % k
    
    splits = {}
    for index, user_id in enumerate(sorted_participants):
        splits[user_id] = q + (1 if index < r else 0)
        
    assert sum(splits.values()) == total_paise, "Split sum must equal total exactly."
    return splits
```

---

### 20.3 Minimum Cash Flow Settlement Simplification Algorithm

To settle peer balances among 4 members, an arbitrary set of multi-party debts can be resolved in at most $N - 1 = 3$ transactions using the greedy Minimum Cash Flow algorithm.

#### Mathematical Steps:
1. Compute each member's net position $B_i$:
   $$B_i = \sum \text{Paid By } i - \sum \text{Owed By } i$$
   Note that $\sum_{i=1}^{N} B_i = 0$.
2. Separate members into **Debtors** ($B_i < 0$) and **Creditors** ($B_i > 0$).
3. Greedily match the debtor with the largest debt to the creditor with the largest credit:
   $$\text{Transfer Amount} = \min(|B_{\text{max\_debtor}}|, B_{\text{max\_creditor}})$$
4. Update net balances and repeat until all balances reach zero.

#### Python Implementation:

```python
from dataclasses import dataclass

@dataclass
class SettlementTransfer:
    debtor_id: str
    creditor_id: str
    amount_paise: int

def solve_minimum_cash_flow(net_balances: dict[str, int]) -> list[SettlementTransfer]:
    # Ensure zero-sum invariant
    assert sum(net_balances.values()) == 0, "Sum of net balances must equal 0."
    
    debtors = []   # (abs(balance), user_id)
    creditors = [] # (balance, user_id)
    
    for user_id, balance in net_balances.items():
        if balance < 0:
            debtors.append([-balance, user_id])
        elif balance > 0:
            creditors.append([balance, user_id])
            
    transfers = []
    
    while debtors and creditors:
        debtors.sort(key=lambda x: x[0], reverse=True)
        creditors.sort(key=lambda x: x[0], reverse=True)
        
        max_debtor = debtors[0]
        max_creditor = creditors[0]
        
        settle_amount = min(max_debtor[0], max_creditor[0])
        
        transfers.append(SettlementTransfer(
            debtor_id=max_debtor[1],
            creditor_id=max_creditor[1],
            amount_paise=settle_amount
        ))
        
        max_debtor[0] -= settle_amount
        max_creditor[0] -= settle_amount
        
        if max_debtor[0] == 0:
            debtors.pop(0)
        if max_creditor[0] == 0:
            creditors.pop(0)
            
    return transfers
```

#### Worked Example:
Suppose 4 members have the following net positions after a week of travel:
- Member A: $+₹4,500$ ($+450000$ paise)
- Member B: $+₹1,500$ ($+150000$ paise)
- Member C: $-₹2,000$ ($-200000$ paise)
- Member D: $-₹4,000$ ($-400000$ paise)

Algorithm Execution:
1. Max Debtor D owes $₹4,000$; Max Creditor A is owed $₹4,500$.  
   $
ightarrow$ **Transfer 1:** D pays A **₹4,000**. (D cleared, A now owed $+₹500$).
2. Max Debtor C owes $₹2,000$; Max Creditor B is owed $₹1,500$.  
   $
ightarrow$ **Transfer 2:** C pays B **₹1,500**. (B cleared, C now owes $-₹500$).
3. Remaining Debtor C owes $₹500$; Remaining Creditor A is owed $₹500$.  
   $
ightarrow$ **Transfer 3:** C pays A **₹500**. (All balances cleared).

**Result:** Only 3 simple transactions resolve all debts across the group.

---

### 20.4 Kitty Accounting Invariant & Reconciliation Formula

The verified balance of the collective Kitty at time $t$, denoted $B_{\text{kitty}}(t)$, is mathematically derived from the ledger:

$$B_{\text{kitty}}(t) = \sum_{c \in \text{Verified}} \text{Amount}(c) - \sum_{d \in \text{Disbursed}} \text{Amount}(d) + \sum_{a \in \text{Adjustments}} \text{Amount}(a)$$

#### Invariant Constraints:
1. Non-Negative Pool: $B_{\text{kitty}}(t) \ge 0$ at all times. A disbursement exceeding the current balance is rejected.
2. Custodian Audit Variance:
   $$\Delta_{\text{reconciliation}} = \text{Actual Bank/Cash Funds} - B_{\text{kitty}}(t)$$
   If $\Delta 
e 0$, the system flags a reconciliation variance, requiring an authorized adjustment entry with an audit explanation.

---

## 21. User Interface & Frontend Screen Specifications

The UI is built with lightweight, responsive HTML5/CSS3/Vanilla JS optimized for mobile viewports (360px–480px) and desktop monitors (1024px+).

```text
+-------------------------------------------------------------+
|  EDITH-TRIP MANAGER          [₹48,000 / ₹96,000]   [Logout] |
+-------------------------------------------------------------+
|  [ Dashboard ]  [ Savings Kitty ]  [ Kitty Split ]  [ Trip ]|
+-------------------------------------------------------------+
|                                                             |
|  +-------------------------------------------------------+  |
|  |  SAVINGS PROGRESS: 50%                     (Month 6)  |  |
|  |  [===========================                         ]  |  |
|  |  Verified: ₹48,000.00         Remaining: ₹48,000.00   |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  +---------------------------+  +------------------------+  |
|  | YOUR STATUS: Month 6      |  | UPCOMING EXPEDITION    |  |
|  | [ SUBMIT PAYMENT PROOF ]  |  | Days to Go: 142 Days   |  |
|  | Due Date: 10-Dec-2026     |  | Stops Planned: 6 Stops |  |
|  +---------------------------+  +------------------------+  |
|                                                             |
|  +-------------------------------------------------------+  |
|  |  KITTY SPLIT QUICK-VIEW                                |  |
|  |  Your Net Position: +₹1,250.00 (You are owed money)   |  |
|  |  [ + Record Shared Expense ]    [ View Settlements ]  |  |
|  +-------------------------------------------------------+  |
+-------------------------------------------------------------+
```

### Detailed Screen Specifications:

1. **Screen 1: Authentication & Perimeter Gate**
   - Clean, dark-mode responsive login form.
   - Email, password, and optional Cloudflare Access SSO redirect.
   - Error toast display with rate-limit warnings.
2. **Screen 2: Consolidated Executive Dashboard**
   - Hero metric card: Total verified savings vs target.
   - Monthly progress bar with milestone indicators.
   - User-specific action banner (e.g., "Month 6 Contribution Pending - Submit Now").
   - Quick glance at trip itinerary and personal split balance.
3. **Screen 3: Savings Kitty Module**
   - **Member View:** 12-month accordion displaying user's personal payment history, status badges (`Verified`, `Submitted`, `Pending`), and UTR submission modal.
   - **Admin Verification Drawer:** Pending submission queue showing member name, payment date, UTR number, and proof thumbnail, with one-click "Verify" and "Reject" buttons.
   - **Disbursement Ledger:** Tab showing common expenses paid from the kitty with category tags and receipts.
4. **Screen 4: Kitty Split Module**
   - Expense stream sorted by date descending.
   - "+ Add Expense" slide-over modal:
     - Amount in ₹, description, date picker, category dropdown.
     - Payer selector (radio buttons).
     - Participant multi-select checkboxes.
     - Split method tabs: Equal, Exact (₹ per person), Percentage (% per person). Real-time sum validation indicator (turns green when $\sum = \text{Total}$).
   - Balances tab: Bar chart of net member positions (+ Green / - Red).
   - "Settle Up" modal: List of suggested minimum transfers with "Record Transfer" and "Confirm Receipt" buttons.
5. **Screen 5: Multi-Destination Trip Planner**
   - Chronological vertical timeline card layout.
   - Each card highlights: Destination name, Stop sequence badge (#1 to #20), Arrival/Departure timestamps, Transport badge (flight, train, van), Stay name, and expandable Notes.
   - Direct Google Maps launcher button.
   - Admin Controls: "Edit Stop", "Add Stop", and drag handles for reordering.
6. **Screen 6: Admin Console & Audit Log**
   - Member management table: Name, email, phone, role, custodian toggle, and reset password trigger.
   - Custodian Reconciliation Tool: Enter actual bank balance, auto-calculate variance, and record audit adjustment.
   - Searchable, filterable audit log stream with JSON state diff viewer.

---

## 22. Indian DLT & SMS Gateway Integration Specifications

To comply with the Telecom Regulatory Authority of India (TRAI) TCCCPR regulations, all SMS messages must be sent through a registered Principal Entity (PE) with approved Header/Sender IDs and pre-registered DLT Content Templates.

### 22.1 DLT Registration Parameters
- **Principal Entity (PE):** EDITH Group
- **Sender ID / Header:** `EDTTRP` (Transactional / Service Implicit)
- **Telecom Operators Supported:** Airtel, Jio, Vodafone Idea, BSNL

### 22.2 Approved DLT Content Templates

#### Template 1: Monthly Contribution Reminder
- **Template ID:** `1107168920192837461`
- **Template Name:** `EDT_REMINDER_01`
- **DLT Pattern:**  
  `EDITH TRP: Dear {#var#}, your monthly trip contribution of Rs {#var#} for {#var#} is due on {#var#}. Please pay via UPI to {#var#}. - EDITH`
- **Sample Text:**  
  *EDITH TRP: Dear Prajwal, your monthly trip contribution of Rs 2000 for Dec-2026 is due on 10-Dec. Please pay via UPI to custodian@okhdfcbank. - EDITH*

#### Template 2: Contribution Verified
- **Template ID:** `1107168920192837462`
- **Template Name:** `EDT_VERIFIED_02`
- **DLT Pattern:**  
  `EDITH TRP: Hi {#var#}, your trip contribution of Rs {#var#} with Ref {#var#} has been verified and added to the Kitty. Current Total: Rs {#var#}. - EDITH`

#### Template 3: Contribution Rejected
- **Template ID:** `1107168920192837463`
- **Template Name:** `EDT_REJECTED_03`
- **DLT Pattern:**  
  `EDITH TRP: Hi {#var#}, your submission for Rs {#var#} could not be verified. Reason: {#var#}. Please update in the app. - EDITH`

#### Template 4: New Shared Expense Logged
- **Template ID:** `1107168920192837464`
- **Template Name:** `EDT_EXPENSE_04`
- **DLT Pattern:**  
  `EDITH TRP: {#var#} paid Rs {#var#} for {#var#}. Your share is Rs {#var#}. Check details in EDITH App. - EDITH`

#### Template 5: Settlement Confirmation
- **Template ID:** `1107168920192837465`
- **Template Name:** `EDT_SETTLE_05`
- **DLT Pattern:**  
  `EDITH TRP: Settlement of Rs {#var#} from {#var#} to {#var#} has been confirmed. Balance updated. - EDITH`

#### Template 6: Itinerary Modification Alert
- **Template ID:** `1107168920192837466`
- **Template Name:** `EDT_ITINERARY_06`
- **DLT Pattern:**  
  `EDITH TRP: Trip Itinerary updated by Admin. Destination: {#var#}. Check app for transit and stay details. - EDITH`

### 22.3 Gateway Client Payload & Webhook Handling

```python
# SMS Dispatch Payload Example (Fast2SMS / Msg91 DLT Standard)
sms_payload = {
    "sender_id": "EDTTRP",
    "template_id": "1107168920192837461",
    "variables_values": "Prajwal|2000|Dec-2026|10-Dec|custodian@upi",
    "route": "dlt",
    "numbers": "9876543210"
}
```
- **Webhook Status Callback:** The gateway posts delivery status (`DELIVRD`, `UNDELIV`, `REJECTD`) to `/api/v1/notifications/webhook`. The backend updates the corresponding document in `notifications` to maintain deliverability logs.

---

## 23. Security Architecture & Access Control Implementation

### 23.1 Multi-Layer Defense Architecture

```mermaid
flowchart TD
    Req[Incoming Client Request] --> L1[Layer 1: Cloudflare Access]
    L1 -->|Verified Email Header| L2[Layer 2: NGINX TLS Termination & Rate Limiting]
    L2 -->|Reverse Proxy| L3[Layer 3: FastAPI JWT Bearer Auth Guard]
    L3 -->|Valid Token Claims| L4[Layer 4: Role-Based Access Dependency]
    L4 -->|Authorized Role| L5[Layer 5: Database Query Filter & Scrubber]
    L5 --> DB[(MongoDB Storage)]
```

1. **Layer 1: Cloudflare Access:** External requests must authenticate against an email allowlist before network packets hit the server.
2. **Layer 2: NGINX TLS 1.3 Termination & Rate Limiter:** Enforces TLS 1.3, strict security headers (HSTS, CSP, X-Frame-Options), and throttles requests to 10 req/s per IP.
3. **Layer 3: FastAPI JWT Bearer Guard:** Decodes and validates HS256 JWT tokens. Verifies signature, expiration (`exp`), and active user status.
4. **Layer 4: Role-Based Access Dependency:** Route decorators (`@require_admin`, `@require_custodian`) reject unauthorized attempts with `HTTP 403 Forbidden`.
5. **Layer 5: Field-Level Query Filter:** Ensures group members cannot access other members' private records even if they manipulate request parameters.

### 23.2 FastAPI Authorization Dependency Example

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.models.user import User
from app.security import decode_access_token
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await db.users.find_one({"_id": payload["sub"], "is_active": True})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return User(**user)

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator privileges required")
    return current_user
```

---

## 24. Comprehensive Test Plan & Verification Matrix

| Test ID | Test Category | Target Component | Input / Precondition | Expected Behavior |
| :---: | :--- | :--- | :--- | :--- |
| **TEST-01** | Arithmetic | `calculate_equal_split` | Total: ₹100.00 (10,000 paise), Participants: 3 | Shares: 3334, 3333, 3333 paise. $\sum = 10,000$. |
| **TEST-02** | Arithmetic | `calculate_equal_split` | Total: ₹1.00 (100 paise), Participants: 4 | Shares: 25, 25, 25, 25 paise. $\sum = 100$. |
| **TEST-03** | Arithmetic | `calculate_equal_split` | Total: 1 paisa, Participants: 3 | Shares: 1, 0, 0 paise. $\sum = 1$. |
| **TEST-04** | Solver | `solve_minimum_cash_flow` | 4 members with complex net balances | Returns $\le 3$ transfers; all balances zero out. |
| **TEST-05** | Solver | `solve_minimum_cash_flow` | All net balances already ₹0.00 | Returns empty transfer list `[]`. |
| **TEST-06** | Accounting | Kitty Invariant | Disbursement exceeding verified balance | Rejection with `HTTP 400 Insufficient Kitty Balance`. |
| **TEST-07** | Security | Endpoint Authorization | Non-admin user calls `PUT /kitty/contributions/{id}/verify` | Rejection with `HTTP 403 Forbidden`. |
| **TEST-08** | Security | IDOR Privacy Leak | Non-admin user calls `GET /kitty/contributions/all` | Rejection with `HTTP 403 Forbidden`. |
| **TEST-09** | Security | Query Injection | Non-admin user calls `/kitty/contributions/my` with spoofed `user_id` query param | Server ignores param and uses JWT `sub` ID. |
| **TEST-10** | Data | Duplicate UTR | Member attempts to submit an already-used 12-digit UTR | Rejection with `HTTP 409 Conflict: UTR already registered`. |
| **TEST-11** | Data | Itinerary Reorder | Admin reorders 6 stops | Sequence numbers update cleanly without duplication. |
| **TEST-12** | Settlement | Two-Phase Settlement | Debtor proposes settlement; Creditor checks balance | Balance does not clear until Creditor confirms. |
| **TEST-13** | Audit | Ledger Mutation | Admin adjusts balance by ₹500 | `audit_logs` records old balance, new balance, reason. |
| **TEST-14** | SMS | Reminder Dispatch | Scheduled job executes on 1st of month | Notifications created with `pending` status for all 4. |

---

## 25. Cloud Infrastructure, Deployment & DevOps Runbook

### 25.1 Production Dockerfile

```dockerfile
# Multi-stage production build
FROM python:3.12-slim AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final runtime image
FROM python:3.12-slim AS runner

WORKDIR /app
COPY --from=builder /install /usr/local
COPY ./app ./app
COPY ./frontend ./frontend

# Run unprivileged user for security
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
```

### 25.2 Docker Compose Configuration

```yaml
version: '3.8'

services:
  web:
    build: .
    container_name: edith_trip_app
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - MONGODB_URI=mongodb+srv://${MONGO_USER}:${MONGO_PASS}@cluster0.mongodb.net/edith_trip?retryWrites=true&w=majority
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - JWT_ALGORITHM=HS256
      - ACCESS_TOKEN_EXPIRE_MINUTES=30
      - REFRESH_TOKEN_EXPIRE_DAYS=7
      - SMS_GATEWAY_API_KEY=${SMS_GATEWAY_API_KEY}
      - SMS_SENDER_ID=EDTTRP
      - CLOUDFLARE_ACCESS_AUD=${CLOUDFLARE_ACCESS_AUD}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### 25.3 Environment Variables Reference (`.env.example`)

```bash
# Core Environment
ENVIRONMENT=production
DEBUG=False
APP_NAME="EDITH-TRIP MANAGER"

# MongoDB Database Connection
MONGODB_URI="mongodb+srv://<username>:<password>@cluster0.mongodb.net/edith_trip?retryWrites=true&w=majority"
DB_NAME="edith_trip"

# Security & Tokens
JWT_SECRET_KEY="generate-a-cryptographically-secure-64-char-hex-key"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Indian DLT SMS Gateway Configuration
SMS_GATEWAY_URL="https://www.fast2sms.com/dev/bulkV2"
SMS_GATEWAY_API_KEY="your-registered-sms-gateway-api-key"
SMS_SENDER_ID="EDTTRP"
SMS_ENTITY_ID="your-principal-entity-id"

# Cloudflare Zero Trust Integration
CLOUDFLARE_ACCESS_TEAM="edith-team"
CLOUDFLARE_ACCESS_AUD="your-cloudflare-access-audience-tag"

# Initial Group & Admin Seed Parameters
ADMIN_EMAIL="admin@example.com"
ADMIN_INITIAL_PASSWORD="ChangeMeOnFirstLogin2026!"
ADMIN_PHONE="+919876543210"
MONTHLY_CONTRIBUTION_INR=2000
SAVINGS_DURATION_MONTHS=12
```

### 25.4 Automated Database Backup & Disaster Recovery Runbook

```bash
#!/usr/bin/env bash
# backup_database.sh - Automated daily encrypted backup to S3-compatible storage
set -euo pipefail

BACKUP_DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/tmp/edith_backup_${BACKUP_DATE}"
ENCRYPTED_ARCHIVE="/tmp/edith_backup_${BACKUP_DATE}.tar.gz.enc"

echo "Starting MongoDB Atlas snapshot export..."
mongodump --uri="${MONGODB_URI}" --out="${BACKUP_DIR}"

echo "Compressing and encrypting backup archive..."
tar -czf - -C "${BACKUP_DIR}" . | openssl enc -aes-256-cbc -salt -pbkdf2 -pass env:BACKUP_PASSPHRASE -out "${ENCRYPTED_ARCHIVE}"

echo "Uploading encrypted backup to offsite storage..."
# aws s3 cp "${ENCRYPTED_ARCHIVE}" s3://edith-trip-backups/backups/

echo "Cleaning up temporary files..."
rm -rf "${BACKUP_DIR}" "${ENCRYPTED_ARCHIVE}"
echo "Backup completed successfully."
```

---

## 26. Engineering Roadmap, Milestones & Definition of Done

### 26.1 Sprint Breakdown

| Sprint | Timeline | Objectives | Primary Deliverables |
| :---: | :---: | :--- | :--- |
| **Sprint 1** | Week 1–2 | Foundation, Security, Models | DB connection, Pydantic schemas, Auth endpoints, Seed script. |
| **Sprint 2** | Week 3–4 | Savings Kitty & Accounting | Rollover scheduler, UTR submission, Admin verification, Integer math. |
| **Sprint 3** | Week 5–6 | Kitty Split & Settlements | Expense creation, Equal/Exact/Pct splits, Min Cash Flow solver, 2-phase settle. |
| **Sprint 4** | Week 7–8 | Trip Planner & DLT SMS | 20-stop timeline, Drag-and-drop reorder, SMS client & webhooks. |
| **Sprint 5** | Week 9–10 | Hardening & Production Go-Live| Cloudflare Access integration, Docker containerization, End-to-end tests. |

### 26.2 Definition of Done (DoD) Checklist

For any feature or module to be marked **Done**:
- [ ] Code is implemented according to specifications in this PRD.
- [ ] Pydantic schemas enforce strict validation with zero floating-point math for money.
- [ ] Pytest unit and integration tests written and passing with $>90\%$ branch coverage.
- [ ] Role-Based Access Control (RBAC) verified with tests proving non-admin users cannot access admin actions or peer private data.
- [ ] All financial state mutations produce an immutable entry in `audit_logs`.
- [ ] Frontend UI conforms to mobile responsiveness (360px tested) with accessible interactive controls.
- [ ] API routes documented and testable via FastAPI OpenAPI Swagger docs (`/docs`).
- [ ] Code formatted with `black` and linted with `ruff`.
- [ ] Production Docker build passes without warnings or vulnerabilities.

---

*This document represents the complete, definitive, and approved Product Requirements Document (PRD) Version 2.0 for EDITH-TRIP MANAGER. All technical implementation, database modeling, API development, test authoring, and cloud deployments must adhere strictly to these specifications.*
