# NEXUS — User Feedback, Stress Testing & Iteration Report

**Project:** NEXUS  
**Team:** DEAD LOCK  
**Repository:** https://github.com/mohamedshameer1412/DeadLock  
**Implementation status:** Prototype  
**Testing date:** 20 September 2026  
**Testing environment:** Windows with Google Chrome  
**Execution environments:** Localhost and port forwarding  
**Participants:** Bala, Anbu, Nirmala   

---

## 1. Purpose

This report documents user feedback, functional retesting, negative-input testing, stress testing, and implementation changes carried out for the NEXUS prototype.

The objective was to identify usability limitations and functional issues through peer testing, apply targeted improvements, and repeat the relevant tests to check whether the observed issues were addressed.

This report records only the testing information currently available. Where supporting evidence, exact logs, screenshots, or commit references are unavailable, the limitation is explicitly stated.

---

## 2. Testing Participants

| Participant | Testing scope |
|---|---|
| Bala | Login, registration, syllabus workflow, and AI Tutor question answering |
| Anbu | Invalid-input testing |
| Nirmala | Complete application flow and general UI/UX feedback |

The participants were fellow students who interacted with the prototype and reported observations based on their testing experience.

---

## 3. Features Covered

The following application features were included in the reported testing scope:

1. Login and registration
2. Syllabus or document upload
3. AI Tutor / question answering
4. Quiz generation
5. Student performance analytics
6. Personalized learning plan
7. Root-cause analysis of mistakes
8. Secure assessment / proctoring
9. Dashboard and progress tracking

---

## 4. User Feedback Summary

### 4.1 Feedback from Bala

**Feedback classification:** Functional issue

Bala reported two issues:

1. A subject could be created, but there was no option to delete the subject.
2. Question generation stopped when the user navigated to another page.

These observations were converted into two tracked issues.

#### ISS-001 — Missing subject deletion option

- **Original behavior:** A created subject did not provide a visible deletion option.
- **Impact:** Users could not remove a subject after creating it.
- **Change reported:** Subject deletion functionality was implemented.
- **Retest result:** Passed.


#### ISS-002 — Question generation state lost during navigation

- **Original behavior:** Question generation stopped when the user navigated to another page.
- **Impact:** The question-generation process did not preserve its state across navigation.
- **Change reported:** Frontend state handling was updated.
- **Retest result:** Passed.
- **Retest observation:** After generation started, the state remained the same after navigation.
- 

---

### 4.2 Feedback from Anbu

**Feedback classification:** Negative-input testing

Anbu tested unsupported and empty-file input conditions.

- **Inputs tested:** Unsupported file and empty file
- **System response:** An error message was reported for the invalid input.
- **Problem reported:** No
- **Fix required:** No

The available information indicates that the system returned an error response for the tested invalid input. The exact error message and complete supporting log were not supplied.

---

### 4.3 Feedback from Nirmala

**Feedback classification:** UX improvement suggestion

Nirmala suggested improving the smoothness and interactivity of the user interface and user experience.

- **Feedback type:** Mixed
- **Issue identified:** Yes, as a general improvement area
- **Specific failure:** No specific reproducible navigation or functional failure was reported.
- **Suggested improvement:** Improve animation smoothness, interaction feedback, and overall UI/UX flow.

This feedback is recorded as a usability enhancement suggestion rather than a confirmed functional defect because a specific failure condition was not provided.

---

## 5. Fix Verification and Retesting

### 5.1 Subject deletion retest

- **Test action:** Create a subject, open the subject details, and attempt to delete the subject.
- **Observed result:** Subject deletion was reported as successful.
- **Status:** Pass
- **Available evidence:** Locally stored screenshot of the retest.

### 5.2 Question generation navigation retest

- **Test action:** Start question generation and navigate to another page.
- **Observed result:** The generation state was reported to remain unchanged after navigation.
- **Status:** Pass
- **Available evidence:** LOCALLY STORED VIDEO OF RETEST.

---

## 6. Regression Testing

The team reported that the major application features were tested again after the changes.

| Feature | Reported result |
|---|---|
| Login / Registration | Pass |
| Syllabus / Document upload | Pass |
| AI Tutor / Question answering | Pass |
| Quiz generation | Pass |
| Student performance analytics | Pass |
| Personalized learning plan | Pass |
| Root-cause analysis of mistakes | Pass |
| Secure assessment / Proctoring | Pass |
| Dashboard / Progress tracking | Pass |

**Regression testing note:** The results above are reported test outcomes. Detailed test-case steps, timestamps, screenshots, and logs for every feature were not supplied and therefore are not represented as independently verified evidence in this document.

---



## 8. Testing Environment

| Item | Recorded value |
|---|---|
| Operating system | Windows, LINUX  |
| Browser | Google Chrome, EDGE , FIREFOX |
| Execution environments | Localhost and port forwarding |
| Testing date | 20 September 2026 |
| Evidence storage | Local computer |

The exact Chrome version, application startup command, port number, API configuration, and device specifications were not recorded in the available responses.

---



## 10. Issues and Iterations Register

| Issue ID | Issue | Reported change | Retest status | 
|---|---|---|---|---|
| ISS-001 | No subject deletion option | Subject deletion implemented | Pass |
| ISS-002 | Question generation stopped after navigation | Frontend state handling updated | Pass | 
| UX-001 | General request for smoother and more interactive UI/UX | MADE CHANGES  |  PASS |

---



## 13. Conclusion

Peer testing identified two functional issues and one general UI/UX improvement suggestion. The reported fixes for subject deletion and question-generation state handling were retested and marked as passed. Invalid-input testing and empty-file testing were also reported as passed.

The current report provides a structured record of the observed feedback, reported changes, retest outcomes, and evidence limitations. Claims requiring independent verification should be supported by the corresponding screenshots, logs, recordings, or commit references before the report is treated as fully evidence-backed.
---