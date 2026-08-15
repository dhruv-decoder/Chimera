"""Payment-fraud technique matrix - an ATT&CK-style taxonomy for the GenAI era.

Structure mirrors MITRE ATT&CK: a small set of *tactics* (the adversary's
goal at each stage of the payment-fraud kill chain) crossed with concrete
*techniques*. Each technique records the rails/channels it touches, the
observable signatures a defender can look for, and public 2026 references.

`simulated=True` means a faithful generator exists in ``chimera.generate.attacks``
and the technique produces labelled events end-to-end. The remainder are mapped
for breadth (the Identify pillar rewards exhaustive coverage) and are the queue
the ideation agent draws from when proposing new simulated variants.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# --- tactics (kill-chain stages) ----------------------------------------
TACTICS: dict[str, str] = {
    "recon": "Reconnaissance - select victims, harvest data, profile targets.",
    "access": "Access - obtain credentials, identities, or authorisation.",
    "setup": "Infrastructure - stand up mules, synthetic accounts, devices, kits.",
    "execution": "Execution - initiate the fraudulent payment(s).",
    "cashout": "Cash-out & layering - extract and launder proceeds.",
    "evasion": "Evasion - defeat controls, models, and monitoring.",
}


@dataclass
class Technique:
    id: str
    name: str
    tactic: str
    rails: List[str]
    channels: List[str]
    genai_role: str                 # how generative AI amplifies this technique
    summary: str
    kill_chain: List[str]
    signatures: List[str]           # observable signals a detector can exploit
    references: List[str]
    simulated: bool = False
    severity: int = 3               # 1..5 expected financial impact


TECHNIQUES: List[Technique] = [
    Technique(
        id="SYN-ID",
        name="GenAI synthetic identity fabrication",
        tactic="setup",
        rails=["card_cnp", "a2a_rt"],
        channels=["web", "mobile_app"],
        genai_role="LLMs stitch real + fabricated PII into coherent, document-consistent "
                   "identities; generative image models forge supporting documents.",
        summary="Fraudsters fabricate net-new identities from a blend of stolen and "
                "synthetic PII, nurture them with thin-file activity, then bust out.",
        kill_chain=["fabricate PII", "open low-KYC account", "age/nurture", "obtain credit", "bust-out"],
        signatures=["thin credit file", "sudden credit-line utilisation", "clustered device/IP reuse",
                    "young account + high amount-to-balance ratio"],
        references=["https://withpersona.com/blog/7-ways-synthetic-identity-fraud-is-changing-in-2026",
                    "https://www.pwc.com/cz/cs/blog/rizeni-rizik/the-fraud-trend-to-watch-in-2026-and-beyond.html"],
        simulated=True, severity=5,
    ),
    Technique(
        id="DF-KYC",
        name="Deepfake KYC / liveness bypass",
        tactic="access",
        rails=["card_cnp", "a2a_rt"],
        channels=["mobile_app", "web"],
        genai_role="Face-swap and generative video defeat selfie/liveness checks; "
                   "injected camera streams replay synthetic faces.",
        summary="Onboarding biometric checks are bypassed with generated faces, enabling "
                "account opening or takeover at scale.",
        kill_chain=["acquire target PII", "generate liveness video", "inject camera stream", "pass KYC"],
        signatures=["emulator/headless device", "camera injection markers", "impossible liveness timing",
                    "reused biometric hash across identities"],
        references=["https://www.getrealsecurity.com/resources/synthetic-identity-fraud-deepfakes-2026-deepfake-summit",
                    "https://sumsub.com/blog/fraud-trends/"],
        simulated=False, severity=4,
    ),
    Technique(
        id="DF-APP",
        name="Deepfake-authorised push payment (APP) scam",
        tactic="execution",
        rails=["a2a_rt"],
        channels=["mobile_app", "web"],
        genai_role="Real-time voice/video cloning impersonates family, executives, or bank "
                   "staff to socially engineer a victim into authorising a push transfer.",
        summary="The victim themselves authorises a real-time transfer to the fraudster after "
                "a cloned-voice/video pretext - defeating auth because it is genuine.",
        kill_chain=["profile victim", "clone voice/video", "pretext call", "induce authorised push", "mule receives"],
        signatures=["first-time payee", "voice-auth channel", "amount spike vs history",
                    "session urgency (short deliberation)", "new-beneficiary + high amount"],
        references=["https://thepaypers.com/fraud-and-fincrime/expert-views/2026-fraud-forecast-ai-deepfakes-and-rising-cybercrime-risks",
                    "https://scamwatchhq.com/india-scams-2026-digital-arrest-upi-fraud-epidemic/"],
        simulated=True, severity=5,
    ),
    Technique(
        id="MULE-NET",
        name="Money-mule network orchestration",
        tactic="cashout",
        rails=["a2a_rt"],
        channels=["mobile_app", "web"],
        genai_role="LLM agents recruit mules, script laundering flows, and adapt fan-in/"
                   "fan-out patterns to stay under structuring thresholds.",
        summary="Proceeds are layered through networks of mule accounts using fan-in "
                "collection and fan-out dispersion, often within minutes on instant rails.",
        kill_chain=["recruit mules", "fan-in collection", "rapid layering", "fan-out dispersion", "off-ramp"],
        signatures=["high in/out degree", "short dwell time of funds", "cyclic flows",
                    "new accounts with immediate high throughput", "community structure"],
        references=["https://the420.in/india-mule-accounts-upi-fraud-march-2026-report/",
                    "https://www.newsx.com/business/worried-about-upi-fraud-by-scamsters-heres-how-npci-will-use-ai-to-take-on-cheats-242854/"],
        simulated=True, severity=5,
    ),
    Technique(
        id="CARD-TEST",
        name="Automated card testing / BIN attack",
        tactic="execution",
        rails=["card_cnp"],
        channels=["web", "agent"],
        genai_role="Agents generate and validate card permutations against low-friction "
                   "endpoints, then triage live cards for resale or cash-out.",
        summary="Bursts of low-value authorisations validate stolen or enumerated card "
                "numbers before they are used for higher-value fraud.",
        kill_chain=["acquire BIN ranges", "enumerate PANs", "micro-auth probing", "triage live cards"],
        signatures=["micro-amount bursts", "high decline ratio", "many cards / one device or IP",
                    "sequential BIN patterns", "velocity spike"],
        references=["https://unit42.paloaltonetworks.com/retail-fraud-agentic-ai/",
                    "https://wyllo.ai/the-2026-ecommerce-fraud-trends-guide-threats-and-how-to-mitigate-them/"],
        simulated=True, severity=4,
    ),
    Technique(
        id="AGENT-CARD",
        name="Agentic-commerce carding (autonomous checkout abuse)",
        tactic="execution",
        rails=["card_cnp"],
        channels=["agent"],
        genai_role="Autonomous shopping agents run carding and rapid-purchase campaigns at "
                   "machine speed against live checkouts using delegated tokens.",
        summary="AI agents exploit Agent Pay / Intelligent Commerce delegated credentials to "
                "test cards and place rapid purchases, blurring bot-vs-human liability.",
        kill_chain=["obtain agentic token", "enumerate SKUs/checkouts", "rapid autonomous purchase", "resale"],
        signatures=["agent channel + agentic_token", "machine-speed session timing",
                    "headless device", "atypical purchase cadence", "many SKUs / short window"],
        references=["https://www.ravelin.com/blog/the-agentic-commerce-gold-rush-risk",
                    "https://www.americanbanker.com/payments/news/as-agentic-commerce-grows-risks-abound",
                    "https://www.ldotr.red/post/ai-agent-commerce-fraud"],
        simulated=True, severity=4,
    ),
    Technique(
        id="AGENT-HIJACK",
        name="Delegated-token / agent-identity abuse",
        tactic="execution",
        rails=["card_cnp"],
        channels=["agent"],
        genai_role="A hijacked or malicious AI shopping agent - taken over via prompt "
                   "injection, token theft, or a rogue agent SDK - spends inside a "
                   "cardholder's delegated mandate without their intent.",
        summary="Under Agent Pay (Agentic Token) and Visa's Trusted Agent Protocol a purchase "
                "can be initiated by a delegated agent credential. Stolen or replayed, that "
                "credential lets an attacker spend within someone else's mandate - looking "
                "identical to a legitimate agent on velocity, device and cadence.",
        kill_chain=["compromise agent or steal delegated token", "replay across principals",
                    "spend off-mandate at resellable merchants", "cash-out"],
        signatures=["missing / replayed network attestation", "low agent-directory trust",
                    "amount over the delegated cap", "off-scope high-risk merchant",
                    "one agent id draining many mandates"],
        references=["https://corporate.visa.com/en/sites/visa-perspectives/security-trust/the-threats-landscape-of-agentic-commerce.html",
                    "https://www.trustsphere.ai/post/agentic-checkout-arrives-why-agent-present-card-payments-break-the-assumptions-fraud-systems-were",
                    "https://www.digitalapplied.com/blog/agent-checkout-authentication-card-networks-2026"],
        simulated=True, severity=5,
    ),
    Technique(
        id="ATO-STUFF",
        name="AI-orchestrated account takeover (credential stuffing)",
        tactic="access",
        rails=["card_cnp", "a2a_rt"],
        channels=["web", "mobile_app"],
        genai_role="Agents solve challenges, rotate proxies, and personalise flows to take "
                   "over accounts, then drain via card or push payment.",
        summary="Compromised credentials are validated and monetised through the victim's own "
                "account, inheriting its trust and history.",
        kill_chain=["acquire creds", "distributed login", "session hijack", "payee/limit change", "drain"],
        signatures=["new device on aged account", "geo/ASN anomaly", "beneficiary/limit change then payout",
                    "impossible travel"],
        references=["https://sumsub.com/blog/fraud-trends/"],
        simulated=True, severity=4,
    ),
    Technique(
        id="PIG-BUTCH",
        name="Real-time investment ('pig-butchering') scam",
        tactic="execution",
        rails=["a2a_rt"],
        channels=["mobile_app", "web"],
        genai_role="LLM chat personas run long-con relationships and fabricate trading "
                   "dashboards to induce escalating authorised transfers.",
        summary="Victims are groomed over weeks then make escalating authorised transfers to "
                "attacker-controlled accounts believing they are investing.",
        kill_chain=["contact victim", "build rapport", "fake returns", "escalate deposits", "vanish"],
        signatures=["escalating transfer sizes to same new payee", "crypto/high-risk off-ramp",
                    "round-number ladder", "no prior payee relationship"],
        references=["https://scamwatchhq.com/india-scams-2026-digital-arrest-upi-fraud-epidemic/"],
        simulated=True, severity=5,
    ),
    Technique(
        id="QR-SWAP",
        name="UPI collect-request / QR manipulation",
        tactic="execution",
        rails=["a2a_rt"],
        channels=["mobile_app"],
        genai_role="Generative content produces convincing merchant/refund pretexts that turn "
                   "collect-requests (pull) into victim-approved debits.",
        summary="Victims approve a 'collect' or scan a swapped QR believing they are receiving "
                "money, and instead authorise an outbound debit.",
        kill_chain=["craft refund pretext", "send collect-request", "victim approves", "debit"],
        signatures=["collect-request approval to new VPA", "refund pretext + outbound flow",
                    "small-then-large pattern"],
        references=["https://www.fraudintel.in/blog/upi-fraud-detection-api-india"],
        simulated=False, severity=3,
    ),
    Technique(
        id="PROMPT-INJ",
        name="Prompt injection of payment assistants",
        tactic="execution",
        rails=["card_cnp", "a2a_rt"],
        channels=["agent", "web"],
        genai_role="Malicious content in product pages, emails, or chat hijacks an LLM banking/"
                   "shopping assistant into redirecting or authorising payments.",
        summary="Indirect prompt injection manipulates an AI assistant with payment authority "
                "into sending funds to or approving an attacker.",
        kill_chain=["plant injected content", "victim agent ingests it", "agent redirects payment", "cash-out"],
        signatures=["agent channel", "payee mismatch vs user intent", "instruction-like payload in context",
                    "anomalous agent-initiated beneficiary"],
        references=["https://www.hoganlovells.com/en/publications/agentic-payments-and-the-new-fraud-landscape-for-retailers"],
        simulated=False, severity=4,
    ),
    Technique(
        id="FAAS",
        name="Fraud-as-a-Service kit deployment",
        tactic="setup",
        rails=["card_cnp", "a2a_rt"],
        channels=["web", "mobile_app", "agent"],
        genai_role="Subscription kits bundle phishing, deepfakes, and automation so low-skill "
                   "actors run enterprise-grade campaigns.",
        summary="Commoditised toolkits lower the barrier to entry, producing correlated, "
                "templated fraud across many accounts.",
        kill_chain=["subscribe to kit", "deploy templated infra", "run campaign", "share proceeds"],
        signatures=["templated device/UA fingerprints", "shared infrastructure across campaigns",
                    "correlated timing across accounts"],
        references=["https://sumsub.com/blog/fraud-trends/"],
        simulated=False, severity=3,
    ),
    Technique(
        id="BUST-OUT",
        name="First-party / friendly-fraud bust-out",
        tactic="cashout",
        rails=["card_cnp"],
        channels=["web", "mobile_app"],
        genai_role="LLMs draft convincing dispute narratives and coordinate synthetic first-"
                   "party fraud at scale.",
        summary="An account builds good standing, maxes available credit rapidly, then defaults "
                "or disputes legitimate spend.",
        kill_chain=["build standing", "raise limits", "max utilisation", "default/dispute"],
        signatures=["sudden utilisation jump", "spend pattern break", "dispute burst after payout"],
        references=["https://withpersona.com/blog/7-ways-synthetic-identity-fraud-is-changing-in-2026"],
        simulated=False, severity=3,
    ),
    Technique(
        id="SIM-SWAP",
        name="SIM-swap / OTP interception",
        tactic="access",
        rails=["card_cnp", "a2a_rt"],
        channels=["mobile_app", "web"],
        genai_role="AI-crafted social engineering of carriers and victims accelerates SIM-swaps "
                   "that intercept OTP-based step-up.",
        summary="Control of the victim's number defeats SMS OTP, enabling takeover and "
                "high-value authorised transactions.",
        kill_chain=["social-engineer carrier", "port number", "intercept OTP", "authorise payment"],
        signatures=["SIM-change flag then payout", "device change + OTP success", "auth via OTP soon after port"],
        references=["https://sumsub.com/blog/fraud-trends/"],
        simulated=False, severity=4,
    ),
    Technique(
        id="ADV-EVADE",
        name="Adversarial evasion of ML controls",
        tactic="evasion",
        rails=["card_cnp", "a2a_rt"],
        channels=["web", "mobile_app", "agent"],
        genai_role="Agents probe the model as a black box and shape transactions (amount, "
                   "timing, payee mix) to slip below the decision boundary.",
        summary="Fraud is tuned against the live detector - low-and-slow amounts, humanised "
                "timing, laundering through aged accounts - to minimise model score.",
        kill_chain=["probe detector", "estimate boundary", "shape features", "execute below threshold"],
        signatures=["amounts just under thresholds", "humanised cadence", "score clustering near boundary"],
        references=["https://www.nature.com/articles/s41598-025-27010-z"],
        # Realised by the adversarial evasion engine (chimera.generate.adversarial),
        # which is applied on top of every standalone attack rather than being a
        # standalone generator of its own.
        simulated=False, severity=4,
    ),
    Technique(
        id="STRUCT",
        name="Structuring / velocity threshold evasion",
        tactic="evasion",
        rails=["a2a_rt", "card_cnp"],
        channels=["mobile_app", "web"],
        genai_role="Optimises transfer sizing and spacing to stay below reporting and velocity "
                   "limits across many accounts.",
        summary="Large sums are split into many sub-threshold transfers across accounts and time "
                "to avoid triggering rules.",
        kill_chain=["compute thresholds", "split amounts", "spread across accounts/time", "reaggregate"],
        signatures=["amounts clustered just below round thresholds", "even spacing", "fan across payees"],
        references=["https://www.fraudintel.in/blog/upi-fraud-detection-api-india"],
        simulated=True, severity=3,
    ),
]


def techniques_by_tactic() -> dict[str, List[Technique]]:
    out: dict[str, List[Technique]] = {t: [] for t in TACTICS}
    for tech in TECHNIQUES:
        out.setdefault(tech.tactic, []).append(tech)
    return out


def simulated_technique_ids() -> List[str]:
    return [t.id for t in TECHNIQUES if t.simulated]


def get_technique(tech_id: str) -> Technique | None:
    return next((t for t in TECHNIQUES if t.id == tech_id), None)
