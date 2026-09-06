"use client";
import { useState } from "react";
import { motion } from "framer-motion";

export default function CareerGapPage() {
  const [jd, setJd]           = useState("");
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  async function analyze() {
    if (jd.trim().length < 50) { setError("Paste a job description (min 50 characters)"); return; }
    setLoading(true); setError(""); setResult(null);
    try {
      const res  = await fetch("/api/nexus/twin/career-gap/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify({ job_description: jd }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Analysis failed");
      setResult(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="flex flex-col gap-8 p-6 md:p-10 animate-fade-in w-full max-w-5xl mx-auto">
      <div className="flex flex-col gap-2">
        <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">
          Career Skill Gap Analyzer
        </h1>
        <p className="text-muted-foreground text-lg">
          Paste a job description. NEXUS compares it against your verified skills
          in your Digital Twin and tells you exactly what to study next.
        </p>
      </div>

      <div className="card-enterprise p-6 flex flex-col gap-4">
        <label className="font-semibold text-foreground/90">Job Description Target</label>
        <textarea
          className="w-full bg-input/50 border border-border rounded-lg p-4 text-foreground focus:ring-2 focus:ring-primary focus:border-transparent transition-all min-h-[200px] resize-y"
          value={jd}
          onChange={e => setJd(e.target.value)}
          placeholder="Paste job description or required skills here..."
        />
        <div className="flex justify-between items-center text-sm text-muted-foreground">
          <span>{jd.length} characters</span>
          {jd.length > 0 && jd.length < 50 && <span className="text-warning">Min 50 characters required</span>}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium animate-slide-in">
          {error}
        </div>
      )}

      <button 
        className="btn-enterprise-primary w-full md:w-auto md:self-end text-lg py-3 px-8 shadow-soft hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
        onClick={analyze} 
        disabled={loading || jd.length < 50}
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Analyzing Neural Gap...
          </span>
        ) : "Analyze Skill Gap"}
      </button>

      {result && <GapResult result={result} />}
    </div>
  );
}

function GapResult({ result }) {
  const { matched, missing, match_pct, recommended_topics } = result;
  
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (match_pct / 100) * circumference;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }} 
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-8 mt-4"
    >
      <div className="card-enterprise p-8 flex flex-col md:flex-row items-center gap-8">
        <div className="relative w-32 h-32 flex items-center justify-center shrink-0">
          <svg className="transform -rotate-90 w-full h-full">
            <circle cx="64" cy="64" r={radius} stroke="currentColor" strokeWidth="8" fill="transparent" className="text-muted/30" />
            <circle 
              cx="64" cy="64" r={radius} 
              stroke="currentColor" strokeWidth="8" fill="transparent" 
              strokeDasharray={circumference} 
              strokeDashoffset={strokeDashoffset}
              className="text-success transition-all duration-1000 ease-out" 
            />
          </svg>
          <div className="absolute flex flex-col items-center justify-center">
            <span className="text-3xl font-bold text-foreground">{match_pct.toFixed(0)}%</span>
          </div>
        </div>
        <div className="flex flex-col gap-2 text-center md:text-left">
          <h2 className="text-2xl font-bold text-foreground">Career Readiness Score</h2>
          <p className="text-muted-foreground text-lg">
            You have <strong className="text-success">{matched?.length ?? 0}</strong> out of <strong className="text-foreground">{result.total_required}</strong> critical skills required for this role based on your verified Nexus Digital Twin.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card-enterprise p-6 flex flex-col gap-4 border-t-4 border-t-success bg-gradient-to-b from-success/5 to-transparent">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-success/20 flex items-center justify-center text-success font-bold">✓</div>
            <h3 className="text-xl font-semibold">Verified Skills</h3>
          </div>
          {matched?.length === 0 && <p className="text-muted-foreground italic p-4 bg-muted/20 rounded-lg">No verified skills matched yet. Keep learning!</p>}
          <div className="flex flex-wrap gap-3 mt-2">
            {matched?.map((s, i) => (
              <div key={i} className="flex items-center gap-2 bg-success/10 border border-success/30 px-3 py-1.5 rounded-full text-sm">
                <span className="text-foreground font-medium">{s.skill}</span>
                <span className="text-success font-bold text-xs bg-success/20 px-1.5 py-0.5 rounded">{(s.confidence * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card-enterprise p-6 flex flex-col gap-4 border-t-4 border-t-destructive bg-gradient-to-b from-destructive/5 to-transparent">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-destructive/20 flex items-center justify-center text-destructive font-bold">✗</div>
            <h3 className="text-xl font-semibold">Missing Skills</h3>
          </div>
          {missing?.length === 0 && <p className="text-success font-medium p-4 bg-success/10 rounded-lg">No gaps detected! You are fully qualified.</p>}
          <div className="flex flex-wrap gap-2 mt-2">
            {missing?.map((s, i) => (
              <div key={i} className="bg-destructive/10 border border-destructive/20 text-destructive/90 px-3 py-1.5 rounded-full text-sm font-medium">
                {s.skill}
              </div>
            ))}
          </div>
        </div>
      </div>

      {recommended_topics?.length > 0 && (
        <div className="card-enterprise p-6 flex flex-col gap-4 bg-gradient-to-br from-card to-primary/5 border border-primary/20">
          <h3 className="text-xl font-semibold flex items-center gap-2">
            <span className="text-2xl">📚</span> Recommended Nexus Study Paths
          </h3>
          <p className="text-muted-foreground">Master these topics in the Nexus Tutor to close your skill gap instantly.</p>
          <div className="flex flex-wrap gap-4 mt-2">
            {recommended_topics.map((t, i) => (
              <a 
                key={i} 
                href={`/nexus/tutor?topic_id=${encodeURIComponent(t)}`} 
                className="group relative overflow-hidden bg-background border border-primary/30 hover:border-primary px-6 py-4 rounded-xl transition-all hover:-translate-y-1 hover:shadow-[0_4px_20px_rgba(99,102,241,0.2)] flex items-center gap-3"
              >
                <div className="absolute inset-0 w-1 bg-primary group-hover:w-full transition-all duration-300 opacity-10 group-hover:opacity-20" />
                <span className="relative text-foreground font-semibold text-lg">{t}</span>
                <span className="relative text-primary opacity-0 group-hover:opacity-100 transition-opacity transform translate-x-[-10px] group-hover:translate-x-0">→</span>
              </a>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}