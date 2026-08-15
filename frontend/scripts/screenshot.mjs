// Capture the landing story and each console view for visual QA and the submission.
// Requires the app running on :3000 and the API on :8000.
//   node scripts/screenshot.mjs
import { chromium } from "playwright";
import { mkdirSync } from "fs";

const OUT = new URL("../../docs/screenshots/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const VIEWS = [
  ["Overview", "overview"],
  ["Threat Matrix", "threats"],
  ["Attack Lab", "lab"],
  ["Closed Loop", "loop"],
  ["Network Graph", "graph"],
  ["Detection", "detect"],
  ["Validation", "evidence"],
];

const base = process.env.URL || "http://127.0.0.1:3000";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
page.on("pageerror", (e) => console.error("PAGE ERROR:", e.message));
console.log("loading", base);
await page.goto(base, { waitUntil: "networkidle" });
await page.waitForTimeout(1800);

// 1) Landing story - hero (viewport)
await page.screenshot({ path: `${OUT}story-hero.png` });
console.log("captured story-hero");

// 2) Scroll into the agentic-frontier section for a second story frame
await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight * 0.72, behavior: "instant" }));
await page.waitForTimeout(1200);
await page.screenshot({ path: `${OUT}story-agentic.png` });
console.log("captured story-agentic");

// 3) Enter the console
await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
await page.waitForTimeout(400);
await page.getByRole("button", { name: /Open the live console/i }).first().click();
await page.waitForTimeout(1500);

for (const [label, id] of VIEWS) {
  await page.locator("nav button", { hasText: label }).first().click();
  await page.waitForTimeout(1200);
  if (id === "lab") {
    await page.getByRole("button", { name: /Launch campaign/i }).click();
    await page.waitForSelector("text=detection recall", { timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(1500);
  }
  if (id === "graph") {
    await page.waitForSelector("svg circle", { timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(2000);
  }
  if (id === "loop") await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}${id}.png`, fullPage: true });
  console.log("captured", id);
}

await browser.close();
console.log("screenshots ->", OUT);
