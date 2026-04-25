# Central Pulse Dashboard Design

## 1. Problem Frame

- **Primary User:** System Operators, Support Engineers, and Sales Managers at HelloSales.
- **Core Task:** Monitor the real-time operational pulse of the HelloSales platform, including agent turns, worker runs, system health, and error alerts.
- **Business Goal:** Enable immediate identification and triaging of system degradation or AI agent failures to ensure uninterrupted sales campaigns.
- **Technical Constraints:** Must render real-time telemetry and metrics efficiently. Needs to be responsive but optimized for desktop/widescreen monitoring displays.
- **Success Criteria:** Users can instantly tell if the system is healthy, identify which agents/workers are failing, and drill down into traces within one click.
- **Failure Modes:** Data overload causing "alert fatigue," generic layouts that fail to highlight critical failures, and slow rendering of metrics.

## 2. Design Thesis

- **Design Thesis:** The Central Pulse Dashboard is a sharp, high-density command center that prioritizes signal over noise through strict typography, high-contrast borders, and absolute spatial precision.
- **Aesthetic Direction:** High-fidelity industrial / Command Center. Flat surfaces, rigid grid alignments, and a distinct lack of decorative fluff.
- **Emotional Target:** Confidence, focus, and technical absolute control.
- **Memorable Move:** A dense, flush-grid layout with zero-gap 1px borders and a live "heartbeat" visualization for agent/worker activity that flashes subtly on updates.
- **Why it fits:** The default SaaS dashboard (soft, friendly, rounded) communicates "consumer app." This is an operational tool for monitoring autonomous AI agents; it should look like a precision instrument.

## 3. Anti-Generic Guardrails

- **Generic Version:** A gray background with floating white cards, soft drop shadows, heavily rounded corners, and a rainbow of chart colors.
- **Banned Patterns:**
  - Soft drop shadows (elevation).
  - Large gap spacing between cards (masonry style).
  - System default fonts (Inter/Roboto/San Francisco) for critical data.
  - Pastel or low-contrast chart colors.
- **Replacements:**
  - **Shadows -> Borders:** 1px crisp borders (`#2A2A2A` in dark mode) dividing flush panels.
  - **Gaps -> Flush Grid:** Panels touch each other, creating a continuous dashboard surface.
  - **Fonts -> Purposeful Type:** Monospace for all telemetry data; geometric sans for labels.
  - **Colors -> Semantic Strictness:** Only 3 semantic colors (Emerald, Amber, Crimson) plus one electric accent (Cyan) against a near-black background.

## 4. Brand Physics

### Typography
- **Display/Body:** Space Grotesk (or Satoshi). Technical, geometric.
- **Data/Numbers:** JetBrains Mono (or Space Mono). Crucial for tabular data and metric alignment.
- **Scale:** Strict base-8 scale.
- **Weight:** Regular (400) for labels, Medium (500) for data values. Uppercase for micro-labels (e.g., "STATUS:").

### Color
- **Theme:** Dark Mode Primary.
- **Background:** Near-black (`#0D0D0D`).
- **Surface:** Slightly lighter (`#141414`).
- **Borders:** `#2A2A2A`.
- **Text:** Primary (`#EDEDED`), Secondary (`#888888`).
- **Semantic:** 
  - Healthy: `#00E5FF` (Electric Cyan replaces generic green for normal "pulse").
  - Warning: `#FFB020` (Amber).
  - Error: `#FF3366` (Crimson).

### Spacing and Composition
- **Grid:** Rigid 12-column CSS grid.
- **Density:** High density. 16px internal padding for panels. Zero margin between panels (flush borders).
- **Symmetry:** Asymmetric but strictly aligned.

### Shape, Surface, and Texture
- **Corners:** 0px radius (absolute sharp corners).
- **Depth:** Absolutely flat. No shadows. Depth is indicated solely by 1px borders.
- **Texture:** Clean, digital. A very subtle noise overlay could be used in the background to reduce banding on large monitors.

### Motion
- **Purpose:** Draw attention to state changes and live data pulses.
- **Transitions:** Fast and snappy (150ms, `ease-out`).
- **Data Updates:** Numbers subtly flash (opacity 1 -> 0.7 -> 1) when underlying metrics increment.
- **Reduced Motion:** Fallback to instant color changes without opacity flashes.

## 5. System Architecture

- **Tokens:**
  - `font-mono`, `font-sans`
  - `color-bg-base`, `color-border-grid`, `color-accent-pulse`, `color-semantic-error`
  - `spacing-panel-p`
- **Primitives:**
  - `GridContainer`: The zero-gap CSS grid layout wrapper.
  - `Panel`: The base container with 1px borders.
  - `MetricValue`: Monospace text component with built-in flash-on-change behavior.
  - `StatusBadge`: Sharp rectangular badge for Operational/Degraded/Down states.
- **Recipes:**
  - `SystemHealthHeader`: Top bar showing overall status and connection state.
  - `LiveAgentFeed`: Scrolling list of real-time agent turns/tools.
  - `MetricChartPanel`: Sparkline or bar chart container.
- **Pages:**
  - `CentralPulseDashboard`: The main layout composing the recipes.

## 6. Information Hierarchy

1. **See First (Global Context):** System Health Banner (Is the whole system Up, Degraded, or Down?).
2. **Understand First (Immediate Actionability):** Active Alerts & Failed Runs panel (Crimson highlights).
3. **Action First:** Clickable "Run ID" or "Trace ID" links on failed items to jump straight to logs.
4. **Supporting Content:** Throughput metrics (Agent Turns / sec, Worker Runs / min), API latencies.
5. **Trust Signals:** "Last Updated: 0s ago" and a blinking "Live" connection indicator.

## 7. Verification

### Usability Review
- [ ] Overall system status is immediately visible.
- [ ] Failed agents/workers are visually isolated and hard to miss.
- [ ] Links to traces/logs are prominent.

### Accessibility Review
- [ ] Contrast ratios for Electric Cyan, Amber, and Crimson against `#0D0D0D` meet WCAG AA.
- [ ] Metric updates have reduced-motion alternatives.
- [ ] Keyboard navigation flows logically through the grid panels.

### Performance Review
- [ ] SVG sparklines are preferred over heavy canvas charting libraries for simple trends.
- [ ] Live updates use efficient DOM diffing (React/Solid) to prevent layout thrashing.
- [ ] Minimal heavy visual assets (no images or complex CSS gradients).

### Responsive Review
- [ ] The zero-gap grid collapses cleanly to a single column on mobile without breaking borders.
- [ ] Monospace tables wrap or scroll horizontally gracefully on small screens.

### Distinctiveness Review
- [ ] Sharp corners, dark mode, flush grid, and monospace data give it a distinct "Mission Control" vibe rather than a "B2B SaaS" vibe.
- [ ] Rejects the generic "white cards on gray background" standard.