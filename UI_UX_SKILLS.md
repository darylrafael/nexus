# Nexus UI/UX Design System Skills & Principles

This document curates the best UI/UX principles from top GitHub design system repositories (like Vercel, shadcn/ui, Radix, and GitHub Primer) to guide the development of the Nexus web dashboard.

## 1. Core Aesthetic Principles (The "Wow" Factor)
Based on modern web app guidelines:
*   **Vibrant & Modern Colors:** Avoid flat, generic colors. Use curated HSL palettes. Incorporate dark mode by default with deep, sleek backgrounds (e.g., `#09090b`) and high-contrast text.
*   **Glassmorphism & Depth:** Use subtle blurs (`backdrop-blur`), translucent backgrounds, and soft, multi-layered drop shadows to create depth.
*   **Modern Typography:** Use clean sans-serif fonts (Inter, Roboto, Outfit) with strict typographic hierarchies. Never use browser default styling.

## 2. Interaction & Micro-animations
An interface must feel alive:
*   **Hover States:** Every interactive element must respond to hover and focus states smoothly (e.g., `transition-all duration-200`).
*   **Micro-interactions:** Use subtle scaling (e.g., `scale-105` on hover for cards) and fade-ins for loading new data to prevent jarring UI jumps.

## 3. Structural Best Practices (From GitHub Primer & Vercel)
*   **Atomic Design:** Break components down to their smallest parts (Buttons, Inputs, Cards) and reuse them consistently. 
*   **Separation of Concerns:** Components should not manage their own external margins. Let the parent layout handle spacing (using Flexbox/Grid gaps) to keep components reusable anywhere.
*   **Design Tokens:** Manage colors, spacing, and typography using global CSS variables in `index.css` (e.g., `--primary: 220 80% 50%`) rather than hardcoding hex codes.

## 4. Layout & Information Architecture
For financial and analytical dashboards (like Nexus):
*   **Dashboard Grid:** Use a responsive CSS grid layout. Sidebars for navigation, top headers for global context, and a main content area for widgets.
*   **Data Scannability:** Financial data (Accuracy rates, IHSG indices) must be instantly readable. Use large typography for key metrics and color-coding (Green for wins/upsides, Red for losses/downsides).
*   **Progressive Disclosure:** Don't overwhelm the user with text. Show the top-level "Accuracy" and "Prediction", and allow them to expand to read the full "Lessons Learned" and root cause analysis.

## 5. Development Strategy (Vanilla CSS & React/Next.js)
*   **CSS Architecture:** Since we prioritize Vanilla CSS for control, utilize modern CSS features: CSS Variables, Flexbox, Grid, and `calc()`.
*   **Accessibility (a11y):** Ensure proper ARIA labels, semantic HTML tags (`<main>`, `<nav>`, `<section>`), and high contrast ratios.

## 6. Design System Architecture (From awesome-design-systems)
A true, professional design system goes beyond just UI components. When building the Nexus dashboard, we will adhere to these 4 pillars of a complete design system:
1.  **Components:** Coded patterns and examples that are reusable and modular.
2.  **Voice & Tone:** The interface must use a consistent, professional, yet accessible language when presenting AI analysis.
3.  **Designers Kit:** Maintaining a clear set of design variables (our Vanilla CSS variables) that act as the source of truth.
4.  **Source Code & Documentation:** The code must be clean, publicly readable (if open-sourced), and self-documenting.

---
*Reference Context Added: 2026-06-16*
*Sourced from principles found in Awesome UI/UX, GitHub Primer, awesome-design-systems (Alex Pate), and modern frontend ecosystems.*
