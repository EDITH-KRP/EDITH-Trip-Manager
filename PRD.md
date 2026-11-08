# EDITH-TRIP MANAGER

## Product Requirements Document (PRD)

**Version:** 1.0\
**Product type:** Private, cloud-hosted web application\
**Target users:** Four friends (one administrator and three members)

## 1. Product Overview

EDITH-TRIP MANAGER is a private web application for four friends to save
money together, plan multi-destination trips, record shared expenses,
and settle balances transparently.

Core modules: 1. **Savings Kitty:** Monthly contributions, verification,
group collection progress, withdrawals, and reconciliation. 2. **Kitty
Split:** Shared trip expenses, participant-based splits, balances, and
settlements. 3. **Trip Planner:** Multiple destinations, dates,
transportation, accommodation, and notes. 4. **Administration:** Member
accounts, group settings, financial oversight, and audit history. 5.
**Notifications:** Ordinary SMS reminders and important updates.

The application records money movements. It does not hold funds or
initiate bank transfers.

## 2. Problem Statement

Managing group savings and trip expenses through spreadsheets, chat
messages, and manual calculations can lead to missed contributions,
unclear balances, duplicate records, and confusion between personal
payments and kitty-funded expenses. This application provides one
reliable source of truth.

## 3. Goals and Success Criteria

  -----------------------------------------------------------------------
  Goal                                Success criteria
  ----------------------------------- -----------------------------------
  Savings transparency                All members see total kitty
                                      collections and group progress.

  Individual privacy                  Members cannot see another member's
                                      individual savings records.

  Expense accuracy                    Every shared expense has a
                                      traceable payer and split.

  No double counting                  Kitty-funded expenses never appear
                                      as personal advances.

  Trip coordination                   Admin can maintain up to 20 trip
                                      stops.

  Access security                     Only approved members can access
                                      the application.

  Notifications                       SMS reminders and alerts can be
                                      sent.

  Accountability                      Financial changes have an audit
                                      history.
  -----------------------------------------------------------------------

### Initial Financial Target

  Parameter                               Value
  --------------------------------- -----------
  Members                                     4
  Monthly contribution per member        ₹2,000
  Saving period                       12 months
  Total target                          ₹96,000

**Calculation:** ₹2,000 × 4 × 12 = ₹96,000. The administrator can
configure the contribution amount and duration.

## 4. Users and Roles

### Administrator

One member is the sole administrator. The administrator can: - Create,
invite, and manage member accounts. - Configure group settings and
contribution rules. - Maintain the official trip itinerary. - Verify
contributions and record kitty withdrawals. - Reconcile the kitty
balance. - Review shared expenses, settlements, and audit history.

### Group Members

The other three members can: - View total group savings and target
progress. - View their own contribution history. - View shared trip
expenses and balances. - Add personal payments toward shared expenses. -
View the itinerary and receive SMS notifications.

Members cannot view another member's private savings records, change
group settings, manage roles, or delete financial records.

### Kitty Custodian

One designated member physically holds the collected funds. This may be
the administrator or another member. The application records the
custodian but does not hold or transfer money.

## 5. Functional Requirements

### 5.1 Savings Kitty

  -----------------------------------------------------------------------
  ID                      Requirement             Priority
  ----------------------- ----------------------- -----------------------
  KIT-01                  Configure monthly       Must
                          contribution amount.    

  KIT-02                  Configure savings       Must
                          duration.               

  KIT-03                  Generate monthly        Must
                          contribution records    
                          for all members.        

  KIT-04                  Track pending,          Must
                          submitted, verified,    
                          and rejected            
                          contributions.          

  KIT-05                  Allow admin to verify   Must
                          received contributions. 

  KIT-06                  Display total verified  Must
                          group collections.      

  KIT-07                  Show each member their  Must
                          own contribution        
                          history.                

  KIT-08                  Show group-level        Must
                          monthly collection      
                          progress.               

  KIT-09                  Record kitty            Must
                          withdrawals and their   
                          purpose.                

  KIT-10                  Reconcile recorded      Must
                          balance against actual  
                          funds held.             

  KIT-11                  Maintain financial      Must
                          change history.         

  KIT-12                  Send monthly SMS        Should
                          reminders.              
  -----------------------------------------------------------------------

**Contribution lifecycle:** 1. The system generates a monthly
contribution obligation. 2. A member submits a payment record with date
and optional reference. 3. The administrator verifies receipt with the
custodian. 4. Only verified contributions increase the kitty balance. 5.
The administrator reconciles the recorded balance with actual funds.

**Privacy rules:** - All members see the total verified kitty amount. -
Each member sees their own contribution history. - Only the
administrator sees detailed contribution histories for all members. -
These restrictions must be enforced by backend authorization, not just
frontend visibility.

### 5.2 Kitty Split --- Shared Trip Expenses

  ID       Requirement                                         Priority
  -------- --------------------------------------------------- ----------
  EXP-01   Add a shared trip expense.                          Must
  EXP-02   Select the member who paid.                         Must
  EXP-03   Select participants who share the expense.          Must
  EXP-04   Support equal splits.                               Must
  EXP-05   Support custom amount splits.                       Must
  EXP-06   Support percentage splits.                          Must
  EXP-07   View shared expenses.                               Must
  EXP-08   Calculate each member's net balance.                Must
  EXP-09   Generate suggested settlements.                     Must
  EXP-10   Confirm settlement payments.                        Must
  EXP-11   Maintain expense and settlement history.            Must
  EXP-12   Correct or reverse expenses with an audit record.   Should

**Example:** One member pays ₹4,000 for a hotel shared equally by all
four members.

  Member      Share     Paid   Net position
  -------- -------- -------- --------------
  A          ₹1,000   ₹4,000        +₹3,000
  B          ₹1,000       ₹0        -₹1,000
  C          ₹1,000       ₹0        -₹1,000
  D          ₹1,000       ₹0        -₹1,000

A positive balance means the member should receive money; a negative
balance means the member owes money.

**Expense rules:** - Payer and participants may differ. -
Non-participants are not charged. - Custom amounts must total the
expense amount. - Percentages must total 100%. - Rounding must be
deterministic and fully reconciled. - Settlements affect balances only
after confirmation by the recipient or administrator. - Use precise
decimal or integer minor-unit arithmetic, never binary floating-point
for money.

### 5.3 Common Kitty Expenses

Expenses paid directly from the kitty use a separate kitty-disbursement
workflow. Examples include hotel advances, common transportation, and
group activities.

Rules: 1. Record amount, date, purpose, and the person who authorized or
made the payment. 2. Reduce the kitty balance by the disbursement
amount. 3. Show the transaction in the group financial summary. 4. Do
not create personal member debts for an expense already paid by the
kitty. 5. Do not also add the same expense to Kitty Split unless there
is a separate personal payment that must be shared.

  Transaction                           Kitty balance   Personal expense balances
  ------------------------------------- --------------- ---------------------------
  Member contributes ₹2,000             Increases       No change
  Member pays ₹4,000 for shared hotel   No change       Recalculated
  Kitty pays ₹4,000 for hotel           Decreases       No change

### 5.4 Trip Planner

The Trip Planner supports multiple destinations and stops.

Requirements: - Create a trip title and description. - Add, edit,
remove, and reorder destinations. - Record arrival and departure
dates. - Record transport and accommodation details. - Add notes and
useful links. - Display stops in chronological order. - Make the
itinerary visible to all group members.

The administrator manages the official itinerary; members can view it.

### 5.5 Dashboard

After login, show: - Total verified kitty balance and target. - Savings
progress and next contribution due date. - Upcoming trip date and number
of destinations. - Total shared trip expenses. - Outstanding balances
and suggested settlements. - Recent financial activity and
notifications.

Individual savings details remain private unless the logged-in user is
the administrator.

### 5.6 Notifications

Notifications use ordinary SMS, not WhatsApp.

  Event                                           Recipient
  ----------------------------------------------- ------------------
  Monthly contribution reminder                   Each member
  Contribution submitted, verified, or rejected   Relevant member
  New shared expense                              Group members
  Settlement proposed or confirmed                Relevant members
  Trip itinerary updated                          Group members
  Admin announcement                              Group members

The selected Indian SMS provider must support applicable DLT
registration, approved sender IDs, templates, and delivery reporting.

## 6. Access Control and Privacy

-   No public registration or public group discovery.
-   Accounts are created or approved by the administrator.
-   Authentication is required for all application data.
-   HTTPS is mandatory in production.
-   Secure password hashing, session expiry, and logout are required.
-   Backend role-based access control is mandatory.
-   Database access is restricted to the backend service.
-   Financial changes are auditable.

**Recommended access architecture:** Approved member email allowlist
through Cloudflare Access, followed by application authentication and
role authorization, then the FastAPI backend and private MongoDB
database.

A private URL alone is not sufficient security.

## 7. Non-Functional Requirements

  -----------------------------------------------------------------------
  Category                            Requirement
  ----------------------------------- -----------------------------------
  Security                            Password hashing, JWT
                                      authentication, backend
                                      authorization.

  Privacy                             Restrict individual savings records
                                      by role.

  Reliability                         Validate financial operations and
                                      preserve consistency.

  Performance                         Common dashboard operations should
                                      normally complete within 2 seconds
                                      under normal use.

  Usability                           Responsive desktop and mobile web
                                      interface.

  Availability                        Target 99% monthly availability
                                      after production deployment.

  Backup                              Automated backups and tested
                                      restoration.

  Auditability                        Record who created, changed,
                                      verified, or reversed financial
                                      transactions.

  Scalability                         Allow additional groups in a future
                                      version.

  Data integrity                      Use database transactions or
                                      equivalent consistency controls for
                                      financial updates.
  -----------------------------------------------------------------------

## 8. Technical Architecture

  Layer               Proposed technology
  ------------------- ---------------------------------------
  Frontend            HTML5, CSS3, Vanilla JavaScript
  Backend             Python 3.12 + FastAPI
  Database            MongoDB Atlas
  Authentication      JWT + Argon2 password hashing
  API                 REST with JSON
  Notifications       Indian SMS gateway
  Hosting             Cloud-hosted application
  Access protection   Cloudflare Access
  Scheduling          APScheduler or managed scheduled jobs
  Version control     Git and GitHub

### Proposed Project Structure

``` text
EDITH-TRIP-MANAGER/
├── frontend/
│   ├── index.html
│   ├── css/
│   └── js/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── admin.py
│   │   ├── groups.py
│   │   ├── kitty.py
│   │   ├── expenses.py
│   │   ├── settlements.py
│   │   └── trips.py
│   └── services/
│       ├── accounting.py
│       ├── notifications.py
│       └── audit.py
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

### Initial Database Collections

  -----------------------------------------------------------------------
  Collection                          Purpose
  ----------------------------------- -----------------------------------
  users                               Member accounts and roles.

  groups                              Group configuration and kitty
                                      target.

  memberships                         Group membership records.

  contributions                       Individual monthly contribution
                                      records.

  kitty_transactions                  Kitty collections, withdrawals, and
                                      adjustments.

  expenses                            Personally paid shared expenses.

  expense_splits                      Individual expense shares.

  settlements                         Proposed and confirmed repayments.

  trips                               Trip details.

  trip_stops                          Destination and stop details.

  notifications                       SMS delivery and notification
                                      history.

  audit_logs                          Financial and administrative
                                      activity history.
  -----------------------------------------------------------------------

Kitty transactions and personal expenses must remain separate. The kitty
balance is derived from verified collections, disbursements, and
authorized adjustments rather than manually overwritten.

## 9. Key Business Rules

1.  Maximum group size in version 1 is four members.
2.  One administrator controls the application.
3.  One member is designated as physical kitty custodian.
4.  A contribution counts only after verification.
5.  Pending or rejected contributions do not increase the kitty balance.
6.  Kitty-funded expenses are recorded only in the kitty ledger.
7.  Personally paid shared expenses are recorded in Kitty Split.
8.  Non-participants are not charged.
9.  Settlements change outstanding balances only after confirmation.
10. Financial records cannot be permanently deleted through normal user
    operations.
11. Corrections use reversals or adjustments with an audit trail.
12. Group-level finances are visible to members, but individual savings
    records are restricted.

## 10. Scope and Release Plan

### Phase 1 --- Foundation

-   Authentication and member management.
-   Group creation and access control.
-   Basic dashboard.
-   Multi-stop trip planner.
-   Personal shared-expense splitting.
-   Basic balances and settlements.

### Phase 2 --- Kitty Accounting Engine

-   Monthly contribution generation.
-   Contribution submission and verification.
-   Private individual contribution history.
-   Kitty collection and withdrawal ledger.
-   Custodian balance reconciliation.
-   Accounting audit history.

### Phase 3 --- Notifications

-   SMS provider integration.
-   Automated monthly reminders.
-   Expense and settlement alerts.
-   Delivery status tracking.

### Phase 4 --- Cloud Deployment

-   Production hosting.
-   MongoDB Atlas configuration.
-   HTTPS and Cloudflare Access.
-   Backup and recovery.
-   Security testing.

### Phase 5 --- Final Validation

-   Four-member end-to-end testing.
-   Accounting reconciliation tests.
-   Access-control testing.
-   Mobile usability testing.
-   Production readiness review.

## 11. Out of Scope for Version 1

-   Direct UPI or bank payment processing.
-   Automatic access to members' bank accounts.
-   Holding funds inside the application.
-   Public registration or public groups.
-   Direct hotel, flight, bus, or train booking.
-   Automatic ticket purchasing.
-   WhatsApp notifications.
-   AI-generated itineraries or expense predictions.

These may be considered for future versions.

## 12. Acceptance Criteria

  -----------------------------------------------------------------------
  Test                                Expected result
  ----------------------------------- -----------------------------------
  Four members contribute ₹2,000 each Verified kitty shows ₹8,000.

  Contribution submitted but not      Kitty total remains unchanged.
  verified                            

  Member requests another member's    Access is denied.
  contribution history                

  One member pays ₹4,000 shared by    Each person's share is ₹1,000.
  four people                         

  Kitty pays ₹4,000 for a hotel       Kitty reduces by ₹4,000; no
                                      personal debt is created.

  Member settles an outstanding       Balance changes after confirmation.
  amount                              

  Admin adds five destinations        All five appear in the correct
                                      order.

  Unapproved user opens the           Access is denied.
  application                         

  Financial record is corrected       Original record and correction
                                      remain auditable.
  -----------------------------------------------------------------------

## 13. Risks and Mitigations

  -----------------------------------------------------------------------
  Risk                                Mitigation
  ----------------------------------- -----------------------------------
  Incorrect contribution verification Admin verification and transaction
                                      history.

  Kitty balance differs from actual   Regular custodian reconciliation.
  funds                               

  Duplicate expense entries           Unique transaction references and
                                      duplicate checks.

  Unauthorized access to private data Backend authorization and privacy
                                      tests.

  Accidental financial record         Reversal-based accounting and audit
  deletion                            logs.

  SMS delivery failure                Retry mechanism and delivery
                                      status.

  Database or hosting failure         Automated backups and recovery
                                      testing.

  Incorrect settlement                Recalculate balances from verified
                                      transactions.
  -----------------------------------------------------------------------

## 14. Assumptions and Decisions

-   Four members, including the administrator.
-   ₹2,000 monthly contribution per member.
-   Twelve-month saving period.
-   Initial savings target of ₹96,000.
-   One designated physical kitty custodian.
-   All members see group-level kitty totals.
-   Individual savings records are private.
-   All members see shared trip expenses and balances.
-   Expense splits support equal, custom, and percentage methods.
-   Trips can contain multiple destinations.
-   SMS is the preferred notification channel.
-   The application is invite-only and cloud-hosted.
-   The application does not transfer or hold money.

## 15. Open Decisions Before Production

1.  **Contribution verification:** Should only the administrator verify
    contributions, or should the custodian also have permission?
2.  **Contribution evidence:** Should members upload a UPI screenshot or
    enter a transaction reference?
3.  **Kitty balance:** Will the custodian hold funds in a bank account,
    as cash, or both?
4.  **SMS identity:** Should notifications use each member's mobile
    number, visible only to the administrator?
5.  **Account recovery:** Should the administrator be able to reset a
    member's password?

## 16. Current Implementation Status

The existing v3 implementation is the starting point for this PRD, not a
completed production product.

  Component                                Status
  ---------------------------------------- -------------
  FastAPI backend foundation               Implemented
  Login and JWT authentication             Implemented
  Admin and group management               Implemented
  Multi-destination trip planner           Implemented
  Personal shared expenses                 Implemented
  Equal/custom/percentage splits           Implemented
  Basic balances and settlements           Implemented
  Monthly contribution ledger              Pending
  Kitty withdrawals and reconciliation     Pending
  Complete audit trail                     Pending
  SMS integration                          Pending
  Cloud deployment and access protection   Pending
  Live end-to-end testing                  Pending

## 17. Product Definition and Development Priority

**EDITH-TRIP MANAGER is a private group savings, trip planning, and
expense management platform---not a payment wallet, banking application,
or public travel-booking service.**

Complete the Kitty Accounting Engine before integrating SMS or deploying
the application. Financial correctness and privacy are the highest
priorities.

This PRD is the source of truth for development, database design, API
specifications, testing, and deployment.
