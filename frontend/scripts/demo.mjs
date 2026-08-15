// Record a ~60s screen video of the main attack -> defense flow.
//   node scripts/demo.mjs    (requires the app running on :8000)
// Output: docs/Chimera_Demo.webm  (upload to YouTube, or convert to mp4)
import { chromium } from "playwright";
import { renameSync, mkdirSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __dir = dirname(fileURLToPath(import.meta.url));
const DOCS = resolve(__dir, "../../docs");
const VID = resolve(DOCS, "_vid");
mkdirSync(VID, { recursive: true });
const base = process.env.URL || "http://127.0.0.1:8000";

const browser = await chromium.launch({ args: ["--force-device-scale-factor=1", "--hide-scrollbars"] });
const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
  recordVideo: { dir: VID, size: { width: 1920, height: 1080 } },
});
const page = await context.newPage();
const wait = (ms) => page.waitForTimeout(ms);
const scrollTo = (frac) => page.evaluate((f) => window.scrollTo({ top: document.body.scrollHeight * f, behavior: "smooth" }), frac);

// 1) Landing hero
await page.goto(base, { waitUntil: "networkidle" });
await wait(3000);

// 2) Scroll the story: problem, how it works, threats
for (const f of [0.08, 0.16, 0.24]) { await scrollTo(f); await wait(1600); }

// 3) The proof - scrub the hardening curve reveal
for (const f of [0.34, 0.40, 0.46, 0.52]) { await scrollTo(f); await wait(1700); }

// 4) Enter the live console
await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
await wait(600);
await page.getByRole("button", { name: /Open the live console/i }).first().click();
await wait(1800);

// 5) Attack Lab: launch the headline vector and read the live result
console.log("step: Attack Lab");
await page.locator("nav button", { hasText: "Attack Lab" }).first().click();
await wait(1200);
await page.locator("button", { hasText: "AGENT-HIJACK" }).first().click();
await wait(800);
await page.getByRole("button", { name: /Launch campaign/i }).click();
await page.waitForSelector("text=detection recall", { timeout: 30000 });
await wait(2500);
await page.screenshot({ path: "/tmp/verify_lab.png" });
console.log("  lab result rendered");
// open a flagged row to reveal reason codes
await page.locator("table tbody tr").first().click().catch(() => {});
await wait(2600);

// 6) Closed Loop: the multi-agent pipeline + hardening curve
console.log("step: Closed Loop");
await page.locator("nav button", { hasText: "Closed Loop" }).first().click();
await page.waitForSelector("text=Multi-agent orchestration", { timeout: 15000 });
await wait(2000);
await page.locator("button", { hasText: /show.*execution trace/i }).click().catch(() => {});
await wait(2000);
await page.screenshot({ path: "/tmp/verify_loop.png" });
console.log("  closed loop rendered");
await scrollTo(0.28); await wait(2200);

// 7) Detection: the leave-one-out novelty result
console.log("step: Detection");
await page.locator("nav button", { hasText: "Detection" }).first().click();
await page.waitForSelector("text=Detection & explainability", { timeout: 15000 });
await wait(1500);
await scrollTo(0.9); await wait(2600);
await page.screenshot({ path: "/tmp/verify_detect.png" });
console.log("  detection rendered");
await scrollTo(0); await wait(1200);

await context.close();
await browser.close();
const src = await page.video().path();
const out = resolve(DOCS, "Chimera_Demo.webm");
renameSync(src, out);
console.log("demo video -> docs/Chimera_Demo.webm");
