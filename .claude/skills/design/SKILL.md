# Csabolanta Design System & UI Guidelines

This document outlines the strict UI/UX, styling, and structural conventions for the Csabolanta (XPlaneTracker) frontend. All new Vue 3 components must strictly adhere to these design rules.

## 1. Color Palette (Tailwind Variables)

The application relies on a deeply dark, sleek aesthetic with a bright cyan accent. Stick strictly to these CSS variables (defined in `style.css`) via Tailwind classes:

- **Backgrounds:** `bg-flight-bg` (`#0b0e14`) for the main app background.
- **Sidebars/Modals:** `bg-flight-sidebar` (`#151921`).
- **Cards/Elements:** `bg-flight-card` (`#1c222d`). Use `hover:bg-flight-card-hover` (`#252d3a`) for interactive cards.
- **Accents:** `text-flight-accent`, `bg-flight-accent`, `border-flight-accent` (`#38bdf8` - Sky Blue).
- **Borders:** `border-flight-border` (`#2d3544`) applied to almost all cards, sidebars, and inputs.
- **Text (Muted):** `text-flight-muted` or `text-slate-400`/`text-slate-500` for secondary info.
- **Semantic Colors:** Use `red-500` (destructive/errors), `green-500` (success), `amber-500` (pending/warnings), and `teal-500` (info). Often used with low-opacity backgrounds (e.g., `bg-red-500/10 text-red-500`).

## 2. Typography Rules

- **Main Headers/Brand:** Use `font-black italic uppercase tracking-tighter` with text sizes like `text-2xl` or `text-3xl`. The absolute main logo uses `font-['Georgia']`.
- **Section Labels/Small Headers:** Heavily utilize tiny, tracked-out text for labels. Standard format: `text-[9px]` or `text-[10px] font-bold text-slate-500 uppercase tracking-widest`.
- **Data & Telemetry:** Always use `font-mono` for numbers, flight stats, FPM, G-Force, and coordinates.
- **Primary Text:** Standard Tailwind `font-sans` with `text-slate-300` or `text-white` for primary readability.

## 3. Component Styling Standards

### Cards

Cards must look slightly elevated but deeply integrated into the dark theme.

- **Standard Card:** `bg-flight-card border border-flight-border rounded-xl p-4 shadow-lg`.
- **Interactive Card:** Add `cursor-pointer transition-colors hover:border-flight-accent/50 group`.

### Buttons

- **Primary Action (Accent):** `bg-flight-accent hover:bg-sky-400 text-flight-bg font-black py-3 px-4 rounded-lg transition-colors shadow-lg uppercase tracking-widest text-xs`.
- **Ghost/Secondary Action:** `bg-flight-card hover:bg-slate-800 text-white font-bold py-3 px-4 rounded-lg transition-colors uppercase tracking-widest text-xs border border-flight-border`.
- **Icon Buttons:** `bg-flight-bg hover:bg-flight-accent/20 text-slate-400 hover:text-flight-accent transition-colors p-2 rounded-md`.

### Inputs & Forms

- **Standard Input:** `w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors`.
- **Input Labels:** Must sit just above the input using the "Section Label" typography (`text-[10px] font-bold text-slate-500 uppercase ml-1`).

### Modals

- **Backdrop:** `fixed inset-0 bg-black/80 flex items-center justify-center z-[5000] p-4 backdrop-blur-sm`.
- **Container:** `bg-flight-sidebar border border-flight-border p-8 rounded-2xl shadow-2xl w-full max-w-md`.

## 4. Iconography

- Use **FontAwesome Solid** icons (`<i class="fa-solid fa-*"></i>`).
- Icons used alongside text inside buttons or badges should generally have a `mr-2` (margin-right) or `ml-2` spacing.

## 5. Layout & Spacing

- Use flexbox and CSS grid heavily.
- Common gaps are `space-y-3` or `space-y-4` for vertical forms/lists.
- Glow effects on active/selected items are achieved using arbitrary shadow values (e.g., `shadow-[0_0_20px_rgba(56,189,248,0.1)]`).

## 6. Development Rules

- Do not write custom CSS in `<style>` blocks unless modifying third-party library internals (like Leaflet or ECharts). Rely entirely on Tailwind utility classes.
- Use `<script setup>` for all Vue components.
- **DO NOT write comments in the code.** Keep the templates and scripts clean.
- New UI text must be written in English.
