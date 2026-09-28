// Records a demo walkthrough video. Needs backend on :8100, frontend on :3000, seeded demo account.
// Usage: node scripts/record-demo.mjs [outDir]
import { chromium } from "playwright";
import { mkdirSync, renameSync } from "node:fs";

const BASE = "http://localhost:3000";
const OUT = process.argv[2] || "demo-video";
const SIZE = { width: 1440, height: 900 };
const S = 1; // subject id
const PAGES = [
  "/dashboard", "/competency", "/learn", "/learn/data-visualization", "/assess", "/ai-tutor", "/profile", "/subjects", `/subjects/${S}`, `/subjects/${S}/materials`, `/subjects/${S}/ask`,
  `/subjects/${S}/practice`, `/subjects/${S}/quiz`, `/subjects/${S}/progress`, `/subjects/${S}/roadmap`,
  `/subjects/${S}/outlook`, `/subjects/${S}/notes`, `/subjects/${S}/twin`, `/subjects/${S}/agents`,
  `/subjects/${S}/report`, "/career", "/search", "/account",
];

const pause = (p, ms) => p.waitForTimeout(ms);

// On the real (non-warm-up) pass, use the on-page "Use this" demo-credentials button
// instead of typing, so the recording shows that feature working.
async function login(page, demo = false) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await pause(page, demo ? 2000 : 500);
  if (demo) {
    await page.getByRole("button", { name: "Use this" }).click();
    await pause(page, 1200);
  } else {
    await page.fill('input[name="email"]', "demo@nexus.local", { timeout: 15000 });
    await page.fill('input[name="password"]', "nexus-demo-2026");
  }
  await pause(page, 500);
  await page.click('button[type="submit"]');
  await page.waitForURL(/dashboard/, { timeout: 30000 });
}

// A few small interactions per page, so the recording shows a working app, not a slideshow.
const INTERACT = {
  "/competency": async (page, dwell) => {
    for (const tab of ["Domain Skills", "Career Path", "Overview"]) {
      await page.getByRole("tab", { name: tab }).click().catch(() => {});
      await pause(page, dwell * 0.6);
    }
  },
  "/assess": async (page, dwell) => {
    await page.getByRole("radio").first().click().catch(() => {});
    await pause(page, dwell * 0.5);
    await page.getByRole("button", { name: /^Next/ }).click().catch(() => {});
    await pause(page, dwell * 0.5);
  },
  "/ai-tutor": async (page, dwell) => {
    await page.getByRole("button", { name: "Give Example" }).click().catch(() => {});
    await pause(page, dwell * 1.4);
  },
  "/learn/data-visualization": async (page, dwell) => {
    for (const tab of ["Modules", "Certificates", "About"]) {
      await page.getByRole("tab", { name: tab }).click().catch(() => {});
      await pause(page, dwell * 0.5);
    }
  },
};

async function tour(page, dwell) {
  for (const path of PAGES) {
    await page.goto(BASE + path, { waitUntil: "networkidle", timeout: 120000 }).catch(() => {});
    await pause(page, dwell);
    await INTERACT[path]?.(page, dwell);
    // Slow scroll to show the whole page, then back up.
    const h = await page.evaluate(() => document.documentElement.scrollHeight - innerHeight);
    for (let y = 0; y < h; y += 300) { await page.mouse.wheel(0, 300); await pause(page, dwell / 4); }
    if (h > 0) { await page.evaluate(() => scrollTo({ top: 0, behavior: "smooth" })); await pause(page, 600); }
  }
}

const browser = await chromium.launch();

// Warm-up: let the dev server compile every route before the camera rolls.
{
  const ctx = await browser.newContext({ viewport: SIZE });
  const page = await ctx.newPage();
  await page.goto(BASE); await login(page); await tour(page, 0);
  await ctx.close();
}

mkdirSync(OUT, { recursive: true });
const ctx = await browser.newContext({ viewport: SIZE, recordVideo: { dir: OUT, size: SIZE } });
const page = await ctx.newPage();
await login(page, true);
await tour(page, 2500);
const video = page.video();
await ctx.close();
await browser.close();
const out = `${OUT}/nexus-demo.webm`;
renameSync(await video.path(), out);
console.log("saved", out);
