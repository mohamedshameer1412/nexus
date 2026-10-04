// Runtime checks of every API response (JavaScript has no compiler to catch a renamed field). A mismatch throws one clear error.
import { z } from "zod";

export const User = z.object({ id: z.number(), username: z.string(), cloud_consent: z.boolean(), email: z.string().nullable().optional(), role: z.enum(["officer", "faculty"]).optional() });
export const Session = z.object({ authenticated: z.boolean(), user: User.nullable(), csrf: z.string() });

export const Counts = z.object({ documents: z.number(), topics: z.number(), questions: z.number(), practice_questions: z.number() });
export const Level = z.enum(["new", "intermediate", "professional"]);
export const Subject = z.object({ id: z.number(), name: z.string(), description: z.string(), created_at: z.string(), counts: Counts, level: Level.nullable().optional() });
export const SubjectList = z.object({ subjects: z.array(Subject) });

export const Doc = z.object({
  id: z.number(), kind: z.string(), title: z.string(), source: z.string(), pages: z.number().nullable(), status: z.string(),
  warnings: z.array(z.string()), bytes: z.number(), chunks: z.number(), created_at: z.string(), role: z.enum(["notes", "syllabus", "pyq"]).optional(), ocr_pages: z.number().optional(),
});
export const DocList = z.object({ documents: z.array(Doc) });
export const Upload = z.object({ document: Doc, duplicate: z.boolean() });
export const Passage = z.object({
  id: z.number(), ordinal: z.number(), page_start: z.number().nullable(), page_end: z.number().nullable(), heading_path: z.string(),
  text: z.string(), quarantined: z.boolean(), flag_reason: z.string(),
});
export const DocDetail = z.object({ document: Doc, passages: z.array(Passage) });
export const TopicList = z.object({ topics: z.array(z.object({ id: z.number(), name: z.string(), path: z.string(), passages: z.number() })) });
export const SearchResult = z.object({
  query: z.string(), terms: z.array(z.string()),
  results: z.array(z.object({
    passage_id: z.number(), document_id: z.number(), document: z.string(), heading_path: z.string(), page_start: z.number().nullable(),
    page_end: z.number().nullable(), text: z.string(), matched: z.array(z.string()), relevant: z.boolean(),
  })),
});
export const Account = z.object({
  user: User, key_configured: z.boolean(), allowed_models: z.array(z.string()),
  academic: z.object({ department: z.string(), semester: z.number().nullable() }).optional(),
  email: z.object({ login: z.string().nullable().optional(), address: z.string().nullable(), verified: z.boolean(), pending: z.string().nullable(), weekly: z.boolean(), last_digest_at: z.string().nullable(), can_send: z.boolean() }).optional(),
});

export const Citation = z.object({
  passage_id: z.number().nullable(), document_id: z.number().nullable().optional(), quote: z.string(), document: z.string(), heading_path: z.string(),
  page_start: z.number().nullable(), page_end: z.number().nullable(),
});
export const Claim = z.object({ text: z.string(), citations: z.array(Citation) });
export const Source = z.object({
  passage_id: z.number().nullable(), document_id: z.number().nullable().optional(), document: z.string(), heading_path: z.string(), page_start: z.number().nullable(),
  page_end: z.number().nullable(), text: z.string(), matched: z.array(z.string()),
});
export const QuestionItem = z.object({
  id: z.number(), question: z.string(), status: z.string(), tier: z.string().nullable().optional(), feedback: z.string().nullable().optional(), saved: z.boolean().optional(),
  created_at: z.string(),
});
export const QuestionList = z.object({ questions: z.array(QuestionItem) });
export const QuestionDetail = QuestionItem.extend({
  model: z.string().nullable().optional(), reason: z.string().optional(), kind: z.string().optional(), dropped: z.number().optional(),
  explanation: z.string().optional(), claims: z.array(Claim).optional(), sources: z.array(Source).optional(),
  verification: z.array(z.string()).optional(), steps: z.array(z.object({ by: z.string(), kind: z.string().optional(), text: z.string() })).optional(), loop: z.object({ sent_back: z.number(), rejected: z.number() }).optional(),
});

// ---- practice (multiple-choice) ----
export const Mcq = z.object({ id: z.number(), topic_id: z.number().nullable(), topic_path: z.string(), question: z.string(), options: z.array(z.string()), created_at: z.string() });
export const McqList = z.object({ questions: z.array(Mcq) });
export const McqStarted = z.object({ id: z.number(), status: z.string() });
export const ActiveJobs = z.object({ jobs: z.array(z.object({ id: z.number(), subject_id: z.number(), subject: z.string(), count: z.number(), created_at: z.string().nullable() })) });
export const McqJob = z.object({
  id: z.number(), status: z.string(), purpose: z.string().optional(), scope: z.string(), requested: z.number(), produced: z.number(), rejected: z.number(), reason: z.string().nullable().optional(),
  model: z.string().nullable().optional(), tier: z.string().nullable().optional(), questions: z.array(Mcq), steps: z.array(z.object({ by: z.string(), kind: z.string().optional(), text: z.string() })), loop: z.object({ sent_back: z.number(), rejected: z.number() }).optional(),
});
export const McqAnswer = z.object({
  id: z.number(), answer_index: z.number(), answer: z.string(), explanation: z.string(), quote: z.string(), document: z.string().nullable().optional(),
  heading_path: z.string().nullable().optional(), page_start: z.number().nullable().optional(), page_end: z.number().nullable().optional(), independently_checked: z.boolean(),
});

// ---- quiz and progress ----
export const Weak = z.object({ topic_id: z.number(), name: z.string(), path: z.string(), answered: z.number(), correct: z.number(), mastery: z.number(), state: z.string() });
export const Attempt = z.object({ id: z.number(), mode: z.enum(["practice", "assessment"]), kind: z.string().optional(), verified_retest: z.boolean().optional(), active: z.boolean(), started_at: z.string().nullable(), finished_at: z.string().nullable(), correct: z.number(), incorrect: z.number(), answered: z.number() });
export const QuizHome = z.object({
  questions_in_bank: z.number(), topics: z.array(z.object({ id: z.number(), path: z.string() })), active_attempt: z.number().nullable(), active_mode: z.string().nullable().optional(),
  attempts: z.array(Attempt), weak_topics: z.array(Weak),
});
export const QuizState = z.discriminatedUnion("state", [
  z.object({
    state: z.literal("mcq"), attempt: Attempt, total_questions: z.number(), position: z.number(),
    item: z.object({
      answer_row_id: z.number(), item_id: z.number(), question: z.string(), options: z.array(z.string()), topic_path: z.string().nullable().optional(),
      topic: z.string().nullable().optional(), backtrack: z.object({ from: z.string().nullable(), topic: z.string().nullable() }).nullable().optional(),
    }),
  }),
  z.object({ state: z.literal("complete"), attempt: Attempt }),
]);
const DiagTopic = z.object({ topic_id: z.number(), name: z.string(), confidence: z.number(), label: z.string(), answered: z.number(), correct: z.number() });
export const Diagnosis = z.object({
  claimed: z.string().nullable(), suggested: z.string().nullable(), note: z.string().nullable(), theta: z.number(), confidence: z.number(),
  by_difficulty: z.object({ easy: z.object({ correct: z.number(), answered: z.number() }), medium: z.object({ correct: z.number(), answered: z.number() }), hard: z.object({ correct: z.number(), answered: z.number() }) }),
  weakest: z.array(DiagTopic), strongest: z.array(DiagTopic), answered: z.number(), correct: z.number(),
});
export const NoteItem = z.object({ id: z.number(), title: z.string(), source: z.string(), doubt_id: z.number().nullable(), topic_id: z.number().nullable().optional(), created_at: z.string(), updated_at: z.string(), snippet: z.string() });
export const NoteList = z.object({ notes: z.array(NoteItem) });
export const Note = NoteItem.extend({ body: z.string() });
export const QuizResult = z.object({
  attempt: Attempt, skipped: z.number(), ended_reason: z.string().nullable(), diagnosis: Diagnosis.nullable().optional(),
  answers: z.array(z.object({
    answer_id: z.number().optional(), question: z.string(), topic: z.string(), options: z.array(z.string()), chosen_index: z.number(), answer_index: z.number(), correct: z.boolean(),
    explanation: z.string(), backtrack: z.boolean().optional(), self_confidence: z.number().nullable().optional(),
    contest: z.object({ id: z.number(), status: z.enum(["open", "upheld", "rejected"]), resolution: z.string() }).nullable().optional(),
  })),
  gap: z.object({
    mastered_at: z.number(), closed: z.boolean(), confidently_wrong: z.number(), rated: z.number(),
    topics: z.array(z.object({
      topic_id: z.number(), topic: z.string(), before: z.number().nullable().optional(), after: z.number(), closed: z.boolean(),
      next_gap: z.object({ topic_id: z.number(), topic: z.string(), chain: z.array(z.string()) }).optional(),
    })),
  }).optional(),
  focus_events: z.object({ tab_switch: z.number(), full_screen_exit: z.number(), copy_attempt: z.number(), paste_attempt: z.number() }),
  weak_topics: z.array(Weak),
});
const Topic = z.object({
  topic_id: z.number(), name: z.string(), path: z.string(), answered: z.number(), correct: z.number(), mastery: z.number(), state: z.string(),
  confidence: z.number().nullable(), theta: z.number().nullable(), se: z.number().nullable(), expected_accuracy: z.number().nullable(), label: z.string(),
  avg_seconds: z.number().nullable(), recent_accuracy: z.number().nullable(),
});
const Overall = z.object({ theta: z.number(), se: z.number(), confidence: z.number(), expected_accuracy: z.number(), answered: z.number(), correct: z.number() });
const Trend = z.object({ attempt_id: z.number(), at: z.number().nullable(), theta: z.number(), confidence: z.number(), accuracy: z.number(), answered: z.number() });
export const Progress = z.object({
  topics: z.array(Topic), weak_topics: z.array(Weak), overall: Overall.nullable(), ability_trend: z.array(Trend),
  prerequisites: z.array(z.object({ topic_id: z.number(), topic: z.string(), prereq_id: z.number(), prereq: z.string() })),
});
export const Revision = z.object({
  wrong: z.array(z.object({ item_id: z.number(), question: z.string(), options: z.array(z.string()), chosen_index: z.number().nullable(), answer_index: z.number(), explanation: z.string(), topic: z.string() })),
  shaky_topics: z.array(z.object({ topic_id: z.number(), name: z.string(), confidence: z.number(), answered: z.number(), correct: z.number() })),
});
export const Report = z.object({
  generated_at: z.string(), subject: z.string(), overall: Overall.nullable(), method: z.string(), recommendations: z.array(z.string()), wrong_questions: z.number(),
  topics: z.array(z.object({ topic_id: z.number(), name: z.string(), answered: z.number(), correct: z.number(), confidence: z.number().nullable(), theta: z.number().nullable(), label: z.string(), avg_seconds: z.number().nullable() })),
  ability_trend: z.array(Trend),
  attempts: z.array(Attempt.extend({ ended_reason: z.string().nullable() })),
  backtracking: z.array(z.object({ topic: z.string(), asked: z.number(), correct: z.number() })),
});

// ---- dashboard ----
export const Saved = z.object({ saved: z.array(z.object({ id: z.number(), subject_id: z.number(), subject: z.string(), question: z.string(), status: z.string(), created_at: z.string() })) });
export const Flashcards = z.object({
  cards: z.array(z.object({ item_id: z.number(), question: z.string(), options: z.array(z.string()), topic: z.string(), is_new: z.boolean() })),
  total: z.number(), due: z.number(), new: z.number(), next_due: z.string().nullable(),
});
export const SearchAll = z.object({
  query: z.string(), terms: z.array(z.string()),
  results: z.array(z.object({
    subject_id: z.number(), subject: z.string(), passage_id: z.number(), document_id: z.number(), document: z.string(), heading_path: z.string(),
    page_start: z.number().nullable(), page_end: z.number().nullable(), text: z.string(), matched: z.array(z.string()),
  })),
});
export const Dashboard = z.object({
  totals: z.object({ subjects: z.number(), materials: z.number(), questions: z.number(), practice_questions: z.number(), quizzes: z.number(), answered: z.number(), correct: z.number() }),
  subjects: z.array(z.object({ id: z.number(), name: z.string(), materials: z.number(), questions: z.number(), practice_questions: z.number(), quizzes: z.number(), answered: z.number(), correct: z.number() })),
  activity: z.array(z.object({ date: z.string(), asked: z.number(), answered: z.number() })),
  quiz_trend: z.array(z.object({ attempt_id: z.number(), subject_id: z.number(), subject: z.string(), finished_at: z.string().nullable(), correct: z.number(), answered: z.number() })),
  topic_states: z.object({ mastered: z.number(), learning: z.number(), weak: z.number(), unknown: z.number() }),
  question_outcomes: z.object({ answered: z.number(), extractive: z.number(), abstained: z.number(), failed: z.number(), pending: z.number() }),
  feedback: z.object({ helpful: z.number(), wrong: z.number() }),
  weak_topics: z.array(z.object({ topic_id: z.number(), subject_id: z.number(), subject: z.string(), name: z.string(), answered: z.number(), correct: z.number(), mastery: z.number(), state: z.string() })),
  streak: z.object({ days: z.number(), today: z.number(), goal: z.number() }).optional(),
});

/** @template T @param {import('zod').ZodType<T>} schema @param {unknown} data @returns {T} */
export function check(schema, data) {
  const r = schema.safeParse(data);
  if (!r.success) throw new Error(`The server sent an unexpected response (${r.error.issues[0]?.path.join(".") || "root"}).`);
  return r.data;
}

// ---- roadmap and skill gaps
const Src = z.object({ answered: z.number(), correct: z.number() });
const Sources = z.object({ diagnostic: Src, quiz: Src, revision: Src, assessment: Src, flashcards: Src });
const Gap = z.object({
  topic_id: z.number(), name: z.string(), path: z.string(), ordinal: z.number(), status: z.enum(["critical", "moderate", "minor", "on_track", "unassessed"]), gap: z.number().nullable(),
  confidence: z.number().nullable(), target: z.number(), answered: z.number(), correct: z.number(), sources: Sources, trend: z.string().nullable(),
  blocked_by: z.array(z.object({ topic_id: z.number(), name: z.string(), confidence: z.number().nullable() })), reasons: z.array(z.string()), avg_seconds: z.number().nullable(),
});
const Step = z.object({ type: z.string(), title: z.string(), minutes: z.number(), href: z.string(), topic_id: z.number(), status: z.string() });
const Week = z.object({ week: z.number(), minutes: z.number(), steps: z.array(Step), focus: z.array(z.string()), goal: z.string(), milestone: z.string(), idea: z.string().nullable() });
export const Roadmap = z.object({
  subject: z.string(), level: Level.nullable(), target: z.number(), readiness: z.number().nullable(),
  counts: z.object({ critical: z.number(), moderate: z.number(), unassessed: z.number(), minor: z.number(), on_track: z.number() }),
  source_totals: Sources, source_labels: z.record(z.string(), z.string()), gaps: z.array(Gap),
  roadmap: z.object({ weeks: z.array(Week), summary: z.object({
    total_minutes: z.number(), weeks: z.number(), shown_weeks: z.number(), hours_per_week: z.number(), lagging: z.number(), unassessed: z.number(),
    target_date: z.string().nullable(), weeks_available: z.number().nullable(), on_track: z.boolean().nullable(), hours_needed: z.number().nullable() }) }),
  profile: z.object({ goal: z.string(), hours_per_week: z.number(), target_date: z.string().nullable(), exam_date: z.string().nullable().optional(), target_date_source: z.string().nullable().optional() }),
  coach: z.object({ status: z.string(), text: z.string(), from_model: z.boolean(), model: z.string().nullable(), stale: z.boolean(), at: z.string().nullable() }),
});

// ---- outlook (risk, debt, what-if), self-check, career goals
const RiskTopic = z.object({ topic_id: z.number(), name: z.string(), score: z.number().nullable(), level: z.string(), reasons: z.array(z.string()), confidence: z.number().nullable() });
const DebtTopic = z.object({ topic_id: z.number(), name: z.string(), own_minutes: z.number(), blocks: z.array(z.string()), interest_minutes: z.number(), confidence: z.number().nullable(), status: z.string(), repay_first: z.boolean() });
export const Outlook = z.object({
  subject: z.string(), target: z.number(), readiness: z.number().nullable(),
  risk: z.object({ summary: z.object({ score: z.number().nullable(), level: z.string(), assessed: z.number(), unassessed: z.number(), high: z.number(), medium: z.number(), late: z.boolean(), hours_needed: z.number().nullable(), hours_per_week: z.number().nullable() }), topics: z.array(RiskTopic), method: z.string() }),
  debt: z.object({ total_minutes: z.number(), total_hours: z.number(), topics: z.array(DebtTopic), edges: z.array(z.object({ from: z.number(), to: z.number() })), method: z.string() }),
  profile: z.object({ hours_per_week: z.number(), target_date: z.string().nullable(), weeks: z.number() }),
  topics: z.array(z.object({ topic_id: z.number(), name: z.string(), status: z.string() })),
});
const SimTopic = z.object({ topic_id: z.number(), name: z.string(), status: z.string(), now: z.number().nullable(), after: z.number().nullable(), minutes_needed: z.number(), minutes_given: z.number(), covered: z.boolean(), focus: z.boolean() });
const Sim = z.object({ hours_per_week: z.number(), weeks: z.number(), budget_minutes: z.number(), unused_minutes: z.number(), readiness_now: z.number().nullable(), readiness_after: z.number().nullable(), lagging: z.number(), covered: z.number(), target: z.number(), weeks_to_finish: z.number(), topics: z.array(SimTopic) });
export const WhatIf = z.object({ baseline: Sim, scenario: Sim, why: z.array(z.string()), assumption: z.string() });
export const SelfCheck = z.object({
  topics: z.array(z.object({ topic_id: z.number(), name: z.string(), rating: z.number().nullable(), perceived: z.number().nullable(), confidence: z.number().nullable(), answered: z.number(), delta: z.number().nullable(), verdict: z.string() })),
  counts: z.record(z.string(), z.number()), message: z.string(), labels: z.record(z.string(), z.string()),
});
export const CareerList = z.object({ goals: z.array(z.object({ id: z.number(), title: z.string(), status: z.string(), skills: z.number(), created_at: z.string().nullable() })) });
const CareerSkill = z.object({ skill: z.string(), importance: z.string(), quote: z.string(), status: z.string(), confidence: z.number().nullable(), answered: z.number(), correct: z.number(), topic: z.string().nullable(), subject: z.string().nullable(), subject_id: z.number().nullable(), topic_id: z.number().nullable(), also: z.array(z.string()) });
export const Career = z.object({
  id: z.number(), title: z.string(), status: z.string(), model: z.string().nullable(), from_model: z.boolean(), created_at: z.string().nullable(),
  skills: z.array(CareerSkill),
  score: z.object({ readiness: z.number().nullable(), verified: z.number(), total: z.number(), counts: z.record(z.string(), z.number()) }),
  next_steps: z.array(z.object({ skill: z.string(), importance: z.string(), status: z.string(), type: z.string(), title: z.string(), href: z.string(), suggestion: z.string() })),
  history: z.array(z.object({ at: z.string().nullable(), readiness: z.number().nullable(), verified: z.number(), total: z.number() })),
});

// ---- learner twin, worked examples
const Loop = z.object({ state: z.string(), last_kind: z.string().nullable(), last_outcome: z.string().nullable(), change: z.number().nullable(), tries: z.number() });
const TwinTopic = z.object({
  topic_id: z.number(), name: z.string(), unit: z.string(), subtopic: z.string(), status: z.string(), confidence: z.number().nullable(), theta: z.number().nullable(), se: z.number().nullable(),
  answered: z.number(), trend: z.string().nullable(), gap: z.number().nullable(), blocked_by: z.array(z.string()), exam_count: z.number(), exam_weight: z.number(),
  drift: z.string(), drift_note: z.string().nullable(), days_since: z.number().nullable(), feeling: z.string(), rating: z.number().nullable(),
  difficulty: z.string(), difficulty_why: z.string(), loop: Loop,
});
const Action = z.object({ topic_id: z.number(), topic: z.string(), kind: z.string(), title: z.string(), why: z.array(z.string()), minutes: z.number(), href: z.string(), difficulty: z.string(), difficulty_why: z.string(), fits_this_week: z.boolean(), priority: z.number() });
export const Twin = z.object({
  subject: z.string(), target: z.number(), readiness: z.number().nullable(),
  overall: z.object({ theta: z.number(), se: z.number(), confidence: z.number(), answered: z.number(), correct: z.number() }).nullable(),
  profile: z.object({ level: z.string().nullable().optional(), goal: z.string(), hours_per_week: z.number(), target_date: z.string().nullable(), exam_date: z.string().nullable().optional(), department: z.string(), semester: z.number().nullable() }),
  strengths: z.array(z.string()), weaknesses: z.array(z.string()),
  units: z.array(z.object({ unit: z.string(), topics: z.number(), assessed: z.number(), confidence: z.number().nullable(), answered: z.number(), status: z.string() })),
  topics: z.array(TwinTopic),
  patterns: z.object({ patterns: z.array(z.object({ kind: z.string(), topic_id: z.number().nullable(), topic: z.string(), count: z.number(), title: z.string(), detail: z.string() })), recurring: z.number(), answers: z.number(), method: z.string() }),
  next: z.array(Action),
  memory: z.array(z.object({ kind: z.string(), label: z.string(), tried: z.number(), improved: z.number(), mean_change: z.number() })),
  history: z.array(z.object({ id: z.number(), topic_id: z.number(), topic: z.string(), kind: z.string(), status: z.string(), outcome: z.string().nullable(), conf_before: z.number().nullable(), conf_after: z.number().nullable(), created_at: z.string().nullable(), verified_at: z.string().nullable() })),
  has_past_papers: z.boolean(),
});
export const Example = z.object({
  id: z.number(), topic_id: z.number(), topic: z.string(), status: z.string(), model: z.string().nullable(), level: z.string().nullable(), created_at: z.string().nullable(),
  example: z.object({ problem: z.string(), steps: z.array(z.object({ text: z.string(), quote: z.string() })), answer: z.string().optional(), check: z.string().optional(), from_model: z.boolean() }).nullable(),
});
export const ExampleList = z.object({ examples: z.array(Example) });
