# Internship Finder

**Real internship offers from European tech companies, ranked for *your* profile, with an explanation for every score.**

🔗 **Live app: [internship-finder-black-five.vercel.app](https://internship-finder-black-five.vercel.app)** · Built by [Titouan](https://github.com/puccioT), a business-school student (EM Lyon) looking for his own Product internship.

---

## The problem

Finding a good internship abroad means checking dozens of career pages, reading postings in three languages,
and guessing whether you're a fit. Generic job boards are noisy, and most "AI job matchers" give a score with no reasoning.

I built this tool for my own search (Berlin, Amsterdam, Munich, Dublin, London, Zurich), then opened it to other students.

## What it does

- **Collects real offers every day** from ~140 companies' public career pages (startups like Doctolib, Celonis, GetYourGuide, Upvest; large groups like Philips, Visa, Salesforce, Deutsche Bank).
- **Reads each posting with AI** (role type, required skills, languages, start date, duration, remote policy, summary).
- **Ranks offers for your profile** with a transparent score out of 100: 50 points for the role fit, 50 for the share of required skills you cover.
- **Filters what doesn't fit**: country, contract type, start date, and offers requiring a language you don't speak (with a clear note on what was hidden, never silently).
- **Shows the gap**: which skills you cover (and through which related skill), which ones to learn, and the skills most requested across your target roles.
- **Drafts a LinkedIn message** to reach someone on the team, based only on skills you actually have.
- **Tracks your applications** (to apply → applied → interview → closed), with follow-up reminders.

## How it works

```
Career pages (8 platforms)  →  collect.py   →  SQLite  →  extract.py (Gemini)  →  export.py  →  offers.json  →  Next.js app
Greenhouse, Lever, Ashby,      intern filter,   upsert,     structured fiche        skill normalisation,         scoring runs
Workday, SmartRecruiters…      dedup            history     once per offer          start-date parsing           in the browser
```

| Layer | Choice | Why |
|---|---|---|
| Collection | Public JSON APIs of each applicant-tracking system (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Personio, Recruitee, Workday) | Real, current offers with direct links; no scraping of HTML pages |
| AI extraction | Gemini (structured JSON output, temperature 0), with a fallback model | Postings are unstructured and multilingual; extraction runs **once** per offer at collection time, not on every visit |
| Data cleaning | Deterministic Python after the AI (skill aliases, start-date parser, country filter) | LLM output is messy ("G-Sheets" vs "Google Sheets"); fixing it in code is testable and free |
| Matching | Rule-based score in JavaScript | Explainable and instant; the AI explains, it doesn't decide |
| App | Next.js, plain CSS, profile stored in `localStorage` | No account needed, nothing personal stored on a server |
| AI message | Server route with cache, per-user and global daily limits, template fallback | Keeps the API key private and the running cost at zero |

## Product decisions I'd defend

1. **Real data over a nice demo.** The first prototype ran on generated offers. It looked good and was useless, so I rebuilt it on real postings.
2. **Explainable score, AI where it adds value.** A black-box "87% match" doesn't help you decide. The score is computed; AI is used to read messy postings and to write a message.
3. **Transparency over magic.** Hidden offers are always counted and can be shown; AI summaries are labelled as such.
4. **Coverage gaps are fixed with data, not guesses.** Startups-only coverage missed the big employers of interns, so I added a Workday connector for large groups.
5. **Zero running cost.** Free tiers only, with guardrails so a traffic spike degrades to a template instead of a bill.

## Run it locally

```bash
# Data pipeline (Python 3.11+)
python -m venv venv && venv\Scripts\activate      # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
echo GEMINI_API_KEY=your_key > .env              # free key from Google AI Studio
python -m src.sources.probe_ats                  # detect which platform each company uses
python -m src.collect                            # fetch internships
python -m src.extract                            # AI reading of new offers
python -m src.export                             # write web/public/data/offers.json

# Web app (Node 20+)
cd web
npm install
echo GEMINI_API_KEY=your_key > .env.local        # only needed for the LinkedIn message
npm run dev                                      # http://localhost:3000
```

## Roadmap

- [x] Real offers from 8 platforms, daily refresh
- [x] AI extraction, skill normalisation, explainable matching
- [x] Onboarding, language and start-date filters, application tracker, AI LinkedIn message
- [x] Public launch with a nightly refresh (GitHub Actions → Vercel)
- [ ] Analytics and user tests
- [ ] Measure AI extraction quality on 50 hand-labelled offers
- [ ] More sources (Teamtailor, Welcome to the Jungle) and a weekly email digest

## Limitations

Coverage depends on the company list: some employers (Zalando, Booking.com, Klarna…) use platforms not yet supported.
AI summaries can be wrong. Always read the original posting.

---

*Offers belong to their publishers; this project only links to them.*
