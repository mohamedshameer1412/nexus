# NEXUS — Software Testing, Validation and Evidence Report

**Project:** NEXUS — AI-Powered Adaptive Learning and Assessment Platform  
**Report Type:** Functional Testing, Negative Testing, Stress/Break Testing and Iteration Evidence  
**Prepared By:** NEXUS Development Team  
**Date:** 20 September 2026  
**Environment:** Development / demonstration environment; record the exact machine, browser, OS, Python/Node version and port-forwarding URL before final submission.

---

## 1. Executive Summary

This report documents the verification approach used for NEXUS. The objective is to demonstrate that the system behaves correctly during normal usage, rejects invalid input safely, remains understandable when external services fail, and improves after defects are identified.

The report separates:

1. Executed tests supported by logs or screenshots.
2. Planned tests that still require execution.
3. Defects discovered during testing.
4. Changes made to address the defects.
5. Remaining limitations and risks.

No test is marked as passed unless an execution record, output, screenshot, or other verifiable evidence is attached.

---

## 2. System Scope

The NEXUS workflow is intended to support the following learning cycle:

> Learn → Test → Verify → Diagnose → Improve → Reassess

### Main functional areas

- User registration and login
- Student profile configuration
- Syllabus upload and syllabus-structure extraction
- Subject and topic roadmap generation
- Study-note ingestion
- Quiz and short-question generation
- Source-grounded answer validation
- Assessment submission
- Mastery estimation
- Weak-topic and root-cause analysis
- Personalized improvement planning
- Human review or escalation when required
- Progress dashboard and learning history
- Failure handling for unavailable APIs, invalid files and malformed model output

### Proposed agent responsibilities

| Agent | Responsibility to verify |
|---|---|
| Tutor Agent | Explains concepts using definitions, examples and stepwise teaching |
| Content Agent | Generates learning content and assessment questions from permitted sources |
| Evaluator Agent | Checks answers and assessment quality |
| Analytics Agent | Analyses performance, time, attempts and answer patterns |
| Mentor Agent | Explains weaknesses and recommends learning actions |
| Planner Agent | Produces a bounded improvement plan based on verified findings |

The existence of an agent in the design does not by itself prove that the agent is implemented or independently testable. Each agent must be linked to a code location and execution evidence.

---

## 3. Test Environment Record

Complete this section using the actual execution environment.

| Item | Recorded value |
|---|---|
| Operating system | [Enter actual OS] |
| Device/browser | [Enter actual browser and version] |
| Runtime | [Python/Node version] |
| Application start command | [Enter command] |
| Local host | [Enter host and port] |
| Port-forwarding URL | [Enter active URL; do not expose secrets] |
| Model provider | [Enter provider] |
| Model name | [Enter configured model] |
| Repository branch | [Enter branch] |
| Commit under test | [Enter commit SHA] |
| Test execution date | [Enter date and time] |
| Network condition | [Connected / disconnected / throttled] |

### Security note

Do not include API keys, access tokens, passwords, private URLs or personal student data in screenshots or logs.

---

## 4. Evidence Standard

Every completed test should include:

- Test ID
- Date and time
- Environment
- Preconditions
- Exact steps
- Expected result
- Actual result
- Status
- Evidence reference
- Related issue or fix commit, where applicable

### Evidence naming convention

Use a consistent naming scheme:

```text
EVID-T01-login-valid.png
EVID-T02-invalid-file.txt
EVID-ST01-concurrent-requests.log
EVID-BUG01-before-fix.png
EVID-BUG01-after-fix.png
```

For terminal evidence:

```text
logs/
  test-run-2026-09-20.txt
  negative-tests-2026-09-20.txt
  stress-test-2026-09-20.txt
```

Screenshots should show enough context to establish what was tested, without exposing secrets or personal data.

---

## 5. Functional Positive Tests

Positive tests verify expected behavior using valid input and normal user actions.

| ID | Test case | Expected result | Status | Evidence |
|---|---|---|---|---|
| POS-01 | Register with valid details | Account/profile creation succeeds or a clear confirmation is shown | NOT EXECUTED | [Attach] |
| POS-02 | Login with valid credentials | User reaches the authenticated workspace | NOT EXECUTED | [Attach] |
| POS-03 | Upload valid syllabus PDF | File is accepted and syllabus structure is extracted or a clear processing state is shown | NOT EXECUTED | [Attach] |
| POS-04 | Edit extracted roadmap | User can correct unit/topic information before saving | NOT EXECUTED | [Attach] |
| POS-05 | Upload valid study notes | Notes are stored or indexed successfully | NOT EXECUTED | [Attach] |
| POS-06 | Generate topic assessment | Questions are generated within configured limits | NOT EXECUTED | [Attach] |
| POS-07 | Submit valid assessment | Answers are recorded and a result is produced | NOT EXECUTED | [Attach] |
| POS-08 | Review incorrect answers | System identifies incorrect responses and provides supported explanations | NOT EXECUTED | [Attach] |
| POS-09 | Generate improvement plan | Plan includes targeted topics and actionable next steps | NOT EXECUTED | [Attach] |
| POS-10 | Reassess a weak topic | New assessment result is recorded without overwriting historical data incorrectly | NOT EXECUTED | [Attach] |
| POS-11 | Refresh dashboard | Persisted progress remains available after refresh | NOT EXECUTED | [Attach] |
| POS-12 | Resume interrupted workflow | Previously saved state is restored or a clear recovery path is provided | NOT EXECUTED | [Attach] |

### Positive test execution record

For each passed test, capture:

```text
Test ID:
Executed by:
Date/time:
Commit SHA:
Input:
Expected:
Actual:
Result:
Evidence file:
```

---

## 6. Negative Tests

Negative tests verify that the system rejects invalid input, prevents unsafe state changes and communicates failures clearly.

| ID | Invalid condition | Expected safe behavior | Status | Evidence |
|---|---|---|---|---|
| NEG-01 | Empty registration fields | Validation message; no incomplete account created | NOT EXECUTED | [Attach] |
| NEG-02 | Invalid email format | Input rejected with a readable message | NOT EXECUTED | [Attach] |
| NEG-03 | Incorrect login password | Access denied; no sensitive information disclosed | NOT EXECUTED | [Attach] |
| NEG-04 | Unsupported file type | Upload rejected with accepted-format guidance | NOT EXECUTED | [Attach] |
| NEG-05 | Oversized upload | Request rejected or safely limited without application crash | NOT EXECUTED | [Attach] |
| NEG-06 | Empty syllabus file | Processing stops with a meaningful error | NOT EXECUTED | [Attach] |
| NEG-07 | Corrupted PDF | File parsing failure is handled without a traceback being shown to the user | NOT EXECUTED | [Attach] |
| NEG-08 | Empty study notes | System requests usable content or returns a controlled response | NOT EXECUTED | [Attach] |
| NEG-09 | Malformed model response | Validator rejects invalid structure and uses a safe fallback | NOT EXECUTED | [Attach] |
| NEG-10 | Missing API key | Application provides a configuration error without exposing secrets | NOT EXECUTED | [Attach] |
| NEG-11 | Provider timeout | User sees retry/recovery guidance; request does not hang indefinitely | NOT EXECUTED | [Attach] |
| NEG-12 | Provider rate limit | System handles the error and avoids uncontrolled retries | NOT EXECUTED | [Attach] |
| NEG-13 | Invalid assessment answer ID | Invalid submission is rejected; valid answers remain consistent | NOT EXECUTED | [Attach] |
| NEG-14 | Duplicate submission | System prevents unintended duplicate scoring or clearly marks the duplicate | NOT EXECUTED | [Attach] |
| NEG-15 | Unauthorized record access | User cannot access another student's private progress data | NOT EXECUTED | [Attach] |

### Negative test evidence requirement

For each negative test, record:

- The invalid input or failure condition.
- The user-visible message.
- The server/application log entry, if applicable.
- Whether the application remained available.
- Whether any partial or corrupted state was created.

---

## 7. Stress and Break Testing

Stress testing examines behavior under increased load. Break testing intentionally creates abnormal conditions to identify failure boundaries.

### 7.1 Stress test matrix

| ID | Scenario | Measurement | Expected behavior | Status |
|---|---|---|---|---|
| ST-01 | Repeated syllabus uploads | Number of requests, failures and response time | Requests are bounded and failures are controlled | NOT EXECUTED |
| ST-02 | Multiple users generating quizzes | Concurrent requests and completion rate | System remains responsive or returns controlled capacity errors | NOT EXECUTED |
| ST-03 | Large notes input | Input size, processing time and memory behavior | Input is limited or processed within defined bounds | NOT EXECUTED |
| ST-04 | Repeated assessment submissions | Duplicate rate and state consistency | No unintended duplicate scoring | NOT EXECUTED |
| ST-05 | Long-running model response | Timeout and recovery behavior | Request terminates within configured timeout | NOT EXECUTED |
| ST-06 | Repeated invalid requests | Error rate and server stability | Validation prevents resource exhaustion | NOT EXECUTED |
| ST-07 | Rapid dashboard refresh | Request count and UI stability | No duplicated state updates or visible crash | NOT EXECUTED |

### 7.2 Break test scenarios

| ID | Break condition | Expected recovery behavior | Status | Evidence |
|---|---|---|---|---|
| BRK-01 | Disconnect network during model request | Timeout/failure message and retry path | NOT EXECUTED | [Attach] |
| BRK-02 | Remove or invalidate API key | Clear configuration failure; no secret exposure | NOT EXECUTED | [Attach] |
| BRK-03 | Return malformed JSON from provider | Schema validation blocks unsafe output | NOT EXECUTED | [Attach] |
| BRK-04 | Force provider HTTP 500 | Controlled error and bounded retry behavior | NOT EXECUTED | [Attach] |
| BRK-05 | Force provider HTTP 429 | Backoff or user guidance; no retry storm | NOT EXECUTED | [Attach] |
| BRK-06 | Interrupt workflow after state persistence | Workflow can resume or clearly reports incomplete state | NOT EXECUTED | [Attach] |
| BRK-07 | Submit empty or extremely long prompt | Input limits prevent uncontrolled processing | NOT EXECUTED | [Attach] |
| BRK-08 | Close browser during processing | State is either safely recoverable or explicitly marked incomplete | NOT EXECUTED | [Attach] |

### 7.3 Stress-test log template

```text
Stress Test ID:
Scenario:
Start time:
End time:
Commit SHA:
Environment:
Input volume:
Concurrency:
Total requests:
Successful requests:
Failed requests:
Timeouts:
Average response time:
Maximum response time:
Observed errors:
Application remained available: YES / NO
Evidence files:
Conclusion:
```

Do not claim that a stress test passed based only on the application opening successfully. A stress test requires measured conditions and recorded results.

---

## 8. AI Output Validation

Because NEXUS uses model-generated content, output validation must be tested separately from UI behavior.

### Required checks

| ID | Validation rule | Expected result | Status |
|---|---|---|---|
| AI-01 | Generated question has required fields | Invalid structure is rejected | NOT EXECUTED |
| AI-02 | Question is grounded in supplied notes | Unsupported claims are flagged or excluded | NOT EXECUTED |
| AI-03 | Answer options are complete | Missing or duplicate options are rejected | NOT EXECUTED |
| AI-04 | Correct answer is within allowed options | Invalid answer key is rejected | NOT EXECUTED |
| AI-05 | Difficulty value is within configured range | Out-of-range value is normalized or rejected | NOT EXECUTED |
| AI-06 | Explanation does not contradict source material | Conflicts are flagged for review | NOT EXECUTED |
| AI-07 | Model returns unexpected text instead of JSON | Parser fails safely and does not persist malformed data | NOT EXECUTED |
| AI-08 | Provider returns empty output | Controlled fallback or retry is triggered | NOT EXECUTED |

### AI safety principle

The system should not treat a fluent model response as automatically correct. Structured validation, source grounding, bounded retries and human review should be used where the consequence of an incorrect output is significant.

---

## 9. Bug Tracking and Fix Verification

A defect should be documented from discovery through verification.

### Bug register

| Bug ID | Description | Impact | Root cause | Fix commit | Retest status |
|---|---|---|---|---|---|
| BUG-01 | [Observed defect] | [User/system impact] | [Confirmed cause] | [SHA] | NOT VERIFIED |
| BUG-02 | [Observed defect] | [User/system impact] | [Confirmed cause] | [SHA] | NOT VERIFIED |
| BUG-03 | [Observed defect] | [User/system impact] | [Confirmed cause] | [SHA] | NOT VERIFIED |

### Required bug-fix workflow

1. Reproduce the original failure.
2. Record the original behavior and evidence.
3. Identify the affected code location.
4. Implement the smallest appropriate fix.
5. Commit the change.
6. Run the same test again.
7. Run related regression tests.
8. Record the new result and remaining limitation.

### Bug-fix record template

```text
Bug ID:
Title:
Reported by:
Date discovered:
Affected feature:
Original behavior:
Expected behavior:
Impact:
Reproduction steps:
Original evidence:
Root cause:
Code change:
Fix commit SHA:
Retest command:
Retest result:
Regression tests:
Remaining limitation:
Before-fix evidence:
After-fix evidence:
```

A commit message alone is not proof that the defect was fixed. The original failure, code change and post-fix retest must be linked.

---

## 10. Test Results and Logs

### 10.1 Test summary

Complete this table only after executing the tests.

| Category | Planned | Executed | Passed | Failed | Blocked |
|---|---:|---:|---:|---:|---:|
| Positive tests | [ ] | [ ] | [ ] | [ ] | [ ] |
| Negative tests | [ ] | [ ] | [ ] | [ ] | [ ] |
| Stress tests | [ ] | [ ] | [ ] | [ ] | [ ] |
| Break tests | [ ] | [ ] | [ ] | [ ] | [ ] |
| AI validation | [ ] | [ ] | [ ] | [ ] | [ ] |
| Regression tests | [ ] | [ ] | [ ] | [ ] | [ ] |

### 10.2 Execution log

```text
Test run:
Date/time:
Branch:
Commit SHA:
Command:
Environment:
Result:
Output log:
Evidence:
```

### 10.3 Example command record

Replace the following with commands that actually exist in the repository:

```bash
python -m pytest
python -m pytest -q
```

Do not include a successful terminal result unless the command was executed and its output was saved.

---

## 11. User Feedback and Iteration Evidence

Use real participants and record their observations accurately. Do not invent names, feedback or successful outcomes.

### Participant register

Use non-sensitive identifiers only.

| Participant | Role/profile | Tasks completed | Consent/permission recorded |
|---|---|---|---|
| P-01 | Fellow student | [Tasks] | [Yes/No] |
| P-02 | Fellow student | [Tasks] | [Yes/No] |
| P-03 | Fellow student | [Tasks] | [Yes/No] |

### Feedback record

| Participant | Observed problem | Impact | Change made | Evidence |
|---|---|---|---|---|
| P-01 | [Actual observation] | [Impact] | [Change] | [Evidence] |
| P-02 | [Actual observation] | [Impact] | [Change] | [Evidence] |
| P-03 | [Actual observation] | [Impact] | [Change] | [Evidence] |

The feedback should contain both positive and negative observations. A credible iteration record explains what was confusing, slow, incorrect or incomplete, and how the implementation changed in response.

---

## 12. Traceability Matrix

| Requirement | Implementation reference | Test IDs | Evidence | Status |
|---|---|---|---|---|
| Valid user access | [File/function] | POS-01, POS-02, NEG-01–03 | [Attach] | NOT VERIFIED |
| Syllabus processing | [File/function] | POS-03, POS-04, NEG-04–07 | [Attach] | NOT VERIFIED |
| Assessment generation | [File/function] | POS-06, AI-01–08 | [Attach] | NOT VERIFIED |
| Assessment evaluation | [File/function] | POS-07, POS-08, NEG-13–14 | [Attach] | NOT VERIFIED |
| Personalized planning | [File/function] | POS-09, POS-10 | [Attach] | NOT VERIFIED |
| State persistence | [File/function] | POS-11, POS-12, BRK-06 | [Attach] | NOT VERIFIED |
| External API failure handling | [File/function] | NEG-10–12, BRK-01–05 | [Attach] | NOT VERIFIED |
| Privacy/access control | [File/function] | NEG-15 | [Attach] | NOT VERIFIED |

---

## 13. Known Limitations

Record only limitations that have been observed or confirmed.

Potential areas requiring explicit verification include:

- Dependence on external model-provider availability.
- Model-generated content may contain factual or instructional errors.
- Source grounding may not guarantee complete correctness.
- Latency and cost can increase with long inputs or repeated retries.
- Port-forwarding environments may introduce network, session or accessibility limitations.
- A prototype test suite may not represent production-scale concurrency.
- Mastery and prediction metrics require validation against an appropriate reference or labeled evaluation process.
- Browser-level anti-cheating controls may be limited by browser permissions and operating-system behavior.

These are risk areas to verify, not claims that each limitation has already occurred.

---

## 14. Release Readiness Checklist

- [ ] Application starts using documented instructions.
- [ ] Main user journey completed using valid inputs.
- [ ] Positive test evidence captured.
- [ ] Negative test evidence captured.
- [ ] API failure behavior tested.
- [ ] Malformed model output tested.
- [ ] Stress/break test executed with measurable inputs.
- [ ] At least one defect reproduced before fixing.
- [ ] Fix committed with a traceable commit SHA.
- [ ] Same defect retested after the fix.
- [ ] Regression tests executed.
- [ ] Participant feedback recorded accurately.
- [ ] Evidence files are linked and readable.
- [ ] Secrets and personal data removed from evidence.
- [ ] Remaining limitations documented.
- [ ] Final branch and commit identified.

---

## 15. Final Statement

This report provides the structure for verifying NEXUS through reproducible software-testing evidence. Final claims about reliability, successful test execution, defect resolution and user feedback must be based on the recorded outputs from the actual implementation.

The strongest submission is not the one containing the largest number of claimed passes. It is the one that clearly connects:

> Requirement → Implementation → Test → Evidence → Defect → Fix → Retest

**Final verification status:** Pending completion of execution records and evidence attachments.
