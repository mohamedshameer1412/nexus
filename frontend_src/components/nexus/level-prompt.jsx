"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { GraduationCap, Sprout, Trophy } from "lucide-react";
import { api } from "@/lib/api";
import { check, McqStarted } from "@/lib/schemas";
import { getDocs, getMcqJob, keys } from "@/lib/queries";
import { cn, friendlyError, plural } from "@/lib/utils";
import { JobProgress } from "@/components/nexus/answer";
import { Alert, Button, Card } from "@/components/ui/primitives";

const LEVELS = [
  { value: "new", label: "New learner", hint: "I am starting from scratch.", Icon: Sprout },
  { value: "intermediate", label: "Intermediate", hint: "I know the basics and want to go deeper.", Icon: GraduationCap },
  { value: "professional", label: "Professional", hint: "I already know this well or work with it.", Icon: Trophy },
];
const jobKey = (id) => `nexus.diagnostic.${id}`;

/**
 * Asked once per subject, after the first upload. "New learner" goes straight on. Anything else writes ten questions of different
 * difficulty from the materials and starts a diagnostic test, and the result says how confident the student is, topic by topic.
 */
export function LevelPrompt({ subject }) {
  const router = useRouter();
  const qc = useQueryClient();
  const id = String(subject.id); // the same string form the other pages use, so they share (and refresh) the same cached lists
  const docs = useQuery({ queryKey: keys.docs(id), queryFn: () => getDocs(id) });
  const [choice, setChoice] = useState("intermediate");
  const [jobId, setJobId] = useState(null);
  const [startedAt, setStartedAt] = useState(() => new Date().toISOString());
  const [problem, setProblem] = useState("");
  const [gone, setGone] = useState(false);

  useEffect(() => { // pick a diagnostic that was still being written when the student left this page
    try { const saved = Number(localStorage.getItem(jobKey(id))); if (saved) setJobId(saved); } catch {}
  }, [id]);

  const job = useQuery({
    queryKey: keys.mcqJob(id, jobId), queryFn: () => getMcqJob(id, jobId), enabled: jobId !== null,
    refetchInterval: (q) => (q.state.data?.status === "pending" ? 2500 : false),
  });
  const status = job.data?.status;

  const begin = useMutation({
    mutationFn: async () => {
      await api(`/subjects/${id}/level`, { method: "PUT", json: { level: choice } });
      if (choice === "new") return null;
      return check(McqStarted, await api(`/subjects/${id}/mcq/jobs`, { method: "POST", json: { purpose: "diagnostic" } }));
    },
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: keys.subject(id) });
      qc.invalidateQueries({ queryKey: keys.subjects });
      if (!r) return toast.success("Welcome. Ask a question, or write notes, whenever you like.");
      setStartedAt(new Date().toISOString());
      setJobId(r.id);
      try { localStorage.setItem(jobKey(id), String(r.id)); } catch {}
    },
    onError: (e) => setProblem(friendlyError(e)),
  });

  const test = useMutation({
    mutationFn: () => api(`/subjects/${id}/quiz/attempts`, { method: "POST", json: { kind: "diagnostic", job_id: jobId, mode: "practice" } }),
    onSuccess: (r) => {
      try { localStorage.removeItem(jobKey(id)); } catch {}
      qc.invalidateQueries({ queryKey: keys.quiz(id) });
      qc.invalidateQueries({ queryKey: keys.mcq(id) });
      router.push(`/subjects/${id}/quiz/${r.id}`);
    },
    onError: (e) => setProblem(friendlyError(e)),
  });

  if (gone || docs.isPending || !docs.data?.some((d) => d.chunks > 0)) return null;
  const waiting = jobId !== null;
  if (!waiting && subject.level) return null;

  const skip = () => { try { localStorage.removeItem(jobKey(id)); } catch {} setJobId(null); setGone(true); };
  return (
    <Card className="mb-6 border-brand/40 p-5 shadow-lift" role="region" aria-labelledby="level-h">
      {!waiting ? (
        <form onSubmit={(e) => { e.preventDefault(); setProblem(""); begin.mutate(); }}>
          <h2 id="level-h" className="font-display text-lg font-semibold">How well do you know {subject.name}?</h2>
          <p className="mt-1 text-sm text-muted">Nexus tailors its help to you. If you are not a new learner, it writes ten questions of different difficulty from your materials so you can take a short diagnostic test and see your confidence, topic by topic.</p>
          <fieldset className="mt-3">
            <legend className="sr-only">Your experience with this subject</legend>
            <div className="grid gap-2 sm:grid-cols-3">
              {LEVELS.map(({ value, label, hint, Icon }) => (
                <label key={value} className={cn("flex cursor-pointer items-start gap-3 rounded-lg border p-3.5 transition-colors has-[:focus-visible]:ring-4 has-[:focus-visible]:ring-brand/20", choice === value ? "border-brand bg-brand-wash" : "border-border bg-surface hover:bg-brand-wash/60")}>
                  <input type="radio" name="level" value={value} checked={choice === value} onChange={() => setChoice(value)} className="mt-1 h-4 w-4 accent-[#0369A8]" />
                  <span><span className="flex items-center gap-1.5 font-semibold"><Icon className="h-4 w-4 text-brand" aria-hidden="true" />{label}</span><span className="text-sm text-muted">{hint}</span></span>
                </label>
              ))}
            </div>
          </fieldset>
          {problem && <Alert tone="danger" className="mt-3">{problem}</Alert>}
          <div className="mt-3 flex flex-wrap gap-2">
            <Button type="submit" loading={begin.isPending}>{begin.isPending ? "Saving" : choice === "new" ? "Continue" : "Continue and take the diagnostic"}</Button>
            <Button type="button" variant="ghost" onClick={skip}>Ask me later</Button>
          </div>
        </form>
      ) : (
        <div aria-live="polite">
          <h2 id="level-h" className="font-display text-lg font-semibold">Your diagnostic test</h2>
          {!job.data || status === "pending" ? (
            <div className="mt-3"><JobProgress createdAt={startedAt} what="Writing ten questions of different difficulty from your materials…" /></div>
          ) : job.data.produced > 0 ? (
            <>
              <p className="mt-1 text-sm">{plural(job.data.produced, "question")} ready, from easy to hard. Answer as best you can: it is not graded, it only shows where you stand.</p>
              {job.data.produced < 10 && <p className="mt-1 text-xs text-muted">Some drafts did not pass the checks and were thrown away, so there are fewer than ten.</p>}
              {problem && <Alert tone="danger" className="mt-3">{problem}</Alert>}
              <div className="mt-3 flex flex-wrap gap-2">
                <Button onClick={() => { setProblem(""); test.mutate(); }} disabled={test.isPending}>{test.isPending ? "Starting…" : "Start the diagnostic test"}</Button>
                <Button variant="ghost" onClick={skip}>Not now</Button>
              </div>
            </>
          ) : (
            <>
              <Alert tone="warning" className="mt-3">{job.data.reason || "No question passed the checks, so nothing was made up."}</Alert>
              <div className="mt-3 flex gap-2"><Button variant="secondary" onClick={skip}>Close</Button></div>
            </>
          )}
        </div>
      )}
    </Card>
  );
}
