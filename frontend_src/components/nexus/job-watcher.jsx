"use client";
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getActiveJobs, getMcqJob, keys } from "@/lib/queries";

const BASE_TITLE_KEY = "__nexusBaseTitle";

/** Watches question-writing jobs wherever the student is in the app, and says so when one finishes: a toast, a mark in the tab title,
 *  and a system notification when the tab is in the background and the student allowed notifications. */
export function JobWatcher() {
  const qc = useQueryClient();
  const router = useRouter();
  const seen = useRef(new Map());
  const { data } = useQuery({
    queryKey: keys.activeJobs, queryFn: getActiveJobs,
    refetchInterval: (q) => (q.state.data?.jobs?.length ? 4000 : 20000),
    refetchIntervalInBackground: true,                     // a hidden tab keeps checking, so the result is waiting when the student comes back
    retry: false,
  });

  useEffect(() => {
    const restore = () => {
      if (document.hidden) return;
      if (window[BASE_TITLE_KEY]) { document.title = window[BASE_TITLE_KEY]; window[BASE_TITLE_KEY] = null; }
    };
    document.addEventListener("visibilitychange", restore);
    return () => document.removeEventListener("visibilitychange", restore);
  }, []);

  useEffect(() => {
    if (!data) return;
    const now = new Set(data.jobs.map((j) => j.id));
    data.jobs.forEach((j) => seen.current.set(j.id, j));
    for (const [id, job] of [...seen.current]) {
      if (now.has(id)) continue;
      seen.current.delete(id);
      finished(job);
    }
    async function finished(job) {
      let result = null;
      try { result = await getMcqJob(job.subject_id, job.id); } catch {}
      qc.invalidateQueries({ queryKey: keys.mcq(String(job.subject_id)) });
      qc.invalidateQueries({ queryKey: keys.quiz(String(job.subject_id)) });
      qc.invalidateQueries({ queryKey: keys.mcqJob(String(job.subject_id), job.id) });
      qc.invalidateQueries({ queryKey: keys.subjects });
      const made = result?.produced ?? 0;
      const ok = result?.status === "done" && made > 0;
      const text = ok ? `Your questions for “${job.subject}” are ready: ${made} added.` : result?.status === "failed" ? `Writing questions for “${job.subject}” did not finish. Try again.` : `No question for “${job.subject}” passed the checks this time. Nothing was made up.`;
      const go = () => router.push(`/subjects/${job.subject_id}/practice`);
      (ok ? toast.success : toast.warning)(text, { duration: 12000, action: { label: "Open", onClick: go } });
      if (document.hidden) {
        if (!window[BASE_TITLE_KEY]) window[BASE_TITLE_KEY] = document.title;
        document.title = `${ok ? "✓ Questions ready" : "Questions finished"} · ${window[BASE_TITLE_KEY]}`;
        try {
          if (typeof Notification !== "undefined" && Notification.permission === "granted") {
            const n = new Notification("Nexus", { body: text, tag: `job-${job.id}` });
            n.onclick = () => { window.focus(); go(); };
          }
        } catch {}
      }
    }
  }, [data, qc, router]);

  return null;
}

/** Ask once, from a click, to be told when a long job finishes while the tab is in the background. */
export function askToBeNotified() {
  try {
    if (typeof Notification !== "undefined" && Notification.permission === "default") Notification.requestPermission();
  } catch {}
}
