# Architecture Guide

## System Overview

**4-Stage Multi-Agent Invoice Processing System**

This is a production-grade system that automates invoice processing using:
- **LangGraph** for workflow orchestration
- **4 specialist agents** (Ingestion, Validation, Approval, Payment)
- **Claude LLM** with generator-critic loop for intelligent reasoning
- **SQLite** for inventory validation
- **Async/await** for high-performance parallel processing

## 4 Agents & Their Responsibilities

### Agent 1: Ingestion
**File:** `src/agents/ingestion.py`

Extracts structured data from invoice documents.

- **Inputs:** Invoice file (any format)
- **Outputs:** ExtractedInvoice (vendor, amount, items, due_date)
- **Formats Supported:** TXT, JSON, PDF, CSV, XML
- **Handles:** Missing fields, typos, unstructured text

**Key Methods:**
- `_extract_from_text()` - Regex-based parsing
- `_extract_from_json()` - JSON parsing
- `_extract_from_pdf()` - pdfplumber OCR
- `_extract_from_csv()` - DictReader parsing
- `_extract_from_xml()` - ElementTree parsing

### Agent 2: Validation
**File:** `src/agents/validation.py`

Validates extracted data against inventory database.

- **Inputs:** ExtractedInvoice
- **Outputs:** ValidationResult (is_valid, issues list)
- **Checks:**
  - Item exists in inventory
  - Quantity in stock
  - No negative quantities
  - Valid amounts

**Key Methods:**
- `execute()` - Main validation logic
- `query_inventory()` - Database queries
- `check_stock()` - Stock availability checks

### Agent 3: Approval (LLM-Powered)
**File:** `src/agents/approval.py`

Makes approval decisions using Claude LLM with generator-critic loop.

- **Inputs:** ExtractedInvoice + ValidationResult
- **Outputs:** ApprovalResult (approved, confidence, reasoning)
- **Decision Logic:**
  - Auto-reject if validation failed
  - Auto-reject if amount > $10K (requires manual review)
  - Use LLM reasoning for borderline cases

**Generator-Critic Loop (3 Phases):**
1. **Generate:** Claude proposes recommendation + analysis
2. **Critique:** Claude reviews recommendation for flaws
3. **Revise:** Claude refines based on critique (if needed)

**Output:** Approval decision with confidence score (0-1)

### Agent 4: Payment
**File:** `src/agents/payment.py`

Processes approved invoices or logs rejections.

- **Inputs:** ExtractedInvoice + ApprovalResult
- **Outputs:** PaymentResult (status, transaction_id, message)
- **States:**
  - `success` - Payment processed
  - `requires_review` - Needs human approval
  - `rejected` - Rejected with reason

## Orchestrator: LangGraph Workflow

**File:** `src/orchestrator/langgraph_orchestrator.py`

Uses **LangGraph StateGraph** to coordinate all agents.

**Workflow Flow:**
```
Ingestion → Validation → Approval → Payment → End
                ↓
            [Error Handling]
                ↓
              [End]
```

**Key Responsibilities:**
- State management (InvoiceProcessingState)
- Conditional routing (if validation fails → skip to end)
- Error handling (try/except in each node)
- Metrics collection (timing, success rates)
- Parallel processing (asyncio.gather with Semaphore)

## Data Flow Through Agents

```
Stage 1: Ingestion
  Input:  Invoice file (any format)
  Output: ExtractedInvoice
  {
    vendor: "TechSupplies Inc",
    amount: 5000.0,
    items: [LineItem(...)],
    due_date: "2026-02-15"
  }

Stage 2: Validation
  Input:  ExtractedInvoice
  Output: ValidationResult
  {
    is_valid: true,
    issues: [],
    total_issues: 0
  }

Stage 3: Approval (LLM)
  Input:  ExtractedInvoice + ValidationResult
  Output: ApprovalResult
  {
    is_approved: true,
    approval_confidence: 0.85,
    reasoning: "All items in stock, amount within threshold"
  }

Stage 4: Payment
  Input:  ExtractedInvoice + ApprovalResult
  Output: PaymentResult
  {
    status: "success",
    transaction_id: "TXN-TEC-12345",
    message: "Paid $5000.00 to TechSupplies Inc"
  }
```

## Database Schema

**File:** `src/database/setup.py`

SQLite inventory database with auto-seeding.

```sql
CREATE TABLE inventory (
  item_id TEXT PRIMARY KEY,
  item_name TEXT NOT NULL,
  stock INTEGER NOT NULL,
  unit_price REAL,
  category TEXT
)

-- Seed Data
WidgetA:  15 in stock @ $250/unit
WidgetB:  10 in stock @ $500/unit
GadgetX:  5 in stock @ $750/unit
FakeItem: 0 in stock (test case)
```

## LLM Integration

**File:** `src/llm.py`

Claude API integration with async support.

**Key Methods:**
- `reason_about_invoice()` - Phase 1: Generate recommendation
- `critique_approval()` - Phase 2: Critique recommendation
- `revise_approval()` - Phase 3: Revise based on critique

**Features:**
- AsyncAnthropic client (proper async/await)
- Graceful fallback to placeholders when API key missing
- Structured JSON responses
- Error handling with defaults

## Data Models

**File:** `src/models.py`

All data uses Pydantic for type safety and validation.

**Key Models:**
- `ExtractedInvoice` - Ingestion output
- `LineItem` - Individual line item
- `ValidationResult` - Validation findings
- `ApprovalResult` - Approval decision
- `PaymentResult` - Payment status
- `ProcessingResult` - Final pipeline output

## Key Design Patterns

### 1. Orchestrator-Workers Pattern
- One orchestrator coordinates 4 specialist agents
- Each agent has single responsibility
- Communication only through orchestrator
- Scalable (add agents without changing core logic)

### 2. Generator-Critic Loop
Self-correcting LLM reasoning:
1. Generate: Propose recommendation
2. Critique: Identify flaws
3. Revise: Refine based on critique

### 3. Star Topology
All communication flows through orchestrator:
- O(n) connections vs O(n²) mesh
- Deadlock prevention
- Simpler testing and debugging

### 4. State-Based Workflow
LangGraph StateGraph manages all state:
- Clear data flow between agents
- Conditional routing
- Error recovery
- Observable execution

## Configuration

**File:** `src/config.py`

Settings loaded from `.env`:

```env
# LLM Configuration
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# System Paths
DATABASE_PATH=inventory.db
INVOICES_DIR=data/invoices
LOGS_DIR=logs

# Agent Configuration
APPROVAL_THRESHOLD=10000.0
BATCH_CONCURRENCY=5
TIMEOUT_SECONDS=30
```

## Performance & Scaling

**Single Invoice:** ~10ms
**Batch (parallel):** 138+ invoices/second
**Batch (sequential):** ~1-2 invoices/second

**Parallelism:** Uses `asyncio.Semaphore` for configurable concurrency:
```bash
--concurrency=1   # Sequential (safe)
--concurrency=5   # 5 in parallel (fast)
--concurrency=10  # 10 in parallel (faster)
```

## Error Handling

Each agent has:
- Try/except wrapper
- Logging of errors
- Graceful fallback
- State preservation

Orchestrator:
- Catches agent exceptions
- Logs errors
- Continues processing
- Marks invoice as failed

## Testing

**File:** `tests/test_orchestrator.py`

Tests cover:
- Agent initialization
- Single invoice processing
- Validation logic
- End-to-end workflows

**Test Data:** 20 invoices in 5 formats (all in `data/invoices/`)

## Observability

**Metrics Collection:** `src/utils/metrics.py`
- Latency per agent
- Success rates
- Approval confidence
- Validation issues

**Export Formats:**
- JSON (monitoring tools)
- CSV (spreadsheet analysis)
- Console summary (real-time feedback)

## Future Enhancements

**Phase 3:** Production features
- HTML dashboard
- Vendor reputation scoring
- Fraud detection agent
- Advanced compliance checks

**Phase 4:** Scale to 50+ agents
- Hierarchical orchestration
- Blackboard pattern
- Dynamic agent discovery

---

**Key Files:**
- `main.py` - CLI entry point
- `src/agents/` - 4 agent implementations
- `src/orchestrator/langgraph_orchestrator.py` - Workflow engine
- `src/llm.py` - Claude API integration
- `src/database/setup.py` - Inventory database
