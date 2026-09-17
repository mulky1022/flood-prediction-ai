---
name: Hydro-Climatic Intelligence
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#45464d'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#006398'
  on-secondary: '#ffffff'
  secondary-container: '#5bb8fe'
  on-secondary-container: '#00476e'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#001e2c'
  on-tertiary-container: '#008ebf'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#cce5ff'
  secondary-fixed-dim: '#93ccff'
  on-secondary-fixed: '#001d31'
  on-secondary-fixed-variant: '#004b73'
  tertiary-fixed: '#c4e7ff'
  tertiary-fixed-dim: '#7bd0ff'
  on-tertiary-fixed: '#001e2c'
  on-tertiary-fixed-variant: '#004c69'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-md:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.025em
  data-display:
    fontFamily: JetBrains Mono
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.02em
  data-metric:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
  data-timestamp:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-lg: 1.5rem
  margin: 1rem
  margin-md: 1.5rem
  margin-lg: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

The design system establishes a high-precision, scientifically grounded operational interface for real-time hydrometeorological monitoring and automated AI/ML flood risk forecasting. It is targeted at disaster management officials, municipal engineers, humanitarian response teams, and civil analysts operating in high-stakes environments where clarity under cognitive load is paramount.

The design movement combines **Data-Dense Modern Minimalist** structure with **Precision Telemetry UI**. Rather than evoking panic or sensory fatigue, the visual language is calm, authoritative, and analytical. High-contrast typographic hierarchy, strict tabular alignments, pristine surface delineation, and restrained chrome ensure that spatial map telemetry, sensor matrices, and predictive flood curves remain the focal point. Sensory alarms are replaced by clear, tier-based status indicators and unambiguous semantic alert levels.

## Colors

The foundation is built upon deep oceanic and atmospheric slate-blues balanced against clinical cool-gray canvases. Pristine white containers float on cool slate washes to present data layers without visual bleed.

### Canvas & Surface Architecture
- **App Canvas (Background):** `#F8FAFC` (Slate-50) for base page backgrounds; `#F1F5F9` (Slate-100) for control bars, utility panels, and table headers.
- **Card Surfaces:** Pure `#FFFFFF` with structural borders in `#E2E8F0` (Slate-200) and hover outlines in `#CBD5E1` (Slate-300).
- **Core Chrome & Navigation:** `#0F172A` (Slate-900) for critical navigational anchors, primary command actions, and deep header bars; `#1E293B` (Slate-800) for secondary framing.

### Primary Accents & Telemetry
- **Primary Interactive / Water Dynamic:** `#0284C7` (Sky-600) for active telemetry states, focused inputs, and primary interactive links.
- **Secondary Telemetry / AI Forecast:** `#38BDF8` (Sky-400) for predictive trendlines, AI confidence intervals, and sensor ray graphs.

### Semantic Risk Scale (Non-Negotiable)
Color is strictly reserved for risk attribution and system status. It is never used decoratively:
- **Low Risk / Safe Operations:** `#10B981` (Emerald-500) | Soft Container: `#ECFDF5` | Text/Stroke: `#047857`
- **Moderate Risk / Advisory:** `#F59E0B` (Amber-500) | Soft Container: `#FFFBEB` | Text/Stroke: `#B45309`
- **High Risk / Severe Watch:** `#F97316` (Orange-500) | Soft Container: `#FFF7ED` | Text/Stroke: `#C2410C`
- **Critical Risk / Inundation Alert:** `#EF4444` (Rose-500) | Soft Container: `#FEF2F2` | Text/Stroke: `#B91C1C`

## Typography

Typography balances rapid scanning with dense, legible data displays. 

- **Primary Headings (Manrope):** Geometric yet friendly, featuring solid legibility and structural balance for dashboard titles, card headers, and basin identifiers.
- **System Body (Inter):** Applied across all analytical prose, descriptions, filter controls, table text, and form fields for optimal neutrality and clear character differentiation.
- **Telemetry & Data Layers (JetBrains Mono):** Monospaced precision is mandatory for river discharge levels (`m³/s`), cumulative rainfall (`mm`), water gauge heights (`m`), timestamps (`UTC+5:30`), and ML model confidence scores (`p-values`). Tabular figures prevent layout jumping during continuous live-streamed data polling.

## Layout & Spacing

The design adopts a rigorous **12-column responsive fluid grid** tuned for analytical command dashboards, splitting screen real estate between dynamic map visualizers and telemetry sidebars.

- **Desktop (≥1280px):** 12 columns, `1.5rem` gutters, `2rem` outer margins. Accommodates a fixed-width left navigation rail (64px collapsed, 240px expanded), an interactive GIS mapping core (spanning 7–8 columns), and an active telemetry/alert stream panel (spanning 4–5 columns).
- **Tablet (768px – 1279px):** 8 columns, `1rem` gutters, `1.5rem` margins. The map core and card streams stack vertically into tabbed master-detail views.
- **Mobile (<768px):** 4 columns, `0.75rem` gutters, `1rem` margins. Prioritizes situational status summary banners, critical alert chips, and expandable metric drawer trays.

Element spacing uses an uncompromising 4px/8px modular rhythm (`0.25rem` intervals) to ensure maximum information density without optical clutter. Compact cards use `0.75rem` padding, while primary analytics surfaces standardize on `1rem` internal padding.

## Elevation & Depth

Visual hierarchy uses a refined pairing of **Low-Contrast Structural Outlines** and **Micro-Diffusion Ambient Shadows**. Surfaces must feel physical and separated, but never heavy or decorative.

- **Level 0 (App Canvas):** Pure background tone (`#F8FAFC`). Flat with no elevation.
- **Level 1 (Telemetry Cards & Panels):** Solid `#FFFFFF` container encased in a crisp `1px solid #E2E8F0` border, lifted with a soft dual-shadow: `0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.03)`.
- **Level 2 (Active Tooltips, Popovers, & Dropdown Menus):** Pure `#FFFFFF` surface with `1px solid #CBD5E1`, raised by: `0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05)`.
- **Level 3 (Modal Overlays, Alert Drawers, & Map Overlays):** Pristine card backed by backdrop blur (`backdrop-blur-sm` over `rgba(15, 23, 42, 0.40)`) supported by: `0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.06)`.
- **Focus & Selection State:** Crisp 2px offset ring in `#0284C7` with no heavy box-glows.

## Shapes

The design system maintains a **Soft/Technical** corner language (`roundedness: 1`). 

- Standard interactive controls (inputs, buttons, segmented toggles), metric badges, and data cards utilize a tight `0.25rem` (4px) radius to preserve horizontal and vertical tracking lines on dense dashboard tables.
- Card panels, modal sheets, and GIS view containers step up to `0.5rem` (8px) (`rounded-lg`).
- River basin status tags and live pulse indicators employ pill silhouettes (`rounded-full`) exclusively to distinguish dynamic status tags from static rectangular layout blocks.

## Components

### Buttons
- **Primary Action:** Solid `#0F172A` background, `#FFFFFF` text, `0.25rem` border radius, font `label-lg`. Subtle hover to `#1E293B`.
- **Secondary / Tactical:** `#FFFFFF` background, `1px solid #E2E8F0` border, `#1E293B` text. Hover transitions to `#F1F5F9`.
- **Destructive / High Alert Action:** Solid `#EF4444` background with pure white text, transitioning to `#DC2626` on hover.

### Risk Status Badges & Chips
- Designed with high-contrast text over a tinted 10% opacity semantic container, bound by a matching 20% opacity border.
- **Low:** `#ECFDF5` background, `#047857` label, `#A7F3D0` outline. Includes steady 6px circular dot indicator in `#10B981`.
- **Moderate:** `#FFFBEB` background, `#B45309` label, `#FDE68A` outline. Dot indicator `#F59E0B`.
- **High:** `#FFF7ED` background, `#C2410C` label, `#FED7AA` outline. Dot indicator `#F97316`.
- **Critical:** `#FEF2F2` background, `#B91C1C` label, `#FECACA` outline. Dot indicator flashes via a restrained 1.5s ease pulse `#EF4444`.

### Data Cards & Sensor Panels
- `#FFFFFF` background, `1px solid #E2E8F0` border, `1rem` internal padding.
- **Header Structure:** Flex layout holding a uppercase category subtitle (`label-md` in `#64748B`), an active river basin headline (`headline-sm`), and a right-aligned telemetry chip or refresh indicator.
- **Value Presentation:** Prominent primary reading (`data-display` in `#0F172A`), followed by standard unit and a delta trend indicator with directional vector arrows (e.g., `+0.42 m/hr`).

### Input Fields & Filter Bars
- Compact height (36px desktop / 40px mobile) to support dense query filters across catchment basins.
- Solid `#FFFFFF` interior with `1px solid #CBD5E1` border, `#0F172A` input text, and `#94A3B8` placeholder. Focused states feature a direct border shift to `#0284C7` with a matching 1px focus shadow.

### Checkboxes & Segmented Filters
- Checkboxes use `0.25rem` roundedness, `#CBD5E1` default stroke, transitioning to `#0284C7` when checked with a crisp white check vector.
- Segmented time horizon controls (e.g., `Now`, `+6h`, `+12h`, `+24h`, `+48h`) sit inside a `#F1F5F9` tray; the active selection uses a raised `#FFFFFF` pill with `#0F172A` text and subtle micro-shadow.

### River Basin Water-Level Gauges (Domain Specific)
- Horizontal dual-track bar: Background track `#E2E8F0` (height: 8px, `rounded-full`). 
- Active water level fill utilizes `#0284C7` up to baseline, shifting dynamically to `#F59E0B`, `#F97316`, or `#EF4444` if the current stage crosses established sensor threshold marks indicated by 1.5px vertical dividers.