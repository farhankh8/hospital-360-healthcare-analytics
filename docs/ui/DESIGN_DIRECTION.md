# Design Direction — HOSPITAL 360 UI Redesign

## Character

**Calm, clinical, trustworthy, data-dense.**  
The interface should feel like a premium enterprise healthcare operations product: quiet confidence, precise numbers, clear hierarchy, and no decorative noise. It should help an executive scan, trust, and investigate.

## Visual principles

1. **Restraint over decoration** - navy/teal/neutral foundation; color carries meaning, not personality.
2. **Hierarchy first** - every page answers: what matters now, what changed, where to investigate.
3. **Data legibility** - tabular numerals, right-aligned numbers, consistent formatting, quiet charts.
4. **Calm density** - dense enough for analysts, breathable enough for executives.
5. **Trust signals** - visible data range/freshness, clear definitions, explicit benchmark/synthetic notices, no fake precision.

## Color meaning (limited, intentional)

- **Navy**: structure, navigation, primary text/brand anchors.
- **Teal**: interactive/focus/selected state and the single signature accent.
- **Green**: favourable change/status.
- **Red**: unfavourable change/status.
- **Amber**: warning/attention.
- **Grey/Slate**: neutral, secondary, disabled.
- **Blue/Info**: informational notices only.

Polarity is **reversed for lower-is-better metrics** (no-show, denial, LOS, waiting time, incidents, overtime, stockouts, etc.).

## Signature detail

**A thin teal status rail on KPI cards** (left edge, 2px) with subtle state coloring: teal for neutral/informational, green/red for favorable/unfavorable delta, amber for warning/snapshot attention. This gives the dashboard a recognizable clinical-instrument feel without adding decoration.

## Typography

- **Font:** Inter (loaded via `next/font`, self-hosted by Next build; no runtime external fetch).
- **Numeric style:** `tabular-nums` everywhere numbers appear.
- **Scale:** restrained - strong page titles, compact section labels, large KPI values, quiet captions.

## Layout & components

- Light neutral background, white cards, subtle borders, rounded corners (6/10/14 system).
- Two subtle shadow levels only.
- Charts use a shared ECharts theme driven by tokens (light/dark).
- Tables: clean, readable, 40px rows, density toggle, sticky header where appropriate.
- Motion: 150-200ms subtle transitions; respect `prefers-reduced-motion`.

## Dark mode

Supported via header toggle, persisted in `localStorage` with try/catch, defaulting to system preference on first load. All tokens/charts/components must remain readable and WCAG AA compliant.