"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Clock, Download, GraduationCap, PlayCircle, RotateCcw, ScanFace, ShieldCheck, Sparkles, Stethoscope, Target } from "lucide-react";
import { api } from "@/lib/api";
import { getQuiz, getRevision, getSubject, keys } from "@/lib/queries";
import { dateTime, ratio, shortDate } from "@/lib/format";
import { cn, friendlyError, plural } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { CameraCheck } from "@/components/nexus/camera-check";
import { TrendArea } from "@/components/nexus/charts";
import { EmptyState, ErrorState, SectionTitle } from "@/components/nexus/common";
import { DataTable } from "@/components/nexus/data-table";
import {
  Alert, Badge, Button, Card, CardBody, CardHeader, Checkbox, Field, Segmented, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton, Slider, Switch,
} from "@/components/ui/primitives";

const KINDS = [
  { value: "standard", label: "Standard quiz", hint: "Choose topic, size and difficulty. A miss steps back to the topic it builds on.", Icon: Target },
  { value: "diagnostic", label: "Diagnostic", hint: "Two questions from every topic, for your first confidence scores.", Icon: Stethoscope },
  { value: "revision", label: "Revision", hint: "Only what you got wrong and topics that are still shaky.", Icon: RotateCcw },
];

function Choice({ active, onClick, Icon, label, hint, disabled }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-pressed={active}
      className={cn("flex w-full items-start gap-3 rounded-xl border p-3.5 text-left transition-colors disabled:opacity-50",
        active ? "border-brand bg-brand-wash shadow-[0_0_0_3px_rgb(1_148_226/.12)]" : "border-border bg-surface hover:border-brand/40 hover:bg-brand-wash/50")}>
      <span className={cn("grid h-9 w-9 shrink-0 place-items-center rounded-lg", active ? "bg-brand text-white" : "bg-brand-soft text-brand-deep")}><Icon className="h-[18px] w-[18px]" /></span>
      <span><span className="block font-semibold">{label}</span><span className="text-[13px] text-muted">{hint}</span></span>
    </button>
  );
}

export default function QuizHome() {
  const { id } = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const { data: subject } = useQuery({ queryKey: keys.subject(id), queryFn: () => getSubject(id) });
  useTitle("Quiz", subject?.name);
  const { data, error, isPending, refetch } = useQuery({ queryKey: keys.quiz(id), queryFn: () => getQuiz(id) });
  const revision = useQuery({ queryKey: keys.revision(id), queryFn: () => getRevision(id) });
  const [kind, setKind] = useState("standard");
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(10);
  const [difficulty, setDifficulty] = useState("mixed");
  const [mode, setMode] = useState("practice");
  const [limit, setLimit] = useState("none");
  const [agreed, setAgreed] = useState(false);
  const [adaptive, setAdaptive] = useState(true);
  const [problem, setProblem] = useState("");
  const start = useMutation({
    mutationFn: () => api(`/subjects/${id}/quiz/attempts`, { method: "POST", json: {
      topic_id: kind === "standard" && topic ? Number(topic) : null, mode, kind, adaptive: kind === "standard" && adaptive,
      count: kind === "standard" ? count : null, difficulty: kind === "standard" ? difficulty : "mixed" } }),
    onSuccess: (r) => {
      if (limit !== "none") { try { localStorage.setItem(`nexus.deadline.${r.id}`, String(Date.now() + Number(limit) * 60000)); } catch {} }
      qc.invalidateQueries({ queryKey: keys.quiz(id) }); router.push(`/subjects/${id}/quiz/${r.id}`);
    },
    onError: (e) => { setProblem(friendlyError(e)); if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {}); },
  });
  const columns = useMemo(() => [
    { accessorKey: "id", header: "Quiz", cell: ({ getValue }) => <span className="tabular font-semibold">#{getValue()}</span> },
    { accessorKey: "started_at", header: "Started", cell: ({ getValue }) => dateTime(getValue()) },
    { accessorKey: "kind", header: "Kind", cell: ({ getValue }) => <Badge tone="outline" className="capitalize">{getValue() ?? "standard"}</Badge> },
    { accessorKey: "mode", header: "Mode", cell: ({ getValue }) => <Badge tone={getValue() === "assessment" ? "brand" : "neutral"}>{getValue() === "assessment" ? "Assessment" : "Practice"}</Badge> },
    { id: "score", accessorFn: (a) => ratio(a.correct, a.answered), header: "Score", meta: { align: "right" }, cell: ({ row, getValue }) => (
      getValue() == null ? <span className="text-muted">–</span> : <span className={cn("tabular font-semibold", getValue() >= 70 ? "text-strong" : getValue() >= 45 ? "text-mid" : "text-weak")}>{getValue()}% <span className="font-normal text-muted">({row.original.correct}/{row.original.answered})</span></span>) },
    { id: "status", accessorFn: (a) => (a.active ? "In progress" : "Finished"), header: "Status", cell: ({ getValue }) => <Badge tone={getValue() === "In progress" ? "mid" : "strong"} dot>{getValue()}</Badge> },
    { id: "go", header: "", enableSorting: false, enableHiding: false, meta: { export: false }, cell: ({ row }) => {
      const a = row.original;
      return (
        <span className="flex justify-end gap-1">
          {!a.active && <Button asChild variant="ghost" size="icon-sm" aria-label={`Download quiz ${a.id} as PDF`}><a href={`/api/v1/subjects/${id}/quiz/attempts/${a.id}/report.pdf`} download onClick={(e) => e.stopPropagation()}><Download className="h-4 w-4" /></a></Button>}
          <Button asChild size="sm" variant="subtle"><Link href={a.active ? `/subjects/${id}/quiz/${a.id}` : `/subjects/${id}/quiz/${a.id}/result`} onClick={(e) => e.stopPropagation()}>{a.active ? "Continue" : "Review"}</Link></Button>
        </span>
      );
    } },
  ], [id]);

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-96" />;
  if (data.questions_in_bank === 0) {
    return <EmptyState icon={GraduationCap} title="No questions to be quizzed on yet" action={<Button asChild><Link href={`/subjects/${id}/practice`}>Generate practice questions</Link></Button>}>A quiz is made from the practice questions Nexus has written from your materials.</EmptyState>;
  }
  const wrongCount = revision.data?.wrong.length ?? 0;
  const noRevision = wrongCount === 0 && !(revision.data?.shaky_topics.length);
  const blocked = (mode === "assessment" && !agreed) || (kind === "revision" && noRevision);
  const finished = data.attempts.filter((a) => !a.active && a.answered > 0).slice().reverse();
  const trend = finished.map((a) => ({ label: shortDate(a.finished_at), score: ratio(a.correct, a.answered) }));

  async function beginAssessment() {
    try { await document.documentElement.requestFullscreen?.(); } catch {}
    try {
      const probe = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      probe.getTracks().forEach((t) => t.stop());
    } catch {
      if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
      setProblem("An assessment needs the camera. Allow the camera for this site, or choose Practice.");
      return;
    }
    start.mutate();
  }

  return (
    <div className="space-y-8">
      {data.active_attempt && (
        <Alert tone="info" icon={PlayCircle} title="You have a quiz in progress">
          <Link href={`/subjects/${id}/quiz/${data.active_attempt}`} className="font-semibold">Continue it</Link>, or start a new one below (the unfinished one is closed).
        </Alert>
      )}
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Start a quiz</h2>
          <form className="mt-4 space-y-6" onSubmit={(e) => { e.preventDefault(); setProblem(""); if (mode === "assessment") beginAssessment(); else start.mutate(); }}>
            <fieldset>
              <legend className="mb-2 text-[13px] font-semibold">Type</legend>
              <div className="grid gap-2 md:grid-cols-3">
                {KINDS.map((k) => <Choice key={k.value} active={kind === k.value} onClick={() => setKind(k.value)} Icon={k.Icon} label={k.label}
                  hint={k.value === "revision" ? `${wrongCount} wrong answers and shaky topics.` : k.hint} disabled={k.value === "revision" && noRevision} />)}
              </div>
            </fieldset>

            <AnimatePresence initial={false}>
              {kind === "standard" && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
                  <div className="grid gap-5 md:grid-cols-2">
                    <Field label="Topic" htmlFor="quiz-topic" hint={`${plural(data.questions_in_bank, "question")} in your bank.`}>
                      <Select value={topic || "all"} onValueChange={(v) => setTopic(v === "all" ? "" : v)}>
                        <SelectTrigger id="quiz-topic"><SelectValue /></SelectTrigger>
                        <SelectContent><SelectItem value="all">Whole subject</SelectItem>{data.topics.map((t) => <SelectItem key={t.id} value={String(t.id)}>{t.path.split(" › ").pop()}</SelectItem>)}</SelectContent>
                      </Select>
                    </Field>
                    <div>
                      <p className="mb-1.5 flex items-center justify-between text-[13px] font-semibold"><span>Number of questions</span><span className="tabular font-display text-lg text-brand-deep">{count}</span></p>
                      <Slider min={3} max={20} step={1} value={[count]} onValueChange={([v]) => setCount(v)} label="Number of questions" className="mt-3" />
                      <p className="mt-2 flex justify-between text-[11.5px] text-muted"><span>3</span><span>20</span></p>
                    </div>
                    <div>
                      <p className="mb-1.5 text-[13px] font-semibold">Difficulty</p>
                      <Segmented label="Difficulty" value={difficulty} onValueChange={setDifficulty} options={["mixed", "easy", "medium", "hard"].map((d) => ({ value: d, label: d[0].toUpperCase() + d.slice(1) }))} />
                    </div>
                    <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-border p-3">
                      <Switch checked={adaptive} onCheckedChange={setAdaptive} aria-label="Pick the questions for me" className="mt-0.5" />
                      <span className="text-[13px]"><b className="flex items-center gap-1 text-[14px]"><Sparkles className="h-3.5 w-3.5 text-brand" />Adaptive selection</b><span className="text-muted">Chooses the questions that tell Nexus the most about you now (IRT information), favouring topics below target and topics past papers ask.</span></span>
                    </label>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="grid gap-5 md:grid-cols-2">
              <fieldset>
                <legend className="mb-2 text-[13px] font-semibold">Mode</legend>
                <div className="grid gap-2">
                  <Choice active={mode === "practice"} onClick={() => setMode("practice")} Icon={GraduationCap} label="Practice" hint="Nothing is watched. Answer at your own pace." />
                  <Choice active={mode === "assessment"} onClick={() => setMode("assessment")} Icon={ShieldCheck} label="Scored assessment" hint="Full screen, camera check, copy and paste blocked. Ends if you leave." />
                </div>
              </fieldset>
              <Field label="Time limit" htmlFor="quiz-limit" hint="When time runs out the quiz ends; unanswered questions are not counted.">
                <Select value={limit} onValueChange={setLimit}>
                  <SelectTrigger id="quiz-limit"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="none">No limit</SelectItem>{[5, 10, 15, 30].map((m) => <SelectItem key={m} value={String(m)}>{m} minutes</SelectItem>)}</SelectContent>
                </Select>
              </Field>
            </div>

            {mode === "assessment" && (
              <Alert tone="info" icon={ScanFace} title="Before you start">
                <p className="mt-1">Nexus opens full screen and turns on your camera. The picture is checked inside your browser only; it is never uploaded or saved. The assessment <b>ends at once</b> if you leave the page or full screen, if no face is visible for 6 seconds, or if more than one face is visible for 3 seconds. Copying, pasting and right-click are blocked.</p>
                <CameraCheck />
                <label className="mt-3 flex cursor-pointer items-center gap-2 font-semibold">
                  <Checkbox checked={agreed} onCheckedChange={(v) => setAgreed(!!v)} />I understand and allow the camera
                </label>
              </Alert>
            )}
            {problem && <Alert tone="danger">{problem}</Alert>}
            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" size="lg" disabled={blocked} loading={start.isPending}><PlayCircle className="h-5 w-5" />
                Start {kind === "diagnostic" ? "diagnostic" : kind === "revision" ? "revision" : `${count}-question quiz`}{mode === "assessment" ? " as an assessment" : ""}
              </Button>
              {kind === "standard" && <span className="text-[13px] text-muted">{difficulty === "mixed" ? "Mixed difficulty" : `${difficulty[0].toUpperCase()}${difficulty.slice(1)} questions only`}{topic ? ", one topic" : ", whole subject"}</span>}
            </div>
          </form>
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader title="Your scores" description={finished.length ? `${finished.length} finished quizzes` : "No finished quizzes yet"} />
            <CardBody><TrendArea data={trend} series={[{ key: "score", name: "Score", color: "#0194E2" }]} yDomain={[0, 100]} yFmt={(v) => `${v}%`} tipFmt={(v) => `${v}%`} reference={{ y: 70, label: "70%" }} height={170} /></CardBody>
          </Card>
          <Card>
            <CardHeader title="Worth another look" description="Lowest scores with at least two answers." />
            <CardBody>
              {data.weak_topics.length === 0 ? <p className="text-sm text-muted">Nothing to flag yet.</p> : (
                <ul className="space-y-3">
                  {data.weak_topics.map((w) => (
                    <li key={w.topic_id}>
                      <div className="flex justify-between gap-2 text-sm"><span className="truncate font-medium">{w.name}</span><span className="tabular shrink-0 text-muted">{w.correct}/{w.answered}</span></div>
                      <div className="mt-1 h-1.5 rounded-full bg-brand-soft/70"><div className={cn("h-full rounded-full", w.mastery >= 0.7 ? "bg-strong" : w.mastery >= 0.4 ? "bg-mid" : "bg-weak")} style={{ width: `${Math.max(4, w.mastery * 100)}%` }} /></div>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </div>
      </div>

      {revision.data && revision.data.wrong.length > 0 && (
        <section aria-labelledby="rev-h">
          <SectionTitle id="rev-h">Revision list <span className="ml-1 text-sm font-normal text-muted">{revision.data.wrong.length} still wrong</span></SectionTitle>
          {revision.data.shaky_topics.length > 0 && <p className="mb-3 text-sm text-muted">Shaky topics: {revision.data.shaky_topics.map((t) => `${t.name} (${Math.round(t.confidence * 100)}%)`).join(", ")}.</p>}
          <div className="grid gap-3 md:grid-cols-2">
            {revision.data.wrong.slice(0, 6).map((w) => (
              <Card key={w.item_id} className="p-4 text-sm">
                <p className="break-anywhere font-semibold">{w.question}</p>
                {w.topic && <p className="mt-0.5 text-xs text-muted">{w.topic.split(" › ").pop()}</p>}
                {w.chosen_index !== null && <p className="break-anywhere mt-2 text-weak">You chose {String.fromCharCode(65 + w.chosen_index)}: {w.options[w.chosen_index]}</p>}
                <p className="break-anywhere mt-1 font-medium text-strong">Right answer {String.fromCharCode(65 + w.answer_index)}: {w.options[w.answer_index]}</p>
              </Card>
            ))}
          </div>
          {revision.data.wrong.length > 6 && <p className="mt-2 text-sm text-muted">and {revision.data.wrong.length - 6} more. Choose Revision above to be asked them again.</p>}
        </section>
      )}

      {data.attempts.length > 0 && (
        <section aria-labelledby="recent-h">
          <SectionTitle id="recent-h">Quiz history</SectionTitle>
          <DataTable columns={columns} data={data.attempts} filename="nexus-quizzes" title="Quiz history" searchPlaceholder="Search quizzes"
            facets={[{ id: "kind", label: "Kinds" }, { id: "mode", label: "Modes" }]}
            onRowClick={(a) => router.push(a.active ? `/subjects/${id}/quiz/${a.id}` : `/subjects/${id}/quiz/${a.id}/result`)} />
        </section>
      )}
    </div>
  );
}
