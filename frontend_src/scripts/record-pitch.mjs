// Records the clips for the ~30 s solution demo of the 60-second pitch, in script order:
//   desktop: home → sign-in → dashboard | competency | AI Tutor | dashboard charts
//   mobile:  learning path → course details | uploaded material → AI-written MCQ → checked answer
// Writes desktop.webm, mobile.webm and segments.json (start/end seconds of each segment) to outDir;
// scripts/compose-pitch.py cuts and joins them into one video.
// Needs backend on :8100, frontend on :3000, the demo account and the "Official Statistics" subject with practice questions.
// Usage: node scripts/record-pitch.mjs <outDir> <subjectId>
import { chromium } from "playwright";
import { mkdirSync, renameSync, writeFileSync } from "node:fs";

const BASE = "http://localhost:3000";
const OUT = process.argv[2] || "pitch";
const SUBJECT = process.argv[3] || "3";
const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };

// A visible pointer (desktop) or touch dot (mobile): headless recordings show no cursor otherwise.
const pointer = (touch) => `
  addEventListener("DOMContentLoaded", () => {
    const d = document.createElement("div");
    d.style.cssText = "position:fixed;z-index:2147483647;pointer-events:none;left:-40px;top:-40px;transition:transform .08s;" +
      ${touch ? '"width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;background:rgba(20,100,232,.28);border:2px solid rgba(20,100,232,.7);"'
              : '"width:22px;height:22px;background:url(\\"data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27%3E%3Cpath d=%27M3 2l7 19 2.6-7.4L20 11z%27 fill=%27%230B2A5B%27 stroke=%27white%27 stroke-width=%271.5%27/%3E%3C/svg%3E\\") no-repeat;"'};
    document.body.appendChild(d);
    addEventListener("mousemove", (e) => { d.style.left = e.clientX + "px"; d.style.top = e.clientY + "px"; }, true);
    addEventListener("mousedown", () => { d.style.transform = "scale(.8)"; }, true);
    addEventListener("mouseup", () => { d.style.transform = ""; }, true);
  });`;

async function signIn(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill('input[name="email"]', "demo@nexus.local");
  await page.fill('input[name="password"]', "nexus-demo-2026");
  await page.click('button[type="submit"]');
  await page.waitForURL(/dashboard/);
}

const browser = await chromium.launch();

// Warm-up: compile every route and keep a signed-in state for the mobile clip.
const warm = await browser.newContext({ viewport: DESKTOP });
{
  const p = await warm.newPage();
  await signIn(p);
  for (const r of ["/", "/competency", "/learn", "/learn/data-visualization", "/ai-tutor", `/subjects/${SUBJECT}/materials`, `/subjects/${SUBJECT}/practice`, "/dashboard"])
    await p.goto(BASE + r, { waitUntil: "networkidle" }).catch(() => {});
}
const signedIn = await warm.storageState();
await warm.close();

mkdirSync(OUT, { recursive: true });
const segments = [];

async function recorder(name, options, touch) {
  // The screencast is taken at CSS-pixel size whatever the device scale, so the video is the viewport size.
  const ctx = await browser.newContext({ ...options, bypassCSP: true, recordVideo: { dir: OUT, size: options.viewport } });
  await ctx.addInitScript(pointer(touch));
  const page = await ctx.newPage();
  const t0 = Date.now();
  const now = () => (Date.now() - t0) / 1000;
  const wait = (ms) => page.waitForTimeout(ms);
  // Move the visible pointer to an element, then click it.
  const click = async (locator) => {
    const el = locator.first();
    await el.evaluate((e) => e.scrollIntoView({ block: "center", behavior: "instant" }));   // clear of fixed headers and the bottom bar
    await wait(150);
    const b = await el.boundingBox();
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 14 });
    await wait(120);
    await el.click();
  };
  // A segment is one or more kept intervals of the clip; `gap` runs a page load that is cut out of the video.
  const seg = async (id, fn) => {
    const parts = [];
    let from = now();
    const gap = async (load) => {
      parts.push([from, now()]);
      await load();
      await page.waitForLoadState("networkidle").catch(() => {});
      await wait(450);                                           // let the entrance animation settle
      from = now();
    };
    await fn(gap);
    parts.push([from, now()]);
    segments.push({ id, clip: name, parts: parts.filter(([a, b]) => b - a > 0.2) });
  };
  return { ctx, page, wait, click, seg,
    async finish() { const v = page.video(); await ctx.close(); renameSync(await v.path(), `${OUT}/${name}.webm`); } };
}

// ---------------------------------------------------------------- desktop
{
  const r = await recorder("desktop", { viewport: DESKTOP }, false);
  const { page, wait, click, seg } = r;
  await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });
  await page.locator('img[src*="nexus-lockup"]').first().waitFor();
  await wait(500);                                               // let the splash fade in before the first kept frame
  await seg("1-home-dashboard", async (gap) => {
    await wait(1700);                                            // splash
    await gap(() => page.waitForURL(/login/, { timeout: 15000 })); // it forwards to sign-in by itself
    await wait(300);
    await click(page.getByRole("button", { name: "Use this" }));
    await wait(250);
    await click(page.locator('button[type="submit"]'));
    await gap(() => page.waitForURL(/dashboard/));
    await wait(2400);                                            // "NEXUS gives every officer a live competency score." 
  });
  await seg("2-competency", async (gap) => {
    await gap(async () => { await click(page.getByRole("link", { name: "Progress", exact: true })); await page.waitForURL(/competency/); });
    await wait(1400);                                            // "It compares their skills with what their role needs ..."
    await page.mouse.move(1180, 640, { steps: 16 });             // over the skill radar: score against target
    await wait(2200);
  });
  await seg("4-ai-tutor", async (gap) => {
    await gap(async () => { await click(page.getByRole("link", { name: "AI Tutor", exact: true })); await page.waitForURL(/ai-tutor/); });
    await wait(600);                                             // "An AI tutor answers doubts, and shows the evidence ..."
    await click(page.getByRole("button", { name: "Give Example" }));
    await wait(2300);                                            // reply + "Why this answer?" panel
    await page.mouse.move(1230, 420, { steps: 14 });             // towards the evidence
    await wait(1300);
  });
  await seg("6-dashboard-progress", async (gap) => {
    await gap(async () => { await click(page.getByRole("link", { name: "Dashboard", exact: true })); await page.waitForURL(/dashboard/); });
    await wait(700);                                             // "Assess, learn, reassess ..."
    await page.mouse.wheel(0, 760);                              // monthly activity + learning progress charts
    await wait(3600);
  });
  await r.finish();
}

// ---------------------------------------------------------------- mobile
{
  const r = await recorder("mobile", { viewport: PHONE, isMobile: true, hasTouch: true, storageState: signedIn }, true);
  const { page, wait, click, seg } = r;
  await page.goto(`${BASE}/learn`, { waitUntil: "networkidle" });
  await seg("3-learning-path", async (gap) => {
    await wait(2500);                                            // "Those gaps drive a personal learning path ..."                                             // prioritised path: iGOT / TPAC steps with status
    await click(page.getByRole("link", { name: /Data Visualization for Governance/ }));
    await gap(() => page.waitForURL(/learn\/data-visualization/));
    await wait(2700);                                            // "... iGOT Karmayogi courses, from a sample catalogue"                                             // course details: source, weeks, key learnings
  });
  await seg("5-material-to-mcq", async (gap) => {
    await gap(() => page.goto(`${BASE}/subjects/${SUBJECT}/materials`, { waitUntil: "networkidle" }));
    await wait(1600);                                            // "Officers upload their own study material ..." 
    await click(page.getByRole("link", { name: "Practice", exact: true }));
    const card = page.locator("li").filter({ hasText: "correlation coefficient" }).filter({ has: page.getByRole("radio") }).first();
    await gap(async () => {
      await page.waitForURL(/practice/);
      await card.waitFor();
      await card.evaluate((e) => e.scrollIntoView({ block: "center", behavior: "instant" }));
    });
    await wait(500);
    await click(card.getByRole("radio", { name: /-1 to \+1/ }));
    await wait(300);
    await click(card.getByRole("button", { name: /Check answer/ }));
    await wait(2500);                                            // "... and the AI turns it into quizzes." 
  });
  await r.finish();
}

await browser.close();
writeFileSync(`${OUT}/segments.json`, JSON.stringify(segments, null, 2));
console.log(JSON.stringify(segments));
