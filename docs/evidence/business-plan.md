# The business plan (cfo.ai)

The owner made this plan in cfo.ai on 11 October 2026 from the measured cost of the final run and a list of assumptions.
It is shared read-only here: https://app.cfo.ai/s/aRFg86F21pDO1EQN

Everything under "What the plan says" is copied from that page as it read on 11 October 2026 at 22:45 UTC. Three
screenshots of it are in [business-plan/](business-plan/). The business is hypothetical: nobody has paid, and the page
says so.

## What went in

Measured, from `runs/20261011-161207/summary.json`:
- 8 county files, 192 scanned pages, 3,061 published rows; 353 model calls, $2.35 of model cost, 20.5 minutes.
- 7 files could be checked. 215 disagreements in 4 of them: 185 proven by printed totals, 30 left as published.
- Model cost per file: $0.10 to $0.79.

Assumed by us, none of it tested:
- A person needs 1 minute to confirm one proven finding, at $30 an hour.
- Three prices to compare: $15 a file; $300 a month for up to 50 files; $1,500 once for up to 200 files.
- $200 a month of fixed cost; $5,000 of opening cash; an unpaid founder for six months.
- 2 paying customers in month 3, then 2 more each month, half on the subscription and half on the one-off offer.

Added by the plan, and stated on the page: every allowance is used in full; Crossfoot pays outside reviewers for all 185
proven findings under every offer; payment is immediate; no subscription is cancelled; nobody buys twice. Taxes, payment
fees, sales effort, refunds and engineering time are left out, so the cash figures are on the kind side.

## What the plan says

Cost per file: $0.29 of model calls ($2.35 over 8 files) and $13.21 for a person (185 proven findings over 7 files is
26.43 a file, at one minute each). $13.51 in all.

| | $1,500 once, 200 files | $15 a file | $300 a month, 50 files |
|---|---|---|---|
| Revenue per file | $7.50 | $15.00 | $6.00 |
| Model cost per file | $0.294 | $0.294 | $0.294 |
| Confirmation cost per file | $13.214 | $13.214 | $13.214 |
| Gross profit per file | -$6.008 | $1.492 | -$7.508 |
| Gross margin | -80.1% | 9.9% | -125.1% |

Cash at each month's end, for the assumed sales, half of them and double (the page holds all 12 months):

| | Oct 2026 | Nov | Dec | Jan 2027 | Feb | Mar | Apr |
|---|---|---|---|---|---|---|---|
| Assumed sales | $4,800 | $4,600 | $2,823 | $671 | -$1,857 | -$4,760 | -$8,039 |
| Half | $4,800 | $4,600 | $3,611 | $2,435 | $1,071 | -$480 | -$2,220 |
| Double | $4,800 | $4,600 | $1,246 | -$2,859 | -$7,714 | -$13,321 | -$19,678 |

- Cash first goes below zero in month 5 with the assumed sales, month 6 with half, month 4 with double. Runway is about
  4.3, 5.7 and 3.3 months. More sales shorten it, because two of the offers lose money on every file.
- No case breaks even on a month's operations within 12 months. Cash at month 12: -$30,063, -$13,732, -$62,726.
- The plan's advice: sell proof, not cheap model calls. Pilot $15 a file as self-service, where the customer does the
  confirming, and quote managed review separately.

## The three numbers the plan says to measure next

1. **How much of an allowance is used.** The plan assumes all of it. At the assumed review effort, a year's operations
   break even at roughly 45 percent usage, which the plan calls "not a dependable business model".
2. **A person's time per file.** 26.43 minutes is an extrapolation from one run and a guessed minute per finding. To cover
   the variable cost at full usage the subscription needs about 26 seconds a finding and the one-off offer about 33.
3. **New paying customers.** Under these prices ten percent more customers makes month-12 cash $3,266 worse.

## What we take from it

- The model is not the cost. A person checking the findings costs about 45 times what the model does.
- Two of the three prices we thought of lose money on every file. We had not seen that before the plan was made.
- Nothing here is validated. The findings have not been confirmed by a person, so the minute per finding is a guess, and
  nobody has been asked to pay.
