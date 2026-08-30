# Live trading review, 2025

*Proven live trading results for 2025 from a retail trader. Outperformed the
market with +40% net returns. Breaking down the results, the process, and the
ways to improve.*

---

## Headline

Two records, two windows. The manual log covers the whole book. The venue export
covers the part where the money was large enough to be worth verifying.

| | Documented book | Venue-verified |
|---|---|---|
| Window (UTC) | 2025-03-09 to 2025-12-30 | 2025-06-02 to 2025-12-30 |
| Source | manual trade log | KCEX export |
| Trades | **382** | 391 closing fills |
| Result | **+24.71R** | **+5,993 USDT net, +40.0%** |
| Benchmark, same window | | BTC **-16%** |
| Max drawdown | | **-29.0%** of peak equity (2025-08-06) |
| Max drawdown, USDT | | -6,231 (2025-11-04 to 2025-12-22, not recovered in window) |
| Win rate | 23.0% | 30.7% |
| Payoff, avg win / avg loss | 3.64 | 2.69 |
| Profit factor | | 1.19 |
| Fees as share of gross profit | | 3.3% |

The two windows differ because I started on a different venue and at a size too
small to matter. The first three months are the sizing ramp, from $1 of risk per
trade up to full size. They are part of the process,
see [Risk](#risk).

The win rate and payoff differ between the two columns because they count
different things. The log counts a trade; the venue counts a closing fill, and
one trade can close in several fills.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/equity_curve-dark.png">
  <img alt="Live book vs BTC buy-and-hold, indexed to 100" src="figures/equity_curve.png">
</picture>

---

## Read this before the equity curve

```
2025-10-10          +6,182 USDT   = 103% of the venue window's net
top 3 days                        = 212% of net
Aug +19.1R and Oct +36.6R         = 225% of the year's +24.71R
```

Excluding 2025-10-10, the book is net negative over the venue window. Excluding
August and October, the documented book is -31R.

The whole book has a 23% win rate with a 3.64 payoff, which I define as convex.
Convex books are supposed to earn in the tail, and this is the intended shape of
my edge.

Two things follow from that, and they cut in opposite directions. The first is
that concentration is the expected result of the design. The second is that it makes the sample much
smaller than 382 trades suggests. The number that matters is how many tail events I traded through, and over ten months that is three (with one trade missed in Jun 2025, on paper it should have been 30R+ winner).

So for me to call this edge repeatable I need more live trades over a 6 to 12
month period, to see the shape of the tail and the cumulative performance. If it
persists as positive with most of the payoff arriving at volatile events, the
edge is repeatable.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/r_distribution-dark.png">
  <img alt="Outcome per trade in R" src="figures/r_distribution.png">
</picture>

The spike at -1R is the stop doing its job. Everything right of +2R is the part
of the distribution the book actually lives on.

---

## How to read the numbers

- **1R** is the unit of risk per trade: the USD amount lost if the stop is hit,
  which is the stop distance times position size. Sized at 1% to 2% of total
  capital. Median across 2025 was 1.21%; the largest single trade was 1.89%.
- **Starting capital** 15,000 USD.
- **Compounding** size is recomputed on a 10% equity change or more.
- **Net** is after all fees, entry and exit. Funding is included.
- **Benchmark** BTC. Binance BTCUSDT spot daily closes, **-16%** over
  2025-06-02 to 2025-12-30, and **-3.83%** over calendar 2025.
- Everything is UTC. The venue export is not; see `docs/00`.

Full definitions: **[docs/00-scope-and-definitions.md](docs/00-scope-and-definitions.md)**

---

## Risk

Risk per trade is 1% to 2% of total capital, and I hold no more than 30% of that
capital on the exchange at any time.

Say risk per trade is 1%. That is 1R for this trade. I long or short the exact
calculated amount of BTC, so when the stop is hit I lose no more than the
predefined 1R plus or minus 10% deviation, so ideally no more than 1.1R. It does
not matter whether I take 1 BTC at 10x or at 100x, the position size and the risk
are the same.

Every fill shows cross margin at 101x or 125x. That is a margin setting, not a
risk setting. Leverage is a tool for capital efficiency, it is what lets me keep
70% of my capital off an exchange that could be hacked or could collapse the way
FTX did, while still taking the position size my stop distance calls for.

The year opened at $1 of risk per trade and reached full size over three
months, moving up only after at least one winner and one loser at the previous
size. The ladder was 1.2, 2, 4, 8, 10, 20, 40, 50, 75, 105, 150, 175, 225, 275.
Fourteen steps, none of them larger than a doubling.

Full framework: **[docs/01-risk-framework.md](docs/01-risk-framework.md)**

---

## Book construction

The book is 18 backtested, objectively defined strategies. Almost all trades are
BTC. All of them are price-action based, across different timeframes and styles,
from mean reverting to trend following, from intraday to multi-day positions.

The rules are objective and the strategies were executed manually, but most of
them could be automated.

By trade count the book is balanced, 196 long closes against 195 short. By money
it is not: over the venue window, **shorts made +10,985 USDT and longs lost
-3,413**. The systems have a similar long/short ratio, so this is the market and
not the design. BTC trended down over the window and the short side is where the
momentum was. In the opposite regime I would expect the mirror image, and that
expectation is exactly what the next live year tests.

---

## Drawdown and monthly

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/underwater-dark.png">
  <img alt="Drawdown from running peak" src="figures/underwater.png">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/monthly_r-dark.png">
  <img alt="Monthly result in R across the documented book" src="figures/monthly_r.png">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/monthly_net-dark.png">
  <img alt="Monthly return, book vs BTC" src="figures/monthly_net.png">
</picture>

Two of ten months carry the book. I saw the biggest performance in volatile
periods like October, which supports the fact that the edge in my systems is
mostly momentum based.

Equity curve volatility is slightly elevated for my liking, but it is a good
start.

---

## Costs

| | |
|---|---|
| Gross realized | +7,571.70 USDT |
| Fees, both legs | -1,578.36 USDT |
| Fees / gross profit | **3.3%** |
| Maker share of fills | 30% |

The maker/taker split is deliberate: some strategies and entries require limit
fills. Funding is included in the net figure.

**[docs/03-costs-and-execution.md](docs/03-costs-and-execution.md)**

---

## What I would and would not do again

**Still would:**

1. **Size up gradually, and only after a loss and a winner at the current size.**
   $1 to $2 to $4, never $1 to $10 to $100. Even when it looks like a small
   increase, only $1 or $3, it is relatively a big jump: a 2x increase.
2. **Trade one fixed window and be fully present in it.** Crypto trades 24/7 and
   I cannot. For me it was the NY session, 9:30am to 4:00pm ET.
3. **Research, backtest, review and journal outside the trading window.**

**Would not:**

1. **Let new strategies enter the book at full risk.** They should have been
   scaled separately, the way I scaled myself. Sleeve G ran 49 trades for
   **-18.30R** against a book total of +24.71R.
2. **Keep a sleeve that was already losing.** That same sleeve was -6.65R after
   its first 24 trades and lost a further -11.65R over its next 25. The
   information to cut it existed halfway through, and no rule forced the
   decision.
3. **Run without calendar risk limits.** November and December together: 104
   trades, **-20.91R**, at full size throughout. More trades in two losing months
   than in October, my best month.

**[docs/04-failures-and-changes.md](docs/04-failures-and-changes.md)**

---

## Capacity

The strategies are scalable. Capital up to $1m would not hurt execution.
Somewhere past that, changes are required.

At 15,000 of capital, 1R is about 180 USD and a median position is **31,000 USDT
of notional**, with the largest at 208,000. The ratio is set by stop distance:
the median stop is **0.47% of entry price**, so every 1 USD of risk buys roughly
**204 USDT of notional**, and a wide-stop trade buys less.

Scaling that ratio:

| Capital | 1R | Median notional | Largest position |
|---|---|---|---|
| 15,000 | 180 | 31,000 | 208,000 |
| 1,000,000 | 12,000 | ~2.1m | ~14m |
| 10,000,000 | 120,000 | ~21m | ~139m |

**What binds first is the stop.** BTC perpetual books
absorb a few million without much trouble, so depth is not the constraint at $1m.
The constraint is that a 0.47% stop leaves very little room, round-trip taker
cost is already about 12bp against a 47bp stop, roughly a quarter of 1R before slippage. Add a few basis points of impact from a larger clip and the cost
share climbs fast. At $10m the median clip is ~21m and the largest ~139m, which
cannot go as one order at all, and the slippage on working it would consume a
meaningful fraction of the risk unit.

There is a second constraint, KCEX has
the lowest fees I have found and no execution API. Any size worth calling capacity
has to move to a tier-1 venue, which raises fees, and higher fees hurt most on
exactly the tightest-stop strategies.

---

## What this is not

- Not a backtest. Every fill is money that moved.
- Not a strategy description. No entry or exit rules, parameters or filters.
- Not advice, not a signal service, not a fund.

2025 is the first year I properly logged my trades and process, which is why it
is the year that gets documented. The trading journey either side of it:

- **2021-2023** learning, but inconsistent trading, gambling basically.
- **2024** learning, researching and backtesting, while holding BTC and paper trading like a professional.
- **2025** +24.71R, +40%, max drawdown -29.0%.
- **2026** ongoing.

**[docs/05-what-this-is-not.md](docs/05-what-this-is-not.md)**

---

## Reproducibility

Public in this repo: **aggregate statistics and the code that computes them**. The
per-trade blotter is not published, because timestamps, sizes and hold times may be
enough to reconstruct a rule.

Full blotter available on request during an interview.

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -q                       # 19 tests, fakes only, no network
python3 scripts/make_sample.py                    # regenerate the synthetic sample
python3 scripts/verify_published_numbers.py       # re-derive every figure on this page
```

`verify_published_numbers.py` recomputes each headline number from source and
fails if the prose has drifted from the data. It also refuses to pass if a
strategy name leaks into a public file. It needs the private sources to run, so
it is a pre-publish check rather than something a reader can execute.

`src/` runs against `data/sample_synthetic.csv`, which is generated and carries
no real trade. `data/public_monthly_stats.csv` is aggregated from the real book.

### Notes on the data

- **The venue export carries no timezone.** Two exports of this account are
  shifted 3h against each other. Both were resolved against BTCUSDT 1-minute
  candles (`scripts/verify_timezone.py`), and after normalising to UTC they agree
  on **390 of 390** overlapping fills.
- **The manual log had a date defect.** The spreadsheet silently converted only
  the ambiguous dates, those where both parts are 12 or lower, into real dates
  under a DD/MM reading, and left the rest as MM/DD text. 55 entry and 107 exit
  dates had day and month transposed. It surfaced as 44 rows whose exit preceded
  their entry. `src/blotter.py` repairs it from cell storage type and
  `validate()` checks the repair rather than assuming it.
- **Round-trip reconstruction does not work on this data.** Residual positions
  never return to flat, so the unit is the closing fill, which carries the
  venue's own realized PnL.

---

## Future work

Identify and clear the sub-optimal strategies and trades, reduce the drawdown,
and push yearly returns toward 50-100% CAGR.

The measurable next step is narrower than that: run the 2026 book with calendar
risk limits in force, 2R a day, 5R a week, 10R a month, and with every new sleeve
scaled from small size separately rather than entering at full risk. The test is
whether the deepest drawdown comes in under 20% of peak equity without the
expectancy in R going negative.
