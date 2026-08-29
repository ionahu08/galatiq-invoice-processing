# Phase 3 Implementation Plan

## Overview
Phase 3 focuses on production readiness, performance, and scalability for the invoice processing system.

## Priority 1: Production Observability (Highest Impact for Shipping)

### 1.1 Metrics Collection
**What:** Track key performance indicators
- Latency per invoice (ingestion, validation, approval, payment)
- Success rates (by agent, by invoice type, by vendor)
- Error rates (by type: parsing, validation, API failures)
- LLM confidence distribution
- Cost tracking (API calls per invoice)

**Files to Create:**
- `src/utils/metrics.py` - Metrics collection class
- `src/orchestrator/metrics_recorder.py` - Record metrics during orchestration

**Output:**
- Real-time metrics logged to structured format
- CSV export for analysis
- JSON for integration with monitoring tools

### 1.2 Performance Dashboard
**What:** HTML dashboard showing live metrics
- Success rate trend (last 24h, 7d, 30d)
- Average latency per stage
- Error distribution by type
- LLM confidence histogram
- Cost trend

**Files to Create:**
- `dashboard.py` - Flask app serving dashboard
- `templates/dashboard.html` - Real-time metrics visualization

### 1.3 Observability Integration
**What:** Prepare for production monitoring
- OpenTelemetry instrumentation (optional: can be added later)
- Structured JSON logging enhancement
- Error tracking preparation (Sentry/DataDog ready)

## Priority 2: Batch Processing Optimization

### 2.1 Parallel Invoice Processing
**What:** Process multiple invoices concurrently
- Current: Sequential (1 invoice at a time)
- New: Parallel (N invoices in parallel, configurable)
- Queue management: Handle 100+ invoices efficiently

**Implementation:**
- Add `asyncio.gather()` for parallel processing
- Configurable concurrency limit
- Progress tracking

**Expected Impact:**
- 10x faster batch processing
- From ~10 invoices/sec to 100+ invoices/sec

### 2.2 Batch Configuration
- `BATCH_CONCURRENCY=10` - Number of parallel invoices
- `BATCH_TIMEOUT=30` - Timeout per invoice
- `BATCH_RETRY_POLICY=exponential` - Retry strategy

## Priority 3: PDF Extraction Hardening

### 3.1 Edge Cases
- Multi-page PDFs (currently works, but test more)
- Scanned/image-based PDFs (may need OCR later)
- Encrypted PDFs (handle gracefully)
- Very large PDFs (>100MB)

### 3.2 Improvements
- Better text extraction (detect tables, columns)
- Fallback to OCR for scanned documents (optional)
- Better vendor/invoice number detection

## Priority 4: New Agents (Nice-to-Have for Phase 3)

### 4.1 Vendor Reputation Agent
**Responsibility:**
- Score vendors based on history
- Flag suspicious vendors
- Track payment reliability

**Input:** Vendor name
**Output:** Reputation score (0-100), risk level (low/medium/high)

**Implementation:**
- In-memory vendor database (seed with test data)
- Score based on: approval rate, payment frequency, fraud history
- Auto-adjust confidence based on vendor reputation

### 4.2 Fraud Detection Agent
**Responsibility:**
- Identify suspicious invoices
- Flag high-risk patterns
- Alert for manual review

**Red Flags:**
- Vendor in fraud database
- Amount > 10x average for vendor
- Mismatched vendor/items
- Negative quantities (already checked in validation)

**Input:** ExtractedInvoice + ValidationResult
**Output:** FraudRisk with score (0-100) and red flags

## Recommended Execution Order

1. **Start with Metrics** (3-4 hours)
   - Best ROI for production readiness
   - Enables data-driven decisions
   - Foundation for dashboard

2. **Then Batch Optimization** (2-3 hours)
   - Performance improvement is visible
   - Helps test new system at scale
   - Relatively simple implementation

3. **Then PDF Hardening** (2-3 hours)
   - Test all 3 PDF invoices thoroughly
   - Fix any extraction issues
   - Add better error handling

4. **Finally New Agents** (4-6 hours each)
   - Vendor reputation scoring
   - Fraud detection
   - Both optional for Phase 3

## Success Criteria

### Metrics Phase
- ✅ Metrics collected for all invoices
- ✅ Latency breakdown available
- ✅ Success rate tracked
- ✅ Basic dashboard functional

### Batch Optimization Phase
- ✅ 10+ invoices process in parallel
- ✅ No loss of accuracy
- ✅ Proper error handling per invoice
- ✅ Progress tracking works

### PDF Hardening Phase
- ✅ All 3 PDF invoices parse correctly
- ✅ No regressions in other formats
- ✅ Better error messages for failures

## Estimated Timeline

| Task | Effort | Impact |
|------|--------|--------|
| Metrics Collection | 3h | High |
| Dashboard | 2h | Medium |
| Batch Optimization | 2h | High |
| PDF Hardening | 2h | Medium |
| Vendor Agent | 3h | Medium |
| Fraud Detection | 3h | Medium |
| **Total** | **15h** | - |

## Cost Impact

- Metrics: +$0 (local collection)
- Dashboard: +$0 (local Flask app)
- Batch Optimization: -10% (process 10x faster = use 1/10th the API calls)
- New Agents: +$0 (rule-based, no LLM calls)

**Net:** Same or better cost with 10x better performance

---

**Status:** Ready to implement
**Recommended Start:** Metrics Collection
