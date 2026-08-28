# Galatiq Invoice Processing - Project Context

**Project:** Automated invoice processing system for Acme Corp (PE-backed manufacturing)
**Role:** Forward Deployed Engineer (Galatiq)
**Goal:** Build a production-grade multi-agent system that automates invoice processing end-to-end
**Timeline:** 4-8 hours to ship MVP

---

## Business Context

**Problem:** Acme Corp loses $2M/year on manual invoice processing
- 30% error rate
- 5-day processing delays
- Frustrated stakeholders
- Manual extraction, validation, approval, payment processing

**Solution:** Multi-agent AI system automating all 4 stages
- Reduces errors from 30% to <5%
- Cuts delays from 5 days to 30 seconds
- Eliminates manual work
- Provides audit trail

**Success Metrics:**
- Functional end-to-end workflow
- Clean, production-grade code
- Agentic sophistication (LLM reasoning, self-correction, structured output)
- Shipping mindset (MVP first, ruthlessly cut scope)

---

## Technical Architecture

### Workflow (4 stages)

```
Invoice (PDF, TXT, JSON, CSV)
    |
    v
[1] INGESTION AGENT
    Extract: Vendor, Amount, Items (qty), Due Date
    Output: ExtractedInvoice (Pydantic model)
    |
    v
[2] VALIDATION AGENT
    Check: Item exists in inventory, qty in stock
    Output: ValidationResult (list of issues)
    |
    v
[3] APPROVAL AGENT
    Rules: Auto-approve if valid, auto-reject if invalid
    LLM: Generator-Critic loop for confidence
    Output: ApprovalResult (decision + reasoning)
    |
    v
[4] PAYMENT AGENT
    If approved: Call mock payment API
    If rejected: Log rejection reason
    Output: PaymentResult (status + transaction ID)
    |
    v
ProcessingResult (success/rejected/requires_review/failed)
```

### Multi-Agent Design Patterns (from study)

**Phase 2 Axes Applied:**
- Control Topology: **Centralized** (one Orchestrator)
- Planning: **Code-driven** (fixed 4-stage workflow)
- Communication: **Star topology** (all agents report to orchestrator)
- Agent Properties: **Ephemeral** (spawn once per invoice, discard after)

**Phase 3 Patterns Applied:**
- **Orchestrator-Workers** (decomposition) - one orchestrator, four specialists
- **Generator-Critic** (confidence) - approval loop iterates for confidence

**Phase 4 Communication:**
- **Structured interfaces** - All agents use Pydantic models
- **Schema enforcement** - Type safety at runtime
- **Information loss** - Citations and grounding at each layer

**Phase 6 Production:**
- **Failure modes** - Graceful degradation, partial results
- **Bounds & control** - Token budgets, timeouts, retries
- **Observability** - Structured logging at each stage
- **Evaluation** - Ablation tests (single-agent baseline)

---

## Project Structure

```
/tmp/galatiq-invoice-processing/

├── src/
│   ├── agents/
│   │   ├── base.py              # BaseAgent (abstract class)
│   │   ├── ingestion.py         # Extract from files [TO IMPLEMENT]
│   │   ├── validation.py        # Check inventory [COMPLETE]
│   │   ├── approval.py          # Approval logic [BASIC + LLM SCAFFOLD]
│   │   └── payment.py           # Payment processing [SCAFFOLD]
│   │
│   ├── orchestrator/
│   │   └── orchestrator.py      # InvoiceOrchestrator [COMPLETE]
│   │
│   ├── database/
│   │   └── setup.py             # SQLite operations [COMPLETE]
│   │
│   ├── config.py                # Pydantic Settings
│   ├── models.py                # 7 data models (ExtractedInvoice, etc.)
│   └── utils/logging.py         # Structured logging
│
├── data/invoices/               # 5 test invoices
│   ├── INV-1001.txt            # Normal order (PASS)
│   ├── INV-1002.txt            # Qty mismatch (FAIL)
│   ├── INV-1003.txt            # Out of stock (FAIL)
│   ├── INV-1004.txt            # High amount $15K (REVIEW)
│   └── INV-1005.txt            # Normal order (PASS)
│
├── tests/
│   └── test_orchestrator.py    # Unit test scaffold
│
├── main.py                     # CLI entry point
├── requirements.txt            # Dependencies
├── README.md                   # Documentation
├── STRUCTURE.md                # Architecture guide
├── CLAUDE.md                   # This file
└── .gitignore
```

---

## Key Components

### 1. Models (src/models.py)
All communication uses strongly-typed Pydantic models:
- `LineItem` - Single line item (name, qty, price)
- `ExtractedInvoice` - Ingestion output
- `ValidationResult` - Validation issues
- `ValidationIssue` - Single issue (type, message, severity)
- `ApprovalResult` - Approval decision + reasoning
- `PaymentResult` - Payment status + transaction ID
- `ProcessingResult` - Full pipeline output

### 2. Database (src/database/setup.py)
SQLite inventory database:
- `create_inventory_database()` - Initialize DB
- `query_inventory()` - Look up item
- `check_stock()` - Verify qty in stock

Seed data:
- WidgetA: 15 in stock
- WidgetB: 10 in stock
- GadgetX: 5 in stock
- FakeItem: 0 in stock (for testing)

### 3. Base Agent (src/agents/base.py)
Abstract class that all agents inherit from:
```python
class BaseAgent(ABC):
    async def execute(self, input_data):
        """Main logic - override in subclass"""
        pass
```

Built-in:
- Logging wrapper (`log_execution()`)
- Error handling in `run()` method
- Async/await support

### 4. Orchestrator (src/orchestrator/orchestrator.py)
Coordinates the 4-stage workflow:
```python
async def process_invoice(invoice_path: str) -> ProcessingResult:
    # Stage 1: Ingestion
    # Stage 2: Validation
    # Stage 3: Approval
    # Stage 4: Payment
```

Also supports batch processing:
```python
async def process_batch(invoice_paths: list[str]) -> list[ProcessingResult]
```

### 5. CLI (main.py)
Command-line interface:
```bash
# Single invoice
python main.py --invoice_path=data/invoices/invoice1.txt

# Batch
python main.py --batch --dir=data/invoices

# Debug logging
python main.py --debug
```

---

## Implementation Roadmap

### Phase 1: Skeleton (COMPLETE ✅)
- [x] Project structure
- [x] Pydantic models (7 types)
- [x] Database layer
- [x] Base agent class
- [x] Orchestrator
- [x] CLI entry point
- [x] Logging setup

### Phase 2: Core Implementation (4-5 hours) [IN PROGRESS]

#### 2.1 Ingestion Agent (1-1.5 hours)
- [ ] Parse TXT format (vendor, amount, items, due date)
- [ ] Parse PDF with pdfplumber
- [ ] [Optional] LLM for unstructured text parsing (Claude/Grok)
- [ ] Handle typos, missing data, variations
- [ ] Return ExtractedInvoice with confidence score
- [ ] Test on all 5 sample invoices

#### 2.2 Approval Agent - Generator-Critic (1.5-2 hours)
- [ ] Implement `_generator_critic_loop()` with 3 phases:
  - Phase 1: LLM generates recommendation + reasoning
  - Phase 2: LLM critiques the recommendation
  - Phase 3: LLM revises based on critique
- [ ] Return higher confidence after iteration (0.8+ target)
- [ ] Keep basic rules for clear cases (auto-approve/reject)
- [ ] Integrate confidence scoring

#### 2.3 Payment Agent (30 min)
- [ ] Implement mock payment API
- [ ] Simulate 95% success, 5% failure
- [ ] Return transaction ID on success
- [ ] Test all approval paths

#### 2.4 End-to-End Testing (1 hour)
- [ ] Single invoice: `python main.py --invoice_path=...`
- [ ] Batch: `python main.py --batch --dir=data/invoices`
- [ ] Verify 5 test cases produce correct outcomes:
  - INV-1001: SUCCESS
  - INV-1002: FAILED (qty mismatch)
  - INV-1003: FAILED (out of stock)
  - INV-1004: REQUIRES_REVIEW (high amount)
  - INV-1005: SUCCESS

### Phase 3: Polish & Observability (1-1.5 hours)
- [ ] Error handling (missing files, timeouts, retries)
- [ ] Detailed logging at each stage
- [ ] Token usage tracking
- [ ] Type hints complete
- [ ] Docstrings on all public methods
- [ ] Unit tests for agents
- [ ] Integration tests for orchestrator

### Phase 4: Ship (30 min - 1 hour)
- [ ] Create GitHub repo
- [ ] Push all files
- [ ] Test clone + install
- [ ] Verify all commands work
- [ ] Send repo link to Galatiq

---

## Tech Stack

- **Language:** Python 3.11+
- **Async:** asyncio (built-in)
- **Type Safety:** Pydantic v2
- **Database:** SQLite3 (built-in)
- **LLM:** Claude (Anthropic API) or Grok (xAI)
- **Document Processing:** pdfplumber
- **CLI:** argparse (built-in)
- **Testing:** pytest + pytest-asyncio
- **Logging:** Python logging (built-in)

---

## Configuration

`.env` file (copy from `.env.example`):
```env
# LLM
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# System
DATABASE_PATH=inventory.db
INVOICES_DIR=data/invoices
LOGS_DIR=logs

# Agent
APPROVAL_THRESHOLD=10000.0

# Features
DEBUG_MODE=false
```

---

## Testing Strategy

### Sample Invoices

| Invoice | Vendor | Amount | Items | Expected | Why |
|---------|--------|--------|-------|----------|-----|
| INV-1001 | TechSupplies | $5000 | WidgetA(5), GadgetX(2) | PASS | Normal order, in stock |
| INV-1002 | OverstockSupply | $3500 | GadgetX(20) | FAIL | Qty mismatch (only 5 in stock) |
| INV-1003 | SuspiciousVendor | $2000 | FakeItem(10) | FAIL | Out of stock (0 available) |
| INV-1004 | PremiumPartners | $15000 | WidgetA(10), WidgetB(5) | REVIEW | Amount exceeds $10K threshold |
| INV-1005 | ReliableSupplier | $2750 | WidgetB(3), GadgetX(1) | PASS | Normal order, in stock |

### Test Execution
```bash
# Single
python main.py --invoice_path=data/invoices/INV-1001.txt

# All 5
python main.py --batch --dir=data/invoices

# Debug
python main.py --batch --debug
```

---

## Expected Output Example

```
================================================================================
INVOICE PROCESSING RESULT
================================================================================
Invoice Number: INV-1001
Vendor: TechSupplies Inc
Amount: $5000.00
Overall Status: SUCCESS

EXTRACTION:
  Vendor: TechSupplies Inc
  Items: 2
  Confidence: 95.0%

VALIDATION:
  Valid: True
  Issues: 0

APPROVAL:
  Approved: True
  Confidence: 85.0%
  Manual Review: False
  Reasoning: Invoice approved: TechSupplies Inc, $5000.00, all validations passed

PAYMENT:
  Status: success
  Message: Paid $5000.00 to TechSupplies Inc
  Transaction ID: TXN-TEC-12345

================================================================================
```

---

## Key Design Decisions

### 1. Async/Await
Enables concurrent agent execution. Agents can run in parallel (with care for data races).

### 2. Pydantic Models
- Type safety at runtime
- Schema enforcement
- Clear contracts between agents
- Easy JSON serialization for logging

### 3. Star Topology
- Orchestrator is the single point of coordination
- Simple to understand, scales to 50+ agents
- No circular dependencies, no deadlock risk

### 4. Centralized Control
- One orchestrator owns stage transitions
- Clear ownership of decisions
- Easy to debug (follow the orchestrator's logic)

### 5. Code-Driven Planning
- Fixed 4-stage workflow
- Predictable, testable
- Upgrade to model-driven planning later if needed

### 6. Structured Logging
- Console: INFO and above (realtime)
- File: DEBUG and above (audit trail)
- Each agent logs its decisions

---

## What Impresses Galatiq

✅ **Multi-agent architecture** - Orchestrator-Workers pattern applied correctly
✅ **Agentic sophistication** - LLM reasoning, generator-critic loop, structured output
✅ **Production code** - Clean, testable, well-structured
✅ **Shipping mindset** - Ruthless scope (MVP first), working prototype
✅ **Business translation** - Explains cost savings, error reduction, time savings
✅ **Error handling** - Graceful degradation, observability, retries
✅ **Going above and beyond** - Generator-Critic loop, batch processing, comprehensive logging

---

## Implementation Notes

### LLM Integration Strategy

**For Approval Agent (generator-critic):**
```python
async def _generator_critic_loop(self, extracted, validation):
    # Phase 1: Generate
    analysis = await llm.generate_recommendation(extracted, validation)
    
    # Phase 2: Critique
    critique = await llm.critique_recommendation(analysis)
    
    # Phase 3: Revise
    if critique.has_flaws:
        revised = await llm.revise_based_on_critique(analysis, critique)
        return revised
    return analysis
```

### For Ingestion Agent:

**Option A: Simple parsing (faster, MVP)**
- Regex for TXT/CSV
- pdfplumber for PDF
- JSON parsing for JSON

**Option B: LLM parsing (better accuracy)**
- Use Claude with structured output
- Handle edge cases better
- Higher confidence scores

**Recommendation:** Start with Option A, upgrade to Option B if time permits.

### Error Handling Pattern

All agents should follow this:
```python
async def execute(self, input_data):
    try:
        # Do work
        return result
    except TimeoutError:
        # Retryable - let orchestrator handle
        raise
    except ValueError as e:
        # Non-retryable - return error result
        return ErrorResult(message=str(e))
```

---

## Git Workflow

1. Create GitHub repo: `galatiq-invoice-processing`
2. Initialize git in `/tmp/galatiq-invoice-processing`:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: MVP scaffold"
   git remote add origin https://github.com/yourusername/galatiq-invoice-processing.git
   git push -u origin main
   ```

3. Send link to Galatiq (only the GitHub URL)

---

## Success Criteria (for Galatiq)

- [ ] Code runs without errors
- [ ] All 4 stages implemented
- [ ] 5 test invoices produce correct output
- [ ] Clean, readable code (no tech debt)
- [ ] Comprehensive logging + observability
- [ ] README explains architecture + business impact
- [ ] Generator-Critic loop implemented (shows sophistication)
- [ ] Error handling + retries
- [ ] Batch processing works

---

## Timeline

- **Phase 2.1 (Ingestion):** 1-1.5 hours
- **Phase 2.2 (Approval/LLM):** 1.5-2 hours
- **Phase 2.3 (Payment):** 30 minutes
- **Phase 2.4 (End-to-end):** 1 hour
- **Phase 3 (Polish):** 1-1.5 hours
- **Phase 4 (Ship):** 30 minutes - 1 hour

**Total: ~7 hours** (can compress to 4-5 with focused effort)

---

## Next Immediate Steps

1. **Move repo to permanent location:**
   ```bash
   cp -r /tmp/galatiq-invoice-processing ~/galatiq-invoice-processing
   cd ~/galatiq-invoice-processing
   ```

2. **Start Phase 2.1: Implement Ingestion Agent**
   - Parser for TXT format
   - Extend to PDF/JSON if time

3. **Run tests frequently:**
   - After each component
   - On all 5 sample invoices
   - Verify correct outcomes

4. **Ship by:** Tonight or tomorrow morning (depending on scope)

---

**Status:** MVP scaffold complete. Ready for implementation. Estimated total effort: 7 hours (4-5 with focus).

**Started:** 2026-08-28
**Target Ship Date:** 2026-08-28 or 2026-08-29
