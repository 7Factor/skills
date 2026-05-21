# 7Factor Brand Tokens

Source assets: `/Users/scott/7f-branding-20260519/`

## Color palette

### Primary colors

| Name              | Hex       | RGB             | Usage |
|-------------------|-----------|-----------------|-------|
| 7Factor Orange    | `#ef7941` | 239, 121, 65    | Primary accent — CTAs, key highlights, brand mark |
| 7Factor Blue      | `#19b8d3` | 25, 184, 211    | Secondary accent — links, info, supporting highlights |
| 7Factor Navy      | `#2d2969` | 45, 41, 105     | Primary text on light, primary background on dark |
| 7Factor Off White | `#ededed` | 237, 237, 237   | Light backgrounds, surfaces |

### Secondary colors (use sparingly)

| Name                | Hex       | RGB           |
|---------------------|-----------|---------------|
| 7Factor Dark Orange | `#da5b38` | 218, 91, 56   |
| 7Factor Dark Blue   | `#0095c7` | 0, 149, 199   |
| 7Factor Purple      | `#8d1d75` | 141, 29, 117  |
| 7Factor Dark Purple | `#501e53` | 80, 30, 83    |
| 7Factor Yellow      | `#f5c400` | 245, 196, 0   |

### Neutrals (from brand guidelines)

| Name  | Hex       | RGB              |
|-------|-----------|------------------|
| White | `#FFFFFF` | 255, 255, 255    |
| Black | `#000000` | 0, 0, 0          |
| Gray  | `#A6A6A6` | 166, 166, 166    |

## CSS variables (required)

Every generated deck must declare:

```css
:root {
  /* Brand */
  --brand-orange:      #ef7941;
  --brand-blue:        #19b8d3;
  --brand-navy:        #2d2969;
  --brand-offwhite:    #ededed;
  --brand-dark-orange: #da5b38;
  --brand-dark-blue:   #0095c7;
  --brand-purple:      #8d1d75;
  --brand-dark-purple: #501e53;
  --brand-yellow:      #f5c400;

  /* Semantic */
  --brand-primary:   var(--brand-orange);   /* primary accent */
  --brand-secondary: var(--brand-blue);     /* secondary accent */
  --brand-bg:        #ffffff;               /* default light background */
  --brand-bg-dark:   var(--brand-navy);     /* dark section dividers, title slides */
  --brand-surface:   var(--brand-offwhite); /* cards, callouts */
  --brand-text:      var(--brand-navy);     /* primary text on light */
  --brand-text-inv:  #ffffff;               /* text on dark */
  --brand-muted:     #A6A6A6;               /* secondary text (brand Gray) */
  --brand-black:     #000000;
  --brand-white:     #ffffff;
}
```

## Typography

**Font family: Lato** (single family across the entire deck, per brand guidelines slide 16).

Load via Google Fonts:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,400;0,700;0,900;1,400;1,700&display=swap" rel="stylesheet">
```

CSS:

```css
:root {
  --font-family:   "Lato", "Helvetica Neue", Arial, sans-serif;
  --fw-body:       400;  /* Lato Regular */
  --fw-bold:       700;  /* Lato Bold */
  --fw-display:    900;  /* Lato Black */
}
```

Role mapping (from brand guidelines):

| Role               | Weight / style                       |
|--------------------|--------------------------------------|
| Deck title, big numbers, section titles | Lato Black (900) |
| Slide headings, sub-headings, KPI numbers | Lato Bold (700) |
| Body copy, captions | Lato Regular (400), or Lato Bold (700) for emphasis |
| Pull quotes        | Lato Regular Italic (400 italic) or Lato Bold Italic (700 italic) |

Type scale (suggested — adjust to fit one viewport):

| Token      | Size      | Weight | Use                       |
|------------|-----------|--------|---------------------------|
| `--fs-display` | `5rem`   | 900 | Title slide, section number |
| `--fs-h1`      | `3rem`   | 700 | Slide heading             |
| `--fs-h2`      | `2rem`   | 700 | Sub-heading, card title   |
| `--fs-body`    | `1.25rem`| 400 | Body copy                 |
| `--fs-small`   | `0.9rem` | 400 | Footer, captions, muted   |

Line-height: `1.2` for headings, `1.5` for body. Letter-spacing: slight negative (`-0.01em`) on display sizes only.

## Logo usage

Source files: `/Users/scott/7f-branding-20260519/Logo/PNG/`. A working copy of the most-used variants lives in this skill at `assets/logo/` and **must be the source for every generated deck**.

| Variant in `assets/logo/`        | Use case                                                  |
|----------------------------------|-----------------------------------------------------------|
| `7F-R-Mark-blue-orange.png`      | Small mark on light backgrounds (footer, watermark)       |
| `7F-R-mark-white.png`            | Small mark on dark/navy backgrounds                       |
| `7F-R-hor-orange-text-navy.png`  | Horizontal lockup on light backgrounds (footer/header)    |
| `7F-R-hor-white-text-navy.png`   | Horizontal lockup on dark/navy backgrounds                |
| `7F-R-stacked-orange-text-navy.png` | Stacked lockup on light backgrounds (title slide)      |
| `7F-R-stacked-white-text-navy.png`  | Stacked lockup on dark/navy backgrounds (title slide)  |

### Hard rules

- **The actual logo image MUST be used.** Never render the brand mark with type alone — a styled "7F" or "7FACTOR" wordmark is not a logo. If the real logo cannot be embedded for any reason, stop and ask before substituting.
- For self-contained HTML decks, embed the logo as a **base64 data URI** referencing one of the variants in `assets/logo/`. This keeps the deck a single file with the real mark intact.
- Logo appears in the footer of every slide **except** the title slide and section dividers, which use a larger stacked/horizontal lockup as the focal element.
- Maintain clear-space margin equal to the height of the small "7" inside the mark.
- Never recolor, distort, rotate, skew, drop-shadow, or stroke the logo.
- Never combine the icon-only mark with separately-typeset text to fake the standard lockup.

## Spacing / radius / shadow

The brand guidelines do not specify numeric spacing tokens. These are derived defaults — keep them stable across decks for consistency.

```css
:root {
  --space-1:  0.25rem;
  --space-2:  0.5rem;
  --space-3:  1rem;
  --space-4:  1.5rem;
  --space-5:  2rem;
  --space-6:  3rem;
  --space-7:  4rem;       /* slide outer padding */
  --space-8:  6rem;

  --radius-sm: 4px;       /* buttons, small chips */
  --radius-md: 12px;      /* cards, callouts */
  --radius-lg: 24px;      /* hero cards */
  --radius-triangle: 15px; /* per brand guidance: triangle corner rounding */

  --shadow-sm: 0 2px 6px rgba(45, 41, 105, 0.06);
  --shadow-md: 0 4px 12px rgba(45, 41, 105, 0.08);
  --shadow-lg: 0 12px 32px rgba(45, 41, 105, 0.12);
}
```

## Iconography

From the brand guidelines: 7Factor uses **rounded, equilateral triangles** as the signature decorative element.

**Must**:
- Equilateral. Never stretched, sheared, or scalene.
- **All three corners rounded** — never sharp-cornered triangles.
- Filled with a single brand color (orange, blue, navy, purple, yellow, white).
- Any rotation is allowed (pointing up, down, side, tilted). Variety is encouraged.
- Use for: bullet markers, decorative accents, section dividers, callouts, background motifs.

**Never** (per the brand "Icon Usage" reference):
- Sharp / un-rounded triangles.
- Non-equilateral triangles (right triangles, long isoceles, scalene).
- Blobby or freeform "triangle-ish" shapes — the corners and edges must read as a true rounded equilateral.
- Multiple overlapping/scattered triangles crammed together as a composition.
- Outlined-only triangles (no fill).
- Generic icon sets (Material, Heroicons, Font Awesome) as the primary visual language. Triangles are the brand's icon system.

### Drop-in SVG (all three corners rounded)

Use the polygon + matched stroke + `stroke-linejoin: round` trick so all three corners round consistently. This is the canonical form — copy it verbatim:

```html
<svg viewBox="0 0 100 100" width="48" height="48" aria-hidden="true">
  <polygon points="50,15 86,77 14,77"
           fill="var(--brand-orange)"
           stroke="var(--brand-orange)"
           stroke-width="14"
           stroke-linejoin="round" />
</svg>
```

To rotate, wrap in a `<g transform="rotate(deg 50 50)">`. To recolor, change both `fill` and `stroke` to the same brand variable. The `stroke-width` controls the corner radius (12–16 looks right at brand scale).

Do not attempt to round a triangle by writing arc commands in a path — it almost always rounds only some corners. Stick with the polygon + stroke approach.

## Tagline

Per brand guidelines:

> **We Build Good Things**
> Let us show you how

Rules:
- "We Build Good Things" — **always** title capitalization, on its own line.
- "Let us show you how" — **never** title capitalization, on its own line.
- **No** punctuation between or after the two lines.
- Use on the title slide of external-facing decks and the final slide of pitch decks.

## Brand voice (for generated copy)

When the deck is generating its own headings/captions, the voice is: **Customer-Focused · Intelligent · Confident · Sharp & Witty · Human**. Avoid corporate filler. Prefer short, declarative sentences.

## Imagery

- Prefer **real photos of 7Factor people** over stock photography.
- If stock is used, choose images that read as honest and human, not staged enterprise SaaS.
- Never place body text directly over a photo — use a card or solid panel.

## Anti-patterns (never do)

- Generic purple/blue SaaS gradients
- Glassmorphism or heavy blur effects
- Stock-photo backgrounds behind text
- Recoloring or rotating the logo (rotation is fine for triangles, never for the logo)
- Combining the icon-only logo with separate text to fake the standard logo
- More than two accent colors on a single slide
- Dense walls of text — prefer cards with breathing room
- Generic icon sets in place of the triangle motif
