// iPhone 16 screenshots (393x852 CSS px at 3x = 1179x2556) of the three differentiators:
// root-cause diagnosis, a verified AI-written MCQ with its source, and the before/after re-test.
// Usage: node scripts/shots-differentiators.mjs <outDir> <subjectId with practice questions>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const BASE = "http://localhost:3000";
const OUT = process.argv[2] || "shots";
const SUBJECT = process.argv[3] || "3";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 393, height: 852 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
const page = await ctx.newPage();
const settle = () => page.waitForTimeout(1600);                    // entrance animations
// Full-page shot: the fixed bottom bar would be stamped mid-page, so let it sit at the end of the page for that capture.
const full = async (path) => {
  const nav = page.locator('nav[aria-label="Mobile navigation"]');
  await nav.evaluate((n) => { n.style.position = "static"; });
  await page.screenshot({ path, fullPage: true });
  await nav.evaluate((n) => { n.style.position = ""; });
};

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[name="email"]', "demo@nexus.local");
await page.fill('input[name="password"]', "nexus-demo-2026");
await page.click('button[type="submit"]');
await page.waitForURL(/dashboard/);

for (const r of ["/diagnosis", "/diagnosis/retest"]) await page.goto(BASE + r, { waitUntil: "networkidle" });   // compile both first
await page.goto(`${BASE}/diagnosis`, { waitUntil: "networkidle" });
await page.getByText("Why the errors happened").waitFor();
await settle();
await page.screenshot({ path: `${OUT}/1-root-cause-diagnosis.png` });
await full(`${OUT}/1-root-cause-diagnosis-full.png`);

await page.goto(`${BASE}/subjects/${SUBJECT}/practice`, { waitUntil: "networkidle" });
const card = page.locator("li").filter({ hasText: "correlation coefficient" }).filter({ has: page.getByRole("radio") }).first();
await card.waitFor();
await card.getByRole("radio", { name: /-1 to \+1/ }).check();
await card.getByRole("button", { name: /Check answer/ }).click();
await card.getByText("independent check").waitFor();
await card.evaluate((e) => { const top = e.getBoundingClientRect().top + scrollY - 64; scrollTo({ top, behavior: "instant" }); });
await settle();
await page.screenshot({ path: `${OUT}/2-verified-mcq-with-source.png` });

await page.goto(`${BASE}/diagnosis/retest`, { waitUntil: "networkidle" });
await page.getByText("Effect on dependent topics").waitFor();
await settle();
await page.screenshot({ path: `${OUT}/3-retest-before-after.png` });
await full(`${OUT}/3-retest-before-after-full.png`);

await browser.close();
console.log("saved to", OUT);
