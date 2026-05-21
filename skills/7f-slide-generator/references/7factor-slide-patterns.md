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
- Centered card, ~70% slide width
- Background: navy, text white
- Optional pull-quote orange mark (a stylized "7") at upper-left of card
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

## When patterns conflict

Prefer this priority: **brand tokens > pattern layout > visual-explainer defaults**.

If a needed layout isn't here, use visual-explainer's mechanics but keep 7Factor colors, typography, and logo placement.
