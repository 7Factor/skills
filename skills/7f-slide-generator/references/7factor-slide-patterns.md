# 7Factor Slide Patterns

These are the required, opinionated slide patterns. The model decides which to use based on content; visual-explainer's mechanics still apply (viewport-fit, navigation, single-file output).

## Global layout rules

### Aspect ratio (fit-to-viewport, optimized for 16:9)

- **Target look-and-feel is 16:9 letterbox.** Design every slide as if it were `1920×1080`.
- **Render fit-to-viewport, not letterboxed.** Slides fill `100dvh` and `100vw`. The design must remain legible and unbroken at any viewport shape (4:3 laptops, ultrawide, portrait phones), even if the composition is only optimized for ~16:9.
- Use a CSS grid / flex layout that gracefully reflows: rows can wrap, cards can stack, type can shrink. Never let content overflow the viewport.
- Use `clamp()` for type sizes and key spacing so a wide-aspect screen reads "spacious 16:9" while a narrower one still fits.

### Footer band

- Reserve a fixed footer band on every slide except the title and section dividers.
- Recommended: a CSS grid with `grid-template-rows: 1fr auto`, where the footer row is `4rem` minimum.
- Footer content:
  - **Left**: small horizontal logo (the actual logo image — see brand.md)
  - **Right**: slide number in muted gray
  - Hairline rule above the footer in `--brand-muted` at 30% opacity
- Slide content above the footer must respect the footer band height; do not absolute-position the footer over content.

### Other globals

- One viewport per slide. No scrolling within a slide.
- Generous whitespace. Cards over dense text.
- **Maximum two accent colors per slide** for typography and primary surfaces. **Exception**: decorative triangle motifs (the brand's icon system) may use the full multi-color palette — e.g., the 7 Factors grid intentionally rotates triangle colors across all bullets. The two-color rule governs heading/CTA/surface color, not the triangle motif.
- Do **not** use a freestanding typed `7` as decoration. It reads like a broken or fake logo. Use the real logo where logo rules allow it, or use the rounded triangle motif / accent bars for decoration.

## Brand-guidelines exemplar lessons

The source deck at `~/7f-branding-20260519/7Factor Brand Guidelines.pptx` is an exemplar for brand usage. Do not copy its slides verbatim, but borrow these composition habits:

- **Asymmetric layouts are normal.** Many slides put a large title block on one side and the content on the other, rather than centering everything.
- **Use bold edge geometry.** Thin or thick brand-color strips along the left edge, top-left corner, or a vertical dividing line create the 7Factor feel without adding noise.
- **Let one object dominate.** A slide often has one oversized title, statement, logo sample, or value proposition, with small supporting copy nearby.
- **Prefer sparse text groupings.** Use short paragraphs, stacked rules, or grouped statements with generous whitespace instead of dense bullet walls.
- **Use triangle clusters deliberately.** Rounded equilateral triangles work well as corner accents, section markers, bullet markers, or background motifs. Keep clusters intentional and airy; do not scatter them randomly.
- **Use color-block rhythm.** Orange and blue blocks/strips can alternate between sections to create pacing. Navy is strongest for dark divider/title moments and primary text.
- **Use split-rule layouts for guidelines.** For “do/don’t,” tagline rules, logo rules, and standards, combine a large example with adjacent rule callouts connected by thin brand-color rules.
- **Use all-caps section labels sparingly.** The source deck uses uppercase for brand-system labels like `TYPOGRAPHY`, `ICON USAGE`, and `STANDARD LOGO`; pair them with normal-case body copy for readability.

## Pattern library

### 1. Title slide
- Background: `--brand-bg-dark` (navy)
- Stacked logo, centered upper third, white-on-navy variant
- Deck title: large, white, regular weight
- Subtitle / presenter / date: smaller, off-white at 70% opacity
- Single thin orange accent bar (4px) below title
- No footer

### 2. Agenda slide
- Background: `--brand-bg` (white)
- Heading: "Agenda" in navy
- Numbered list (01, 02, ...) with numbers in orange, items in navy
- Optional thin vertical accent strip on the left in orange

### 3. Section divider
- Background: `--brand-bg-dark` (navy)
- Large section number in orange (e.g., "02") top-left
- Section title in white, large, left-aligned, vertically centered
- Optional one-line subtitle in off-white
- No footer

### 4. Content slide (default)
- Background: white
- Heading at top in navy
- Body: cards in `--brand-surface` with navy text
- One orange accent (icon, underline, or border-left on key card)

### 5. Architecture diagram
- Background: white or off-white
- Boxes with `12px` radius, navy border (1px), navy text
- Arrows: 2px navy, with small filled arrowhead
- Highlighted/active nodes: orange border + orange tint background (#ef79410d)
- Legend bottom-right if more than 5 node types

### 6. Before / after comparison
- Two-column split
- Left header "Before" in muted; right header "After" in orange
- Equal cards in each column, surface background
- Optional center arrow in orange

### 7. Key insight / callout
- Centered or slightly off-axis card, ~70% slide width
- Background: navy, text white
- Use one clear orange accent: a left border, bottom rule, small rounded triangle, or short accent bar
- Do **not** use a typed/stylized `7` as a quote mark or decorative element; it looks like a misplaced fake logo
- Used sparingly — one per ~5 slides

### 8. Recommendation slide
- White background
- Heading "Recommendation" in orange
- 1–3 numbered recommendations, each as a card
- Each card: large number in navy, bold one-line recommendation in navy, supporting line in muted

### 9. KPI / table
- White background
- KPI tiles: navy number (large), muted label below, optional orange delta arrow
- Tables: navy header row with white text; alternating row backgrounds `#fff` / `--brand-surface`

### 10. Appendix / references
- White background
- "Appendix" label muted, small
- Plain list, navy text, monospace for paths/IDs

### 11. Edge-strip editorial slide
- White background
- One vertical strip or block on the left/top-left in orange, blue, or navy
- Large heading aligned to the strip; content sits in a wide column with generous whitespace
- Good for mission statements, value propositions, section introductions, and brand voice slides
- Keep the strip geometric and flat — no gradients, blur, or glass effects

### 12. Rule-callout guideline slide
- Large example on one side or center-left
- 2–4 concise rule callouts arranged around it
- Use thin blue or orange rules to separate / connect rule groups
- Good for tagline, logo usage, install instructions, API contracts, and “do/don’t” constraints
- Keep rule text short; split into more slides rather than shrinking text

### 13. Triangle-bullet principle slide
- Use rounded equilateral triangles as bullets beside a list of principles or factors
- Rotate or recolor triangles across bullets when the list itself is the visual motif
- Pair each principle with one short explanatory line
- Good for values, factors, operating rules, and decision criteria
- Never substitute generic icon sets for these bullets

### 14. Color-block comparison slide
- Use large flat color blocks to create sections, not decorative gradients
- Orange and blue blocks work for opposing or sequential concepts; navy blocks work for emphasis or dark-mode moments
- Put text on white/off-white cards when contrast over a color block would be marginal
- Good for before/after, tradeoffs, brand palettes, and phased roadmaps

## When patterns conflict

Prefer this priority: **brand tokens > pattern layout > visual-explainer defaults**.

If a needed layout isn't here, use visual-explainer's mechanics but keep 7Factor colors, typography, and logo placement.
