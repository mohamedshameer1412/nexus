"use client";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowRight, Camera, CornerDownLeft, Maximize, ShieldAlert, Timer } from "lucide-react";
import { api } from "@/lib/api";
import { getAttempt, keys } from "@/lib/queries";
import { cn, friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { useFaceWatch } from "@/lib/use-face-watch";
import { ErrorState } from "@/components/nexus/common";
import { Alert, Badge, Button, Card, Kbd, Progress, Skeleton } from "@/components/ui/primitives";

const NO_COUNTS = { tab_switch: 0, full_screen_exit: 0, copy_attempt: 0, paste_attempt: 0 };
const LABELS = { tab_switch: "left the page", full_screen_exit: "left full screen", copy_attempt: "copy attempts", paste_attempt: "paste attempts" };

/**
 * Assessment mode only (the student chose it and accepted the notice).
 * Blocks copy, cut, paste, right-click and the matching shortcuts; counts leaving the page or full screen.
 * The browser can only report what it sees: this does not stop a second device or a photo of the screen.
 */
function useAssessment(id, aid, on, finished, onViolation) {
  const [counts, setCounts] = useState(NO_COUNTS);
  const [fullscreen, setFullscreen] = useState(false);
  const wasFull = useRef(false);
  const lastLeave = useRef(0);
  const violation = useRef(onViolation);
  violation.current = onViolation;

  useEffect(() => {
    if (!on) return;
    const armedAt = Date.now() + 2500; // page changes and permission prompts right at the start are not violations
    const record = (type, message) => {
      if (finished.current) return;
      setCounts((c) => ({ ...c, [type]: c[type] + 1 }));
      api(`/subjects/${id}/quiz/attempts/${aid}/events`, { method: "POST", json: { event_type: type } }).catch(() => {});
      if (message) toast.warning(message, { id: "assessment-block" });
    };
    const block = (e) => e.preventDefault();
    const onCopy = (e) => { e.preventDefault(); record("copy_attempt", "Copying is turned off during an assessment. This was counted."); };
    const onPaste = (e) => { e.preventDefault(); record("paste_attempt", "Pasting is turned off during an assessment. This was counted."); };
    const onKey = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      const k = e.key.toLowerCase();
      if (k === "c" || k === "x" || k === "insert") { e.preventDefault(); record("copy_attempt", "Copying is turned off during an assessment. This was counted."); }
      else if (k === "v") { e.preventDefault(); record("paste_attempt", "Pasting is turned off during an assessment. This was counted."); }
      else if (["a", "p", "s", "u"].includes(k)) e.preventDefault(); // select all, print, save, view source
    };
    const leave = () => {
      const now = Date.now();
      if (now - lastLeave.current < 1500) return; // switching tabs fires both "hidden" and "blur": count it once
      lastLeave.current = now;
      if (now < armedAt) return;
      record("tab_switch", "You left the assessment page.");
      violation.current("tab_switch"); // the assessment ends at once
    };
    const onHidden = () => { if (document.hidden) leave(); };
    const onFull = () => {
      const now = !!document.fullscreenElement;
      setFullscreen(now);
      if (wasFull.current && !now && Date.now() >= armedAt) { record("full_screen_exit", "You left full screen."); violation.current("full_screen_exit"); }
      wasFull.current = now;
    };
    setFullscreen(!!document.fullscreenElement);
    wasFull.current = !!document.fullscreenElement;
    document.addEventListener("copy", onCopy);
    document.addEventListener("cut", onCopy);
    document.addEventListener("paste", onPaste);
    document.addEventListener("keydown", onKey, true);
    document.addEventListener("contextmenu", block);
    document.addEventListener("dragstart", block);
    document.addEventListener("visibilitychange", onHidden);
    window.addEventListener("blur", leave);
    document.addEventListener("fullscreenchange", onFull);
    return () => {
      document.removeEventListener("copy", onCopy);
      document.removeEventListener("cut", onCopy);
      document.removeEventListener("paste", onPaste);
      document.removeEventListener("keydown", onKey, true);
      document.removeEventListener("contextmenu", block);
      document.removeEventListener("dragstart", block);
      document.removeEventListener("visibilitychange", onHidden);
      window.removeEventListener("blur", leave);
      document.removeEventListener("fullscreenchange", onFull);
    };
  }, [id, aid, on, finished]);

  const enterFullscreen = () => document.documentElement.requestFullscreen?.().catch(() => toast.error("Your browser did not allow full screen."));
  return { counts, fullscreen, enterFullscreen };
}

function Mcq({ id, aid, st, refresh }) {
  const [chosen, setChosen] = useState(null);
  const [problem, setProblem] = useState("");
  const t0 = useRef(Date.now());
  const changes = useRef(0);
  const it = st.item;
  const submit = useMutation({
    mutationFn: () => api(`/subjects/${id}/quiz/attempts/${aid}/answer`, {
      method: "POST", json: { answer_row_id: it.answer_row_id, item_id: it.item_id, chosen, response_time: (Date.now() - t0.current) / 1000, hesitations: changes.current },
    }),
    onSuccess: (r) => {
      if (r?.backtrack) toast.info(`Stepping back to the basics: ${r.backtrack.to.join(", ")}`, { id: "backtrack" });
      return refresh();
    },
    onError: (e) => setProblem(friendlyError(e)),
  });
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.closest?.("input[type=text],textarea")) return;
      const n = "1234".indexOf(e.key);
      const l = "abcd".indexOf(e.key.toLowerCase());
      const pick = n >= 0 ? n : l;
      if (pick >= 0 && pick < it.options.length) { if (chosen !== null && chosen !== pick) changes.current += 1; setChosen(pick); }
      if (e.key === "Enter" && chosen !== null && !submit.isPending) { e.preventDefault(); submit.mutate(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [chosen, it.options.length, submit]);
  return (
    <form onSubmit={(e) => { e.preventDefault(); if (chosen !== null) submit.mutate(); }}>
      {it.backtrack && (
        <Alert tone="info" icon={CornerDownLeft} className="mb-4" title="Checking the foundations">
          A question about <b>{it.backtrack.from}</b> went wrong, so here is one from <b>{it.backtrack.topic}</b>, which it builds on.
        </Alert>
      )}
      <Card className="p-6 sm:p-7">
        <fieldset>
          <legend className="w-full">
            {(it.topic || it.topic_path) && <Badge tone="neutral" className="mb-3">{(it.topic || it.topic_path).split(" › ").pop()}</Badge>}
            <span className="break-anywhere block font-display text-[21px] font-semibold leading-snug">{it.question}</span>
          </legend>
          <div className="mt-5 space-y-2.5">
            {it.options.map((opt, i) => (
              <label key={i} className={cn("group flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3.5 transition-all has-[:focus-visible]:ring-4 has-[:focus-visible]:ring-brand/20",
                chosen === i ? "border-brand bg-brand-wash shadow-[0_0_0_3px_rgb(1_148_226/.12)]" : "border-border bg-surface hover:border-brand/40 hover:bg-brand-wash/50")}>
                <input type="radio" name="choice" className="sr-only" checked={chosen === i} onChange={() => { if (chosen !== null) changes.current += 1; setChosen(i); }} />
                <span className={cn("grid h-8 w-8 shrink-0 place-items-center rounded-lg text-sm font-bold transition-colors", chosen === i ? "bg-brand text-white" : "bg-brand-soft/70 text-brand-deep group-hover:bg-brand-soft")}>{String.fromCharCode(65 + i)}</span>
                <span className="break-anywhere text-[15px]">{opt}</span>
              </label>
            ))}
          </div>
        </fieldset>
        {problem && <Alert tone="danger" className="mt-4">{problem}</Alert>}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <p className="hidden text-[12.5px] text-muted sm:block">Keys <Kbd>A</Kbd>–<Kbd>D</Kbd> choose, <Kbd>Enter</Kbd> confirms</p>
          <Button type="submit" size="lg" disabled={chosen === null} loading={submit.isPending}>{st.position === st.total_questions ? "Finish quiz" : "Next question"}<ArrowRight className="h-4 w-4" /></Button>
        </div>
      </Card>
    </form>
  );
}

export default function QuizRun() {
  const { id, aid } = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const finished = useRef(false);
  const { data: st, error, isPending, refetch } = useQuery({
    queryKey: keys.attempt(id, aid), queryFn: () => getAttempt(id, aid), refetchOnWindowFocus: false, staleTime: Infinity, retry: false,
  });
  const assessment = st?.attempt.mode === "assessment"; // stored with the quiz, so resuming it keeps the same rules
  useTitle(assessment ? "Assessment" : "Quiz");

  // The assessment ends the moment a rule is broken: tell the server, then show the result of what was answered so far.
  const end = async (reason) => {
    if (finished.current) return;
    finished.current = true;
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
    try { await api(`/subjects/${id}/quiz/attempts/${aid}/terminate`, { method: "POST", json: { reason } }); } catch {}
    await qc.invalidateQueries({ queryKey: keys.quiz(id) });
    router.replace(`/subjects/${id}/quiz/${aid}/result`);
  };
  const guard = useAssessment(id, aid, assessment, finished, end);
  const face = useFaceWatch({ on: assessment, onViolation: end });

  // Optional time limit (chosen when the quiz was started): counts down, warns at one minute, ends the quiz at zero.
  const [left, setLeft] = useState(null);
  useEffect(() => {
    let deadline = null;
    try { deadline = Number(localStorage.getItem(`nexus.deadline.${aid}`)) || null; } catch {}
    if (!deadline) return undefined;
    const tick = async () => {
      const secs = Math.max(0, Math.round((deadline - Date.now()) / 1000));
      setLeft(secs);
      if (secs === 60) toast.warning("One minute left.", { id: "time-left" });
      if (secs === 0 && !finished.current) {
        clearInterval(timer);
        finished.current = true;
        if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
        toast.info("Time is up. The quiz has ended.");
        try { await api(`/subjects/${id}/quiz/attempts/${aid}/finish`, { method: "POST" }); } catch {}
        await qc.invalidateQueries({ queryKey: keys.quiz(id) });
        router.replace(`/subjects/${id}/quiz/${aid}/result`);
      }
    };
    const timer = setInterval(tick, 1000);
    tick();
    return () => clearInterval(timer);
  }, [aid, id, qc, router]);
  useEffect(() => {
    if (st?.state !== "complete") return;
    finished.current = true; // leaving full screen now is not an event
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
    qc.invalidateQueries({ queryKey: keys.quiz(id) });
    router.replace(`/subjects/${id}/quiz/${aid}/result`);
  }, [st?.state, id, aid, router, qc]);
  const refresh = () => qc.invalidateQueries({ queryKey: keys.attempt(id, aid) });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending || st.state === "complete") return <Skeleton className="h-48" />;
  const pct = Math.round(((st.position - 1) / st.total_questions) * 100);
  const total = Object.values(guard.counts).reduce((n, x) => n + x, 0);
  return (
    <div className={cn("mx-auto max-w-3xl", assessment && "select-none")}>
      {assessment && (
        <Alert tone="info" icon={ShieldAlert} className="mb-4" title="Assessment mode">
          The camera checks that your face is visible, and copy and paste are blocked. It ends at once if you leave this page or full screen, or if no face (6 s) or more than one face (3 s) is seen.
          <span aria-live="polite" className="mt-1 block">Focus events so far: <b>{total}</b>{total > 0 && <> ({Object.entries(guard.counts).filter(([, n]) => n > 0).map(([k, n]) => `${n} ${LABELS[k]}`).join(", ")})</>}</span>
          {!guard.fullscreen && <Button size="sm" variant="secondary" className="mt-2" onClick={guard.enterFullscreen}><Maximize className="h-4 w-4" />Enter full screen</Button>}
        </Alert>
      )}
      {assessment && (
        <div className="fixed bottom-20 right-3 z-30 w-36 overflow-hidden rounded-xl border border-border bg-surface shadow-pop sm:bottom-4 sm:right-4 sm:w-44">
          <video ref={face.videoRef} muted playsInline className="aspect-[4/3] w-full -scale-x-100 object-cover" aria-hidden="true" />
          <p role="status" aria-live="polite" className={cn("flex items-center gap-1 px-2 py-1.5 text-xs font-semibold", face.faces === 1 && !face.secondsLeft ? "text-strong" : "text-weak")}>
            <Camera className="h-3 w-3 shrink-0" aria-hidden="true" />
            {face.status === "error" ? face.problem : face.status !== "ready" ? "Starting camera…" : face.secondsLeft ? `${face.faces === 0 ? "No face" : "More than one face"}: ends in ${face.secondsLeft}s` : face.faces === 1 ? "Face detected" : "Checking…"}
          </p>
        </div>
      )}
      <div className="mb-5 flex items-center gap-4">
        <div className="flex-1">
          <p className="mb-1.5 flex items-center justify-between text-sm font-semibold"><span>Question <span className="tabular">{st.position}</span> of <span className="tabular">{st.total_questions}</span></span>
            {left !== null && <span aria-live="off" className={cn("tabular inline-flex items-center gap-1 rounded-full px-2.5 py-0.5", left <= 60 ? "bg-weak-bg text-weak" : "bg-brand-soft text-brand-deep")}><Timer className="h-3.5 w-3.5" />{String(Math.floor(left / 60)).padStart(2, "0")}:{String(left % 60).padStart(2, "0")}</span>}</p>
          <Progress value={pct} aria-label="Quiz progress" />
        </div>
      </div>
      <Mcq key={st.item.answer_row_id} id={id} aid={aid} st={st} refresh={refresh} />
    </div>
  );
}
