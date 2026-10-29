---
version: alpha
colors:
  ink: "#1b2823"
  primary: "#193b30"
  primaryDeep: "#122d24"
  primarySoft: "#dce8dd"
  canvas: "#f2f3ed"
  paper: "#fffefa"
  accent: "#e76e43"
  muted: "#74817a"
  line: "#dce1d8"
typography:
  sans:
    fontFamily: "DM Sans, Segoe UI, sans-serif"
  display:
    fontFamily: "Space Grotesk, DM Sans, sans-serif"
  mono:
    fontFamily: "DM Mono, Consolas, monospace"
rounded:
  small: "6px"
  medium: "8px"
scrollbars:
  thumb: "#aeb9ae"
  track: "#f2f3ed"
  hover: "#7e8e81"
  active: "#193b30"
spacing:
  sidebar: "250px"
omitted:
  - section: components
    reason: "Component token values remain in the existing application stylesheet; no separate component library is configured."
---

## Overview

Rallydesk is a product interface for table tennis club organisers. Keep it composed like a well-run club desk: calm, tactile, legible, and efficient during play. It is a product surface, not a marketing landing page. The signature is the deep pine navigation paired with a small warm-orange scoring accent.

The current runtime stylesheet is the token source of truth. `:root` variables in `src/styles.css` map the palette, type roles, sidebar width, and global scrollbar colors into the interface. This document records the intended values; update both documentation and stylesheet when the visual system deliberately changes.

## Colors

Use pine for structure and primary actions, warm chalk for the page canvas, paper for working surfaces, and orange sparingly for focus, live play, and key emphasis. Green/red/yellow communicate semantic outcomes and must not be the only status cue. Keep text contrast strong and avoid decorative gradients.

## Typography

Use Space Grotesk for product names and short display headings, DM Sans for controls and reading, and DM Mono for compact operational metadata. Keep body text comfortably readable; small uppercase mono labels are secondary context, never the only instruction.

## Layout

Use a persistent 250px sidebar on desktop and the existing overlay navigation on narrow screens. Main content uses a centered, fluid working area with clear page toolbar, action hierarchy, and natural document scrolling. Tables may scroll horizontally on small screens when comparisons need column alignment.

## Elevation & Depth

Prefer borders, subtle surface changes, and the pine sidebar over floating-card stacks. Use elevation only when it explains layering, such as a menu, dialog, or sticky top bar.

## Shapes

Use compact 6–8px radii for controls and cards. Reserve fully rounded shapes for status dots, avatars, and small count badges.

## Scrollbars

Keep scrollbars visible and operable. Use a thin, global warm-gray thumb with a chalk track, a darker hover state, and pine active state; preserve native high-contrast colors in forced-colors mode.

## Components

Shared runtime styles in `src/styles.css` are canonical. Preserve common button, field, dialog, toast, footer, card, and navigation treatment across screens. Icons use lucide-react. Keep decorative mark construction simple and consistent with the brand lockup.

## Do's and Don'ts

- Do keep the initial club, player, match, and tournament data empty; users create their own records.
- Do label local-only behavior honestly until Firebase is integrated.
- Do make create, score, correction, pause, and export actions easy to find during an event.
- Don't add fabricated names, club branding, data, or claims of cloud security.
- Don't use generic gradient hero art, gratuitous motion, or decorative dashboard filler.
