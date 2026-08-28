# Repository Structure Overview

## File Organization

```
galatiq-invoice-processing/
│
├── main.py                          # CLI entry point (async)
├── requirements.txt                 # Python dependencies
├── README.md                        # Project documentation
├── STRUCTURE.md                     # This file
├── .env.example                     # Environment variable template
├── .gitignore                       # Git ignore rules
│
├── src/                             # Main package
│   ├── __init__.py                 # Package exports
│   ├── config.py                   # Configuration (Pydantic Settings)
│   ├── models.py                   # Data models (Pydantic schemas)
│   │
│   ├── agents/                     # Four specialist agents
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseAgent (abstract class)
│   │   ├── ingestion.py            # Extracts invoice data
│   │   ├── validation.py           # Checks inventory
│   │   ├── approval.py             # Makes approval decisions
│   │   └── payment.py              # Processes payments
│   │
│   ├── orchestrator/               # Workflow coordination
│   │   ├── __init__.py
│   │   └── orchestrator.py         # InvoiceOrchestrator (star topology)
│   │
│   ├── database/                   # Data layer
│   │   ├── __init__.py
│   │   └── setup.py                # SQLite operations (create, query, check_stock)
│   │
│   └── utils/                      # Utilities
│       ├── __init__.py
│       └── logging.py              # Structured logging setup
│
├── data/
│   └── invoices/                   # Sample invoice data
│       ├── INV-1001.txt           # Normal order (pass)
│       ├── INV-1002.txt           # Quantity mismatch (fail validation)
│       ├── INV-1003.txt           # Out of stock (fail validation)
│       ├── INV-1004.txt           # High amount (requires review)
│       └── INV-1005.txt           # Normal order (pass)
│
└── tests/
    └── test_orchestrator.py        # Orchestrator unit tests
```

## Core Components

### 1. Configuration (`src/config.py`)
- Pydantic Settings for type-safe config
- Loads from `.env` file
- Provides paths, LLM settings, agent config

### 2. Data Models (`src/models.py`)
All communication between agents uses these Pydantic models:
- `ExtractedInvoice` — Ingestion output
- `LineItem` — Single line item
- `ValidationResult` — Validation findings
- `ApprovalResult` — Approval decision
- `PaymentResult` — Payment status
- `ProcessingResult` — Full pipeline output

### 3. Database Layer (`src/database/setup.py`)
- `create_inventory_database(db_path)` — Initialize SQLite
- `query_inventory(db_path, item_id)` — Look up item
- `check_stock(db_path, item_id, quantity)` — Verify availability

### 4. Base Agent (`src/agents/base.py`)
- Abstract class all agents inherit from
- Provides `execute()` interface
- Built-in logging wrapper (`log_execution()`)
- Error handling in `run()` method

### 5. Four Specialist Agents

#### IngestionAgent (`src/agents/ingestion.py`)
- **Input:** Invoice file path (PDF, TXT, JSON, CSV)
- **Output:** `ExtractedInvoice`
- **Methods:** `_extract_from_pdf()`, `_extract_from_text()`, etc.
- **Status:** Skeleton (implement parsers in Phase 2)

#### ValidationAgent (`src/agents/validation.py`)
- **Input:** `ExtractedInvoice`
- **Output:** `ValidationResult`
- **Checks:** 
  - Amount > 0
  - Each item exists in inventory
  - Quantity is in stock
  - No negative quantities
- **Status:** Fully implemented (uses database)

#### ApprovalAgent (`src/agents/approval.py`)
- **Input:** `ExtractedInvoice` + `ValidationResult`
- **Output:** `ApprovalResult`
- **Rules:**
  - Auto-reject if validation failed
  - Require manual review if amount > $10K
  - Generator-Critic loop (scaffold in place)
- **Status:** Basic rules implemented; LLM integration pending

#### PaymentAgent (`src/agents/payment.py`)
- **Input:** `ExtractedInvoice` + `ApprovalResult`
- **Output:** `PaymentResult`
- **Actions:**
  - If approved: Call mock payment API
  - If requires_review: Flag for manual approval
  - If rejected: Log rejection
- **Status:** Mock API scaffolded

### 6. Orchestrator (`src/orchestrator/orchestrator.py`)
- **Topology:** Star (all agents report to orchestrator)
- **Control:** Centralized (orchestrator decides stage transitions)
- **Workflow:**
  1. Ingestion Agent
  2. Validation Agent
  3. Approval Agent
  4. Payment Agent
- **Methods:**
  - `process_invoice(invoice_path)` — Single invoice
  - `process_batch(invoice_paths)` — Multiple invoices
- **Status:** Fully structured; ready for implementation

### 7. CLI Entry Point (`main.py`)
- Async argument parser
- Single invoice: `python main.py --invoice_path=...`
- Batch: `python main.py --batch --dir=...`
- Debug: `python main.py --debug`
- Formatted output + batch summary

## Design Patterns Applied

### Orchestrator-Workers (Phase 3.1)
- One orchestrator coordinates four specialists
- Each agent has one responsibility
- Scalable: Can add more agents without changing orchestrator logic

### Star Topology (Phase 2.3)
- All communication flows through orchestrator
- Linear communication cost: O(n) instead of O(n²)

### Code-Driven Planning (Phase 2.2)
- Fixed 4-stage workflow
- No dynamic discovery (yet)
- Ideal for MVP, upgrade to model-driven planning later

### Ephemeral Agents (Phase 2.4)
- Agents spawn once per invoice, discard after
- No memory between invoices
- Clean state for each request

### Structured Output (Phase 4.1)
- All agents use Pydantic models
- Type safety at runtime
- Schema enforcement with tool use

## What's Implemented

- [x] Project skeleton
- [x] Configuration system
- [x] Pydantic models (strong typing)
- [x] Database initialization + querying
- [x] Base agent class
- [x] Validation agent (complete logic)
- [x] Approval agent (basic rules + LLM scaffold)
- [x] Payment agent (mock API scaffold)
- [x] Orchestrator (workflow coordination)
- [x] CLI entry point
- [x] Sample invoices (5 test cases)
- [x] Logging setup (console + file)
- [x] Tests (scaffold)

## What's Next

### Phase 2: Implementation (4-5 hours)
1. **Ingestion Agent** — PDF + text parsing with LLM
2. **Generator-Critic Loop** — Approval confidence iteration
3. **Mock API** — Test payment success/failure paths
4. **End-to-End Tests** — Workflow validation

### Phase 3: Polish (1-2 hours)
1. Error recovery (retry logic)
2. Observability (trace logging per stage)
3. Code review + cleanup
4. README updates + deployment guide

### Phase 4: Ship (30 min)
1. Push to GitHub
2. Verify all commands work
3. Send repo link to Galatiq

## Running the System

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Process single invoice
python main.py --invoice_path=data/invoices/INV-1001.txt

# Process all invoices
python main.py --batch --dir=data/invoices

# Debug mode
python main.py --batch --debug
```

### Logs
- Console: Realtime INFO+ messages
- File: `logs/invoice_processing.log` (DEBUG+ messages)

## Tech Stack

- **Language:** Python 3.11+
- **Async:** asyncio (built-in)
- **Type Safety:** Pydantic v2
- **Database:** SQLite3 (built-in)
- **Framework:** LangGraph (when LLM integrated)
- **Logging:** Python logging (built-in)
- **Testing:** pytest + pytest-asyncio
- **CLI:** argparse (built-in)

## Key Design Decisions

1. **Async/await** — Enables concurrent agent execution
2. **Pydantic** — Type safety + schema validation
3. **Star topology** — Simple coordination, scales to 50+ agents
4. **Centralized control** — No deadlock, clear ownership
5. **Structured logging** — Observability for multi-agent debugging
6. **Separation of concerns** — Each agent has one job
7. **Code-driven planning** — Predictable, testable workflow

## Notes for Phase 2

- Ingestion will need LLM (Claude or Grok) for unstructured text parsing
- Approval loop can use Claude for reasoning (confidence scoring)
- Payment API is mocked (ready for real integration)
- Database schema can be extended (add unit_price, category, etc.)
- All agents should follow the same error-handling pattern
- Log all decisions for auditability (compliance requirement)

---

**Status:** MVP structure complete. Ready for Phase 2 (implementation).
