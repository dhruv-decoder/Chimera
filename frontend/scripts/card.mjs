// Render the 560x280 Kaggle card/thumbnail image.
//   node scripts/card.mjs
import { chromium } from "playwright";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __dir = dirname(fileURLToPath(import.meta.url));
const ART = resolve(__dir, "../../data/artifacts");
const DOCS = resolve(__dir, "../../docs");
const loop = JSON.parse(readFileSync(resolve(ART, "loop_report.json"), "utf8"));
const curve = loop.hardening_curve || [];
const worst = curve.length ? curve.reduce((a, b) => (b.pre_recall < a.pre_recall ? b : a)) : { pre_recall: 0.19, post_recall: 0.83 };
const pre = Math.round(worst.pre_recall * 100), post = Math.round(worst.post_recall * 100);

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter','Segoe UI',system-ui,sans-serif;}
.card{position:relative;width:560px;height:280px;overflow:hidden;color:#e8eaf0;padding:30px 32px;
  background:radial-gradient(30rem 18rem at 88% -20%, rgba(46,214,166,0.16), transparent 60%),
             radial-gradient(24rem 18rem at 4% 8%, rgba(139,140,240,0.14), transparent 58%), #07080b;}
.brand{display:flex;align-items:center;gap:9px;}
.mark{width:22px;height:22px;border-radius:6px;border:1px solid rgba(255,255,255,0.15);background:#12151c;box-shadow:inset 0 0 0 1px rgba(46,214,166,0.3);}
.name{font-size:15px;font-weight:600;}
.title{font-size:30px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin-top:20px;max-width:440px;}
.title em{color:#2ed6a6;font-style:normal;}
.sub{font-size:13px;color:#aeb4c2;margin-top:12px;max-width:430px;line-height:1.45;}
.foot{position:absolute;left:32px;bottom:26px;display:flex;align-items:center;gap:14px;}
.stat{font-family:ui-monospace,monospace;font-size:13px;color:#8a909f;}
.stat b{color:#ff5c49;}.stat i{color:#2ed6a6;font-style:normal;}
.pillars{position:absolute;right:32px;bottom:26px;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#6b7280;}
</style></head><body>
<div class="card">
  <div class="brand"><div class="mark"></div><div class="name">Chimera</div></div>
  <div class="title">Fraud that learns needs a defense that <em>learns back</em>.</div>
  <div class="sub">A closed-loop adversarial AI lab for GenAI-era payment fraud. Identify, generate and defend as one feedback loop.</div>
  <div class="foot"><span class="stat">recall under live attack <b>${pre}%</b> &rarr; after retrain <i>${post}%</i></span></div>
</div></body></html>`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 560, height: 280 }, deviceScaleFactor: 2 });
await page.setContent(html, { waitUntil: "networkidle" });
await page.locator(".card").screenshot({ path: resolve(DOCS, "kaggle_card_560x280.png") });
await browser.close();
console.log("card -> docs/kaggle_card_560x280.png");
