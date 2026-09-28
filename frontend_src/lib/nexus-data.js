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
  totalHours: 688,
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
  { month: "Jan", hours: 9 },
  { month: "Feb", hours: 15 },
  { month: "Mar", hours: 27 },
  { month: "Apr", hours: 22 },
  { month: "May", hours: 14 },
  { month: "Jun", hours: 28 },
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

// ─── Screens from the NEXUS mockups ───────────────────────────────────────────

export const SOURCES = { igot: "iGOT", tpac: "TPAC", internal: "Internal Learning" };

export const DASHBOARD_RECOMMENDED = [
  { id: "data-visualization", title: "Data Visualization for Governance", badge: "igot", weeks: 8, icon: "statistics" },
  { id: "advanced-statistics", title: "Advanced Statistical Methods", badge: "tpac", weeks: 6, icon: "skills" },
  { id: "leadership", title: "Leadership & Management", badge: "internal", weeks: 4, icon: "progress" },
];

export const PROGRESS_TREND = [
  { month: "Jan", value: 12 }, { month: "Feb", value: 22 }, { month: "Mar", value: 30 },
  { month: "Apr", value: 41 }, { month: "May", value: 52 }, { month: "Jun", value: 68 },
];

export const ROLE_BENCHMARK = { yours: 68, target: 85 };

export const LEARNING_PATH = [
  { id: "fundamentals", title: "Fundamentals of Official Statistics", badge: "igot", weeks: 4, status: "completed", icon: "learning" },
  { id: "data-visualization", title: "Data Visualization for Governance", badge: "igot", weeks: 8, status: "in-progress", icon: "statistics" },
  { id: "advanced-statistics", title: "Advanced Statistical Methods", badge: "tpac", weeks: 6, status: "not-started", icon: "digital" },
  { id: "leadership", title: "Leadership & Management in Public Service", badge: "igot", weeks: 4, status: "not-started", icon: "leadership" },
];

export const CURRENT_LEARNING = { courseId: "data-visualization", progress: 60, week: 5, weeks: 8, modulesLeft: 3 };

export const COURSE_DETAILS = {
  "data-visualization": {
    title: "Data Visualization for Governance",
    badge: "igot", level: "Intermediate", weeks: 8, pace: "Self-paced",
    about: "Learn how to use data visualization tools and techniques for effective policy making and decision support in government.",
    learnings: ["Principles of data visualization", "Tools and platforms", "Real-world government use cases", "Hands-on exercises"],
    modules: [
      { title: "Module 1: Introduction to Data Visualization", hours: 2, status: "completed" },
      { title: "Module 2: Charts and Graphs", hours: 2, status: "completed" },
      { title: "Module 3: Storytelling with Data", hours: 3, status: "in-progress" },
      { title: "Module 4: Dashboards for Governance", hours: 2, status: "not-started" },
    ],
    reviews: [
      { name: "R. Iyer", role: "Deputy Director, NSO", rating: 5, text: "Practical examples from NSS and PLFS releases made it easy to apply at work." },
      { name: "S. Das", role: "Statistical Officer", rating: 4, text: "The dashboard module helped me rebuild our monthly CPI brief." },
    ],
    certificate: "iGOT Karmayogi certificate of completion, credited to your competency profile when you pass the final assessment (60% or more).",
  },
  fundamentals: {
    title: "Fundamentals of Official Statistics", badge: "igot", level: "Beginner", weeks: 4, pace: "Self-paced",
    about: "The foundations of the official statistical system in India: survey design, national accounts, indices and dissemination standards.",
    learnings: ["Structure of the statistical system", "Survey and census methods", "Price and production indices", "Dissemination standards"],
    modules: [
      { title: "Module 1: The Official Statistical System", hours: 2, status: "completed" },
      { title: "Module 2: Surveys and Censuses", hours: 3, status: "completed" },
      { title: "Module 3: Indices", hours: 2, status: "completed" },
      { title: "Module 4: Dissemination", hours: 1, status: "completed" },
    ],
    reviews: [], certificate: "Certificate earned on 12 Aug 2024.",
  },
  "advanced-statistics": {
    title: "Advanced Statistical Methods", badge: "tpac", level: "Advanced", weeks: 6, pace: "Instructor-led",
    about: "Regression, sampling theory, small-area estimation and time-series methods used in national surveys.",
    learnings: ["Regression and model diagnostics", "Complex survey sampling", "Small-area estimation", "Time-series analysis"],
    modules: [
      { title: "Module 1: Regression", hours: 3, status: "not-started" },
      { title: "Module 2: Sampling Theory", hours: 3, status: "not-started" },
      { title: "Module 3: Small-Area Estimation", hours: 2, status: "not-started" },
      { title: "Module 4: Time Series", hours: 3, status: "not-started" },
    ],
    reviews: [], certificate: "NSSTA TPAC certificate on completion.",
  },
  leadership: {
    title: "Leadership & Management in Public Service", badge: "igot", level: "Intermediate", weeks: 4, pace: "Self-paced",
    about: "Team leadership, programme management and stakeholder communication for officers moving into supervisory roles.",
    learnings: ["Leading field teams", "Programme planning", "Stakeholder communication", "Performance reviews"],
    modules: [
      { title: "Module 1: Leading Teams", hours: 2, status: "not-started" },
      { title: "Module 2: Programme Management", hours: 2, status: "not-started" },
      { title: "Module 3: Communication", hours: 2, status: "not-started" },
      { title: "Module 4: Reviews and Feedback", hours: 1, status: "not-started" },
    ],
    reviews: [], certificate: "iGOT Karmayogi certificate on completion.",
  },
};

export const DIAGNOSTIC = {
  topic: "Data Visualization",
  questions: [
    { q: "Which chart best shows the change in CPI over 24 months?", options: ["Pie chart", "Line chart", "Scatter plot", "Histogram"] },
    { q: "What does a box plot summarise?", options: ["Only the mean", "The five-number summary", "Category shares", "Correlation"] },
    { q: "Which scale suits growth rates that span several orders of magnitude?", options: ["Linear", "Logarithmic", "Ordinal", "Nominal"] },
    { q: "A choropleth map is best for showing…", options: ["Values by region", "Flows between points", "A time trend", "Rank order"] },
    { q: "Which colour scheme suits a diverging indicator such as surplus or deficit?", options: ["Sequential", "Diverging", "Qualitative", "Monochrome"] },
    { q: "Truncating the y-axis of a bar chart mainly risks…", options: ["Slower rendering", "Exaggerating differences", "Hiding the legend", "Losing labels"] },
    { q: "Small multiples help to…", options: ["Compare many series on a shared scale", "Show one number", "Replace tables", "Add 3D depth"] },
    { q: "Which of the following is a key advantage of using data visualization in policy making?",
      options: ["Increases data storage capacity", "Helps in faster and clearer decision making", "Reduces the need for data collection", "Eliminates statistical errors"] },
    { q: "Which chart shows parts of a whole most accurately?", options: ["Stacked bar", "3D pie", "Radar", "Bubble"] },
    { q: "An annotation on a chart should…", options: ["Repeat the title", "Explain the key takeaway", "List data sources only", "Be avoided"] },
    { q: "A dashboard for district officers should first show…", options: ["Every indicator", "The few indicators they act on", "Raw microdata", "Methodology notes"] },
    { q: "Which is a sign of an overplotted scatter plot?", options: ["Too few points", "Points hiding each other", "Missing axis titles", "Log scale"] },
    { q: "Why add confidence intervals to survey estimates?", options: ["Decoration", "To show sampling uncertainty", "To hide outliers", "To increase precision"] },
    { q: "Which ordering helps readers compare bars fastest?", options: ["Alphabetical", "Sorted by value", "Random", "By data entry date"] },
    { q: "Accessible charts should avoid relying only on…", options: ["Text labels", "Colour to encode meaning", "Gridlines", "Legends"] },
  ],
  // The mockup opens on question 8 with eight answered (53%) and 12:30 left.
  start: 7,
  secondsLeft: 750,
  preAnswered: { 0: 1, 1: 1, 2: 1, 3: 0, 4: 1, 5: 1, 6: 0, 7: 1 },
};

export const PROFILE = {
  aspiration: "Strengthen my data analysis skills and contribute to evidence-based policy making.",
  menu: [
    { key: "profile", label: "My Profile", href: "/account", tone: "blue" },
    { key: "certificates", label: "Certificates", href: "/learn" },
    { key: "history", label: "Learning History", href: "/learn" },
    { key: "career", label: "Career Goals", href: "/career", mobileOnly: true },
    { key: "settings", label: "Settings", href: "/account" },
    { key: "help", label: "Help & Support", href: "/search" },
    { key: "logout", label: "Logout", tone: "red" },
  ],
};

export const TUTOR_REPLIES = {
  "Explain Again": "**In one line**\n- Correlation asks *do these two move together, and how strongly?*\n- Regression asks *if X changes by one unit, how much does Y change?*\n\n**Example**\n- Household size and monthly consumption: r = 0.6 says they rise together.\n- The regression line says each extra member adds about ₹2,100 to consumption.",
  "Generate MCQs": "**MCQ 1.** A correlation of r = −0.9 means…\n- A) No relationship\n- B) A strong negative linear relationship\n- C) X causes Y to fall\n- D) A weak relationship\n\n**MCQ 2.** In Y = a + bX, *b* is the…\n- A) Intercept\n- B) Correlation\n- C) Slope\n- D) Error term\n\n**Answers:** 1-B, 2-C",
  "Give Example": "**PLFS example**\n- *Correlation:* district literacy rate and female labour force participation, r = 0.48.\n- *Regression:* LFPR = 12.1 + 0.31 × literacy, so each extra point of literacy goes with 0.31 points higher LFPR.\n- Neither shows that literacy *causes* participation.",
  "Practice Question": "**Practice question**\nStudy time and exam scores have r = 0.85. Which is the most accurate interpretation?\n- A) Studying more *causes* higher scores\n- B) There is a strong positive linear relationship\n- C) Study time explains 85% of the variance\n- D) Both A and C\n\n**Answer: B.** Correlation is not causation, and R² = 0.72, not 0.85.",
};
