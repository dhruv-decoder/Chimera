---
title: Agentic commerce fraud surface (2026)
tags: [agentic, carding, agent-pay, intelligent-commerce, delegated-token]
sources:
  - https://www.ravelin.com/blog/the-agentic-commerce-gold-rush-risk
  - https://www.americanbanker.com/payments/news/as-agentic-commerce-grows-risks-abound
  - https://unit42.paloaltonetworks.com/retail-fraud-agentic-ai/
  - https://www.ldotr.red/post/ai-agent-commerce-fraud
---

By 2026 autonomous shopping agents transact on users' behalf through delegated
credentials (Mastercard Agent Pay agentic tokens; Visa Intelligent Commerce with
Anthropic, OpenAI, Microsoft, Perplexity). MRC's 2026 report found ~63% of
merchants exploring or planning agentic payments. The attack surface is new:

- Delegated tokens carry no cardholder step-up, so a compromised or malicious
  agent can transact without friction.
- Agents run at machine speed and scale, so carding and rapid-purchase abuse
  complete before human-tuned velocity rules react. HUMAN Security documented AI
  agents autonomously testing stolen cards against live checkouts.
- Bot-vs-human liability is unclear; a consumer using an agent can still dispute
  under Regulation E.
- Visa's risk team logged a 450%+ rise in dark-web posts mentioning "AI Agent"
  in H1 2026.

Detection leans on: agent channel + agentic-token entry mode, headless runtime,
sub-second-to-few-second session timing, atypical purchase cadence, and many
SKUs in a short window. The hard part is separating malicious agents from the
large and growing volume of legitimate agentic shopping.

## Delegated-token / agent-identity abuse (the harder half)

Carding velocity is the loud version. The quieter, harder version is abuse of a
*legitimately delegated* credential. Both card networks now bind agent identity
into the payment: Mastercard Agent Pay issues an Agentic Token (via the Mastercard
Digital Enablement Service) that binds three identities into one credential - the
cardholder, the registered AI agent, and the scope of the mandate; Visa's Trusted
Agent Protocol (TAP, launched with Cloudflare in Oct 2025) signs the agent's
identity into request headers, which merchants verify against Visa's directory.

That binding is exactly what an attacker attacks. Credential theft, prompt
injection of a shopping agent, or a rogue agent SDK lets an attacker spend inside
someone else's mandate. The acquirer's problem, stated plainly by Visa's own
threat team: how do you tell a legitimately delegated agent from a scripted
attacker reusing a stolen token? Velocity, device and cadence do not answer it -
a real trusted agent is also fast, automated, and serves many principals. The
answer is credential integrity: a missing or replayed network attestation, low
agent-directory trust, spend over the delegated per-transaction cap, an off-scope
high-risk merchant, and one agent id draining many mandates at once. Visa also
reports a 25% rise in malicious bot-initiated transactions over six months (40%
in the US), so this surface is scaling with adoption.
