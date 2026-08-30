# 01. Risk framework

> Rules as they existed in 2025

## Limits in force

| Limit | 2025 value | Hard or soft | Held? |
|---|---|---|---|
| Risk per trade | 1% to 2% of total capital, ramped from $1 | Hard | Yes. Median 1.21%, max 1.89%, no trade above 2% |
| Max concurrent risk | 5R | Soft | Yes. Five positions were open at once exactly three times, all on 2025-11-11; the usual state is one or two |
| Max single-name exposure | Same as concurrent risk, the book is almost all BTC | Soft | Yes, by the same measure |
| Share of total capital on venue | no more than 30% | Soft | Yes |
| Leverage cap | none. Risk is controlled by position size and stop, not by leverage | n/a | n/a |
| Daily stop | **none** | | This was the gap |
| Weekly stop | **none** | | This was the gap |
| No-trade conditions | **none** | | This was the gap |

The three limits that were missing are the three that would have mattered most in
November and December. See `04`.

## Leverage, stated plainly

Every fill in the export shows cross margin at 101x or 125x. That is a margin
setting, not a risk setting. Position size came from stop distance, and the
leverage number only controls how much collateral the venue reserves.

Leverage is a tool for capital efficiency. It lets me hold no more than 30% of my
total capital on the exchange, which matters because exchanges get hacked and blow
up, as FTX did, so holding money on one is itself a risk. Stop distance and
expected loss are always within 1% to 2% of total capital, so the exposure is
managed regardless of the leverage figure.

Put concretely, a 1R trade at 1.2% of a 15,000 book risks about 180 USD. With a
median stop of 0.47% that is roughly 31,000 USDT of notional, which needs margin
that a 30%-funded exchange balance can only post with leverage. The leverage
figure is a consequence of keeping most of the capital off the venue.

## Sizing history

The year opened at **$1 of risk per trade** and reached full size over
eight months:

```
2.2 -> 3.5 -> 4 -> 5.7 -> 8 -> 10 -> 15 -> 20 -> 40 -> 50 -> 75
    -> 80 -> 105 -> 150 -> 175 -> 200 -> 225 -> 275 -> 300
```

Nineteen steps between 2025-03-09 and 2025-11-04. The smallest risk actually
traded was $1.20. **No step exceeds a doubling**.

Sizing up from the lowest risk possible $1 to target risk 1-2% helps manage
emotions, and it tests your discipline and commitment to the trading. You find
out whether you care about the money (the outcome) more than about systematic
improvement (the process).

The framework I settled on was to have at least one winning and one losing trade
at each risk level, with a reasonable gap between levels. Jumping from $1 to $2 is
small in absolute terms but relatively it is 2x, and doubling risk is not
something you can keep doing at higher figures. Going from $75 to $105 is only
marginally bigger in absolute terms, but you also cross from double digits into
triple digits and the brain reads that as a big change, so I put **$80** in
between. In relative terms the change is small.

The ramp cost nothing to run: **81 trades, +4.40R, +998 USD** across March to May.
It was a live test conducted at a size where being wrong was affordable.

## Concentration

- 196 long closes against 195 short: balanced by count
- Not balanced by money: **shorts +10,985 USDT, longs -3,413 USDT**
- Essentially one instrument

I trade systems, and they have a similar long/short ratio. Shorts paid off more
over this period because BTC momentum and trend were to the downside. That is the
performance I would expect in those conditions, and the mirror image, longs paying
more than shorts, is what I would expect in bullish ones.

That expectation is a claim, it is untested here, and testing it is
one of the things the next live year is for.

## What was missing

Calendar risk limits, 2R a day, 5R a week, 10R a month, were not in force in 2025.

I was familiar with these limits and I chose to ignore them, which was a mistake
born of ignorance. I had backtested results for each strategy, and each strategy
performed worse with calendar risk limits applied, so I decided not to use them
because it looked like a negative expectancy rule.

But I was very wrong. I treated backtest results as a source of truth and
certainty, which is not what they are for markets. Calendar risk limits exist for
the uncertainty part of market behaviour and system returns, which is precisely
the part a backtest cannot show you.

That is why I introduced and tested such rules, under uncertainty, for my 2026
strategy book.
