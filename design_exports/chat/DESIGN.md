---
name: Editorial Collective
colors:
  surface: '#f8f9fa'
  surface-dim: '#d9dadb'
  surface-bright: '#f8f9fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f5'
  surface-container: '#edeeef'
  surface-container-high: '#e7e8e9'
  surface-container-highest: '#e1e3e4'
  on-surface: '#191c1d'
  on-surface-variant: '#444748'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f2'
  outline: '#747878'
  outline-variant: '#c4c7c7'
  surface-tint: '#5f5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1c1b1b'
  on-primary-container: '#858383'
  inverse-primary: '#c8c6c5'
  secondary: '#4b41e1'
  on-secondary: '#ffffff'
  secondary-container: '#645efb'
  on-secondary-container: '#fffbff'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#151c27'
  on-tertiary-container: '#7d8492'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e5e2e1'
  primary-fixed-dim: '#c8c6c5'
  on-primary-fixed: '#1c1b1b'
  on-primary-fixed-variant: '#474746'
  secondary-fixed: '#e2dfff'
  secondary-fixed-dim: '#c3c0ff'
  on-secondary-fixed: '#0f0069'
  on-secondary-fixed-variant: '#3323cc'
  tertiary-fixed: '#dce2f3'
  tertiary-fixed-dim: '#c0c7d6'
  on-tertiary-fixed: '#151c27'
  on-tertiary-fixed-variant: '#404754'
  background: '#f8f9fa'
  on-background: '#191c1d'
  surface-variant: '#e1e3e4'
typography:
  display-lg:
    fontFamily: Source Serif 4
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Source Serif 4
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  article-body:
    fontFamily: Source Serif 4
    fontSize: 20px
    fontWeight: '400'
    lineHeight: 32px
  article-body-mobile:
    fontFamily: Source Serif 4
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  interface-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
  interface-sm:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  container-max: 1120px
  article-max: 680px
  gutter: 24px
  margin-mobile: 16px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
  stack-xl: 64px
---

## Brand & Style
The design system is anchored in a content-first, editorial philosophy designed for high-intellect discourse. The aesthetic balances the precision of modern SaaS with the timelessness of a prestige periodical. By prioritizing whitespace and extreme typographic clarity, the interface recedes to let the author's voice take center stage.

The style is **Minimalist with Editorial influence**. It avoids trendy ornamentation in favor of structural integrity, utilizing thin strokes, a disciplined grid, and a sophisticated interplay between functional sans-serifs and literary serifs. The emotional response is one of calm, focus, and professional reliability.

## Colors
The palette is intentionally restrained to maintain an "ink-on-paper" feel. 
- **Backgrounds:** The main page uses a soft neutral (`#F8F9FA`) to reduce eye strain, while content cards and article containers use pure white (`#FFFFFF`) to pop forward.
- **Typography:** Primary headers and body text use a deep charcoal (`#1A1A1A`) rather than pure black for a more premium, softer contrast. Secondary metadata and labels use a muted gray (`#6B7280`).
- **Accents:** A sophisticated indigo (`#4F46E5`) is used sparingly for primary actions, text links, and active states.
- **Borders:** A thin, light gray (`#E5E7EB`) defines structure without adding visual noise.

## Typography
This design system employs a dual-typeface strategy. 
- **Editorial Layer:** `Source Serif 4` is used for all long-form content, article headlines, and blockquotes. It provides the authoritative, literary feel required for publishing. For article body text, a generous `1.6x` line height is mandated for optimal readability.
- **Interface Layer:** `Geist` handles the functional aspects of the platform—navigation, buttons, input fields, and metadata. Its technical precision contrasts beautifully with the organic serif.
- **Hierarchy:** Use `label-caps` for overlines or category tags to create clear distinction from the main headlines.

## Layout & Spacing
The layout follows a **Fixed Grid** philosophy for desktop to ensure line lengths remain readable. 
- **Article Views:** Content is constrained to a `680px` central column to prevent horizontal eye fatigue.
- **Discovery/Feed Views:** Uses a 12-column grid with a `1120px` max-width.
- **Vertical Rhythm:** Spacing follows a strict 8px base unit. Use `stack-xl` (64px) between major sections and `stack-md` (16px) between related interface elements.
- **Mobile:** Margins shrink to `16px`, and typography scales down according to the defined mobile tokens to maintain vertical density.

## Elevation & Depth
Elevation is communicated through **Tonal Layering** and **Thin Outlines** rather than traditional shadows.
- **Level 0 (Base):** Page background (`#F8F9FA`).
- **Level 1 (Surface):** Cards, article containers, and menus sit on white (`#FFFFFF`) with a `1px` solid border (`#E5E7EB`).
- **Level 2 (Overlay):** Dropdowns and modals use a slightly thicker `1px` border in a darker neutral or a very soft, diffused ambient shadow (0px 4px 20px rgba(0,0,0,0.04)) to indicate interactivity.
- **Interaction:** Hover states on interactive cards should result in a subtle background shift to `#F3F4F6` or a border color change to the primary accent, rather than a "lift" effect.

## Shapes
The shape language is structured and architectural. 
- **Containers:** Content cards and main UI containers use a **Soft** radius (`8px`).
- **Small Elements:** Buttons and input fields follow the same `8px` radius to maintain a consistent silhouette.
- **Avoidance:** Pill-shapes and fully circular buttons are avoided (except for user avatars) to preserve the sophisticated, editorial tone.

## Components
- **Buttons:** Primary buttons are solid `#1A1A1A` with white `Geist` text. Secondary buttons use a `1px` border with no fill. Padding is typically `10px 20px`.
- **Input Fields:** Minimalist design with a `1px` border. On focus, the border transitions to the Indigo accent. Labels always use `interface-sm` above the field.
- **Article Cards:** Features a `label-caps` category, a `Source Serif 4` headline, and a short `Geist` metadata row (author, date, read time).
- **Lists:** Clean, undivided lists for navigation; horizontal dividers (`1px` `#E5E7EB`) are used only for separating distinct content pieces in a feed.
- **Chips/Tags:** Rectangular with `4px` radius, using a light gray fill (`#F3F4F6`) and `interface-sm` text. No borders.
- **Icons:** Use 20px or 24px light-weight (2pt stroke) outline icons to match the thin-line aesthetic of the borders and typography.