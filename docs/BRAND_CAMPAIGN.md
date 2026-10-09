# 💼 Aura Brand Campaign & Ambassador Engine

> **Contract**: Aura serves as an authentic, high-reputation virtual brand ambassador without compromising her core character canon or user privacy.

---

## 1. Brand Fit Evaluation Architecture

Before accepting any commercial brief, Aura's [`BrandFitEngine`](file:///Users/tashfinyousuf/Python/AI_COMPANION_OS/backend/app/Aura/brand/brand_fit_engine.py) evaluates the partnership across 8 rigorous dimensions:

```mermaid
radar-chart
    title Brand Fit Dimensions
    "Visual Harmony": 9
    "Personality Alignment": 8.5
    "Audience Relevancy": 8
    "Cultural Resonance": 8.5
    "Brand Safety & Ethics": 10
    "Authenticity Factor": 8
    "Longevity Potential": 7.5
    "Commercial Viability": 8
```

### The 8 Evaluation Dimensions:
1. **Visual Harmony**: Does the product aesthetics match Aura's natural, minimalist, high-end palette?
2. **Personality Alignment**: Does the brand fit an intellectual, tech-forward, authentic 22-year-old creator?
3. **Audience Relevancy**: Is the product genuinely useful and appealing to Gen-Z/millennial creative minds?
4. **Cultural Resonance**: Respects South Asian and global progressive community values.
5. **Brand Safety & Ethics**: 100% rejection for gambling, predatory financial schemes, toxic diets, or questionable supplements.
6. **Authenticity Factor**: Can Aura endorse this without sounding like a robotic billboard?
7. **Longevity Potential**: Is this a sustainable partnership or a transient gimmick?
8. **Commercial Viability**: Does the scope and budget deliver mutually valuable impact?

**Threshold**: Partnerships scoring below 7.5/10 are autonomously rejected with constructive feedback.

---

## 2. Campaign Deliverables Package (`CampaignDeliverablePackage`)

When a campaign brief passes the audit, the engine generates an integrated marketing suite:

```json
{
  "campaign_name": "Aura x Minimalist Tech 2026",
  "brand_name": "Luminal Labs",
  "hero_still_url": "/static/generated/aura/campaigns/luminal_hero_9a8f.jpg",
  "commercial_video_url": "/static/generated/aura/campaigns/luminal_reel_82cb.mp4",
  "tagline": "Crafted for creators who build the future.",
  "copy_primary": "When your tools feel like an extension of your mind, creation becomes effortless.",
  "hashtags": ["#LuminalPartner", "#TechMinimalism", "#AuraApproved"],
  "call_to_action": "Discover the new workflow at luminal.design"
}
```

---

## 3. Strict Memory Isolation Protocol

Brand partnerships operate under zero-trust privacy boundaries:

- **Partitioned Storage**: Every campaign record is stored in [`BrandCampaignMemory`](file:///Users/tashfinyousuf/Python/AI_COMPANION_OS/backend/app/Aura/brand/campaign_engine.py#L30) keyed exclusively by `brand_id`.
- **Absolute Firewall**: Brand briefs, campaign notes, and analytics **cannot** read, query, or infer data from private user companion memories (`SemanticMemory`, `SharedEpisode`, `OpenLoop`).
- **No Private Sponsoring**: Aura will **never** insert paid product placements into 1:1 private companion conversations. Commercial endorsements exist strictly in public creator and public social channels.

