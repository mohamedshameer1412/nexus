import { Bot, ClipboardList, Compass, FileText, Fingerprint, GraduationCap, Layers, LineChart, MessageCircleQuestion, NotebookPen, Route } from "lucide-react";

/** The sections of a subject workspace, in the order a student meets them: used by the tabs, the sidebar and the command palette. */
export const SECTIONS = [
  { slug: "materials", label: "Materials", Icon: FileText, hint: "Upload and read your files" },
  { slug: "ask", label: "Ask", Icon: MessageCircleQuestion, hint: "Answers cited from your files" },
  { slug: "practice", label: "Practice", Icon: Layers, hint: "Questions and flashcards" },
  { slug: "quiz", label: "Quiz", Icon: GraduationCap, hint: "Scored and proctored tests" },
  { slug: "progress", label: "Progress", Icon: LineChart, hint: "Mastery per topic" },
  { slug: "roadmap", label: "Roadmap", Icon: Route, hint: "Your weekly plan" },
  { slug: "outlook", label: "Outlook", Icon: Compass, hint: "Risk, debt and what-if" },
  { slug: "notes", label: "Notes", Icon: NotebookPen, hint: "Your notes and saved answers" },
  { slug: "twin", label: "Learner twin", Icon: Fingerprint, hint: "Your learning profile" },
  { slug: "agents", label: "Agents", Icon: Bot, hint: "What the six agents decided" },
  { slug: "report", label: "Report", Icon: ClipboardList, hint: "Printable summary" },
];
