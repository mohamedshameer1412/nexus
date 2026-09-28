// Records a ~30 s highlights reel: splash, sign-in, dashboard, competency, learning path, assessment, AI Tutor, profile.
// Needs backend on :8100, frontend on :3000, seeded demo account.  Usage: node scripts/record-highlights.mjs [outDir]
import { chromium } from "playwright";
import { mkdirSync, renameSync } from "node:fs";

const BASE = "http://localhost:3000";
const OUT = process.argv[2] || "demo-video";
const SIZE = { width: 1440, height: 900 };
const ROUTES = ["/", "/login", "/dashboard", "/competency", "/learn", "/assess", "/ai-tutor", "/profile"];

const browser = await chromium.launch();

// Warm-up off camera so the dev server has compiled every route.
{
  const ctx = await browser.newContext({ viewport: SIZE });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await p.fill('input[name="email"]', "demo@nexus.local");
  await p.fill('input[name="password"]', "nexus-demo-2026");
  await p.click('button[type="submit"]');
  await p.waitForURL(/dashboard/);
  for (const r of ROUTES) await p.goto(BASE + r, { waitUntil: "networkidle" }).catch(() => {});
  await ctx.close();
}

mkdirSync(OUT, { recursive: true });
const ctx = await browser.newContext({ viewport: SIZE, recordVideo: { dir: OUT, size: SIZE } });
const p = await ctx.newPage();
const wait = (ms) => p.waitForTimeout(ms);
const nav = async (label, url) => { await p.getByRole("link", { name: label, exact: true }).first().click(); await p.waitForURL(url); };

// 1. Splash → it forwards to sign-in by itself
await p.goto(BASE + "/", { waitUntil: "networkidle" });
await p.waitForURL(/login/, { timeout: 15000 });
await wait(1000);

// 2. Sign in with the demo account
await p.getByRole("button", { name: "Use this" }).click();
await wait(900);
await p.click('button[type="submit"]');
await p.waitForURL(/dashboard/);

// 3. Dashboard, with a glance at the charts
await wait(2800);
await p.mouse.wheel(0, 520);
await wait(1600);
await p.mouse.wheel(0, -520);
await wait(500);

// 4. Competency profile
await nav("Progress", /competency/);
await wait(2800);

// 5. Learning path
await nav("Learn", /learn/);
await wait(2300);

// 6. Diagnostic assessment: pick an answer
await nav("Assess", /assess/);
await wait(1200);
await p.getByRole("radio").nth(1).click();
await wait(1300);

// 7. AI Tutor with explainability panel
await nav("AI Tutor", /ai-tutor/);
await wait(1500);
await p.getByRole("button", { name: "Give Example" }).click();
await wait(3200);

// 8. Profile
await p.getByRole("link", { name: "Profile" }).first().click();
await p.waitForURL(/profile/);
await wait(2200);

const video = p.video();
await ctx.close();
await browser.close();
const out = `${OUT}/nexus-highlights-30s.webm`;
renameSync(await video.path(), out);
console.log("saved", out);
