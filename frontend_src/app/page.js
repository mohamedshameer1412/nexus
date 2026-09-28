"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { GovLine, Lockup, TAGLINE, Waves } from "@/components/nexus/auth";
import { fetchSession } from "@/lib/api";

const PILLARS = [["skills", "Smarter\nSkills"], ["learning", "Continuous\nLearning"], ["officers", "Stronger\nOfficers"], ["data", "Data-Driven\nNation"]];
const LOAD_MS = 2600;

/** Splash: the brand screen while the session is checked, then on to the dashboard or sign-in. */
export default function Splash() {
  const router = useRouter();
  useEffect(() => {
    document.title = "NEXUS · Adaptive Competency & Career Learning Loop";
    const session = fetchSession().catch(() => ({ authenticated: false }));
    const t = setTimeout(async () => router.replace((await session).authenticated ? "/dashboard" : "/login"), LOAD_MS);
    return () => clearTimeout(t);
  }, [router]);

  return (
    <main className="relative min-h-dvh overflow-hidden bg-gradient-to-br from-[#F7FAFE] via-[#EAF4FF] to-[#DCEBFF]">
      <Waves />
      <div className="relative mx-auto grid min-h-dvh max-w-[1280px] items-center px-6 py-10 lg:grid-cols-[1fr_1.1fr] lg:px-14">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }} className="flex flex-col items-center">
          <GovLine />
          <Lockup className="mt-4 lg:mt-6" />
          <p className="mt-4 text-center text-[14px] font-medium italic leading-relaxed text-[#1450B8] lg:hidden">{TAGLINE.join(" ")}</p>
          <img src="/assets/generated/government-building.png" alt="" aria-hidden="true" className="mt-4 w-[230px] lg:hidden [mask-image:linear-gradient(to_bottom,black_82%,transparent)]" />
          <div className="mt-5 flex w-full max-w-[380px] lg:mt-8 items-center gap-3" role="progressbar" aria-label="Loading NEXUS">
            <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-[#CFE0FA]">
              <motion.div className="h-full rounded-full bg-gradient-to-r from-[#1464E8] to-[#3B8BFF]" initial={{ width: "4%" }} animate={{ width: "100%" }} transition={{ duration: LOAD_MS / 1000, ease: "easeInOut" }} />
            </div>
            <span className="text-[13px] font-medium text-[#5A6E8C]">Loading…</span>
          </div>
          <ul className="mt-6 grid w-full max-w-[460px] lg:mt-10 grid-cols-4 divide-x divide-[#C9DBF5]">
            {PILLARS.map(([icon, label], i) => (
              <motion.li key={icon} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 + i * 0.1 }} className="flex flex-col items-center gap-2 px-2 text-center">
                <img src={`/assets/generated/icon-${icon}.png`} alt="" aria-hidden="true" className="h-11 w-11 object-contain" />
                <span className="whitespace-pre-line text-[12.5px] font-semibold leading-tight text-[#0B2A5B]">{label}</span>
              </motion.li>
            ))}
          </ul>
          <button type="button" onClick={() => router.replace("/login")} className="mt-5 text-[13px] font-semibold text-[#1464E8] lg:mt-8 underline-offset-4 hover:underline">Skip</button>
        </motion.div>

        <div className="relative hidden h-full lg:block">
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}
            className="absolute right-0 top-4 text-right font-serif text-[20px] italic leading-relaxed text-[#1450B8]">
            {TAGLINE.map((t) => <span key={t} className="block">{t}</span>)}
          </motion.p>
          <motion.img initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 1 }}
            src="/assets/generated/government-building.png" alt="" aria-hidden="true" className="absolute bottom-6 right-0 w-[620px] max-w-full [mask-image:linear-gradient(to_bottom,black_82%,transparent)]" />
        </div>
      </div>
    </main>
  );
}
