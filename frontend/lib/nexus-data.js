// NEXUS mock data for UI development — realistic government officer profile

export const OFFICER = {
  name: "A. Sharma",
  fullName: "Ashok Sharma",
  designation: "Statistical Officer (Grade-II)",
  department: "Ministry of Statistics and Programme Implementation",
  ministry: "MoSPI",
  employeeId: "MOS-2019-4421",
  email: "a.sharma@mospi.gov.in",
  phone: "+91 11 2337 XXXX",
  cadre: "Indian Statistical Service",
  location: "New Delhi",
  joiningDate: "2019-07-15",
  avatar: null,
};

export const COMPETENCY = {
  overallScore: 68,
  level: "Developing",
  lastAssessed: "2024-11-12",
  domains: [
    { id: "stats",    label: "Statistics & Data Analysis",    score: 75, target: 85, status: "on-track" },
    { id: "digital",  label: "Digital & Technology Skills",   score: 60, target: 80, status: "gap" },
    { id: "policy",   label: "Policy & Governance",           score: 55, target: 75, status: "gap" },
    { id: "comms",    label: "Communication & Reporting",     score: 70, target: 80, status: "on-track" },
    { id: "mgmt",     label: "Management & Leadership",       score: 50, target: 70, status: "gap" },
    { id: "domain",   label: "Domain Knowledge",              score: 80, target: 85, status: "on-track" },
  ],
};

export const LEARNING = {
  ongoingCount: 3,
  pendingAssessments: 2,
  completedCount: 12,
  totalHours: 86,
  thisMonthHours: 14,
  streak: 7, // days
  lastActivity: "2024-11-20",
};

export const COURSES = [
  {
    id: "c1",
    title: "Fundamentals of Official Statistics",
    provider: "iGOT Karmayogi",
    badge: "igot",
    progress: 72,
    duration: "8h",
    domain: "Statistics & Data Analysis",
    status: "ongoing",
    thumbnail: null,
    dueDate: "2024-12-10",
  },
  {
    id: "c2",
    title: "Data Visualization for Governance",
    provider: "iGOT Karmayogi",
    badge: "igot",
    progress: 45,
    duration: "6h",
    domain: "Digital & Technology Skills",
    status: "ongoing",
    thumbnail: null,
    dueDate: "2024-12-20",
  },
  {
    id: "c3",
    title: "Leadership for Senior Officers",
    provider: "NSSTA TPAC",
    badge: "tpac",
    progress: 20,
    duration: "12h",
    domain: "Management & Leadership",
    status: "ongoing",
    thumbnail: null,
    dueDate: "2025-01-15",
  },
  {
    id: "c4",
    title: "Advanced Statistical Methods",
    provider: "iGOT Karmayogi",
    badge: "igot",
    progress: 100,
    duration: "10h",
    domain: "Statistics & Data Analysis",
    status: "completed",
    thumbnail: null,
  },
  {
    id: "c5",
    title: "Policy Writing & Communication",
    provider: "NSSTA TPAC",
    badge: "tpac",
    progress: 100,
    duration: "5h",
    domain: "Communication & Reporting",
    status: "completed",
    thumbnail: null,
  },
];

export const RECOMMENDATIONS = [
  {
    id: "r1",
    title: "Introduction to R for Statistical Analysis",
    provider: "iGOT Karmayogi",
    badge: "igot",
    duration: "6h",
    domain: "Digital & Technology Skills",
    gap: "Identified gap in digital competency",
    score: 60,
    confidence: 0.92,
    type: "course",
  },
  {
    id: "r2",
    title: "Public Policy Formulation & Governance",
    provider: "NSSTA TPAC",
    badge: "tpac",
    duration: "8h",
    domain: "Policy & Governance",
    gap: "Required for Grade-II promotion",
    score: 55,
    confidence: 0.87,
    type: "program",
  },
  {
    id: "r3",
    title: "Mid-Term Competency Assessment",
    provider: "NEXUS",
    badge: "assessment",
    duration: "45 min",
    domain: "All Domains",
    gap: "Scheduled assessment overdue",
    score: null,
    confidence: 1.0,
    type: "assessment",
  },
];

export const MONTHLY_ACTIVITY = [
  { month: "Jun", hours: 8,  courses: 2 },
  { month: "Jul", hours: 12, courses: 3 },
  { month: "Aug", hours: 6,  courses: 1 },
  { month: "Sep", hours: 18, courses: 4 },
  { month: "Oct", hours: 22, courses: 5 },
  { month: "Nov", hours: 14, courses: 3 },
];

export const ASSESSMENTS = [
  {
    id: "a1",
    title: "Statistics Fundamentals — Module 2",
    domain: "Statistics & Data Analysis",
    dueDate: "2024-11-25",
    duration: "30 min",
    questions: 20,
    status: "pending",
    type: "mcq",
  },
  {
    id: "a2",
    title: "Digital Tools Proficiency Check",
    domain: "Digital & Technology Skills",
    dueDate: "2024-11-28",
    duration: "45 min",
    questions: 30,
    status: "pending",
    type: "mcq",
  },
  {
    id: "a3",
    title: "Policy Analysis Baseline",
    domain: "Policy & Governance",
    dueDate: "2024-10-30",
    duration: "60 min",
    questions: 40,
    status: "completed",
    score: 62,
    type: "mcq",
  },
];

export const CAREER_PATH = {
  current: "Statistical Officer (Grade-II)",
  next: "Senior Statistical Officer (Grade-I)",
  targetDate: "2026-07",
  requiredCompetency: 78,
  currentCompetency: 68,
  gap: 10,
  milestones: [
    { label: "Complete iGOT Foundation Track", done: true },
    { label: "Score ≥70% in Statistics Assessment", done: true },
    { label: "Complete Leadership Module", done: false },
    { label: "Policy Governance Certification", done: false },
    { label: "Mid-level Competency Assessment ≥78%", done: false },
  ],
};

export const AI_TUTOR_HISTORY = [
  {
    role: "user",
    content: "Explain the difference between correlation and regression in simple terms.",
    ts: "2024-11-20T10:14:00Z",
  },
  {
    role: "assistant",
    content: `Great question! Here's a clear breakdown:

**Correlation**
- Measures the *strength* and *direction* of a linear relationship between two variables
- Ranges from **−1** (perfect negative) to **+1** (perfect positive); 0 = no linear relationship
- Does **not** imply causation — it's purely descriptive
- Example: "Height and weight are correlated (r = 0.72)"

**Regression**
- Models the *functional relationship* between variables to predict one from the other
- Provides an equation: **Y = a + bX** where *b* is the slope
- Can be used for prediction and quantifying the effect of X on Y
- Example: "For every 1 cm increase in height, weight increases by 0.4 kg on average"

**Key rule of thumb:** Correlation tells you *if* two things move together. Regression tells you *how much* and lets you *predict*.`,
    ts: "2024-11-20T10:14:18Z",
    xai: {
      reason: "Based on your current Statistics & Data Analysis learning path and your Module 2 performance (62%).",
      evidence: [
        "Fundamentals of Official Statistics — Chapter 4",
        "Regression Analysis — NSSTAT Module",
        "Your recent Module 1 Quiz (65% accuracy on quantitative questions)",
      ],
      competency: "Statistics & Data Analysis",
      confidence: 0.94,
      sources: ["NSSTA Learning Material", "iGOT Statistics Foundation"],
    },
  },
  {
    role: "user",
    content: "Give me a practice question on this.",
    ts: "2024-11-20T10:16:00Z",
  },
];
