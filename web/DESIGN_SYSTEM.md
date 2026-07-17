# Drown Platform - Design System

A premium dark mode dashboard inspired by GitHub, Linear, Railway, and Stripe.

## 🎨 Color Palette

### Background System
```css
--bg-primary: #0A0E14      /* Deep slate background */
--bg-secondary: #151A21    /* Elevated surfaces (cards, modals) */
--bg-tertiary: #1C2128     /* Hover states, active elements */
--border: #21262D          /* Subtle separation */
--border-accent: #30363D   /* Focus states, stronger borders */
```

### Text Hierarchy
```css
--text-primary: #E6EDF3    /* High contrast, primary content */
--text-secondary: #8B949E  /* Muted gray, labels, secondary info */
--text-tertiary: #6E7681   /* Subdued, timestamps, hints */
```

### Status Colors
```css
--status-running: #3FB950     /* Green - active/healthy */
--status-stopped: #F85149     /* Red - stopped/failed */
--status-warning: #D29922     /* Amber - warnings */
```

### Accent Colors
```css
--accent-blue: #58A6FF        /* Primary accent (links, CTAs) */
--accent-purple: #A371F7      /* Secondary accent (metrics) */
--accent-green: #238636       /* Success actions */
--accent-green-hover: #2EA043 /* Success hover state */
```

## 📐 Typography

### Font Stack
- **Primary**: `'Inter', -apple-system, system-ui, sans-serif`
- **Monospace**: `'JetBrains Mono', 'Fira Code', 'Consolas', monospace`

### Scale
- **Hero**: 48px / 700 weight / -0.02em tracking
- **Page Title**: 32px / 700 weight / -0.02em tracking
- **Section Title**: 18px / 600 weight / normal tracking
- **Body**: 14px / 400 weight
- **Small**: 13px / 400 weight
- **Label**: 12px / 600 weight / 0.5px tracking (uppercase)

## 🎯 Key Design Elements

### Status Indicators

**Running Status Dot**
- Size: 12px circle
- Color: `#3FB950` (green)
- Animation: Pulse effect (2s infinite)
- Glow: `rgba(63, 185, 80, 0.4)`

**Stopped Status Dot**
- Size: 12px circle
- Color: `#F85149` (red)
- No animation (static to convey "inactive")

### Cards & Surfaces
- Background: `#151A21`
- Border: `1px solid #21262D`
- Border Radius: `12px`
- Hover: Border becomes `#30363D`, transform `translateY(-2px)`
- Transition: `200ms cubic-bezier(0.4, 0, 0.2, 1)`
- Shadow on hover: `0 8px 24px rgba(0, 0, 0, 0.4)`

### Buttons

**Primary Button**
- Background: `#238636` (GitHub green)
- Hover: `#2EA043`
- Text: `#E6EDF3`
- Padding: `10px 20px`
- Border Radius: `8px`
- Font: 14px / 500 weight
- Hover effect: translateY(-1px) + shadow

**Secondary Button**
- Background: transparent
- Border: `1px solid #30363D`
- Hover BG: `#1C2128`
- Text: `#8B949E` → `#E6EDF3` on hover

### Header
- Background: `rgba(10, 14, 20, 0.8)` with `backdrop-filter: blur(12px)`
- Glass morphism effect (subtle transparency + blur)
- Border bottom: `1px solid #21262D`
- Sticky positioning

### Micro-interactions
- All transitions: `200ms cubic-bezier(0.4, 0, 0.2, 1)`
- Status dot pulse: `2s infinite`
- Card hover: `translateY(-2px)` + shadow
- Link underlines: Expand from 0 to full width on hover
- Button hover: `translateY(-1px)` + glow shadow

## 📱 Pages

### 1. Apps Overview (`/`)
**Layout**:
- Stats bar: 3 cards (Total Apps, Total Replicas, Running/Stopped)
- App cards grid: 2-3 columns depending on viewport
- Each card shows:
  - Status dot (pulsing if running)
  - App name (18px, semibold)
  - Domain link (opens in new tab)
  - Replica count badge
  - Age in days
  - "View Details" button

### 2. App Detail (`/app/<app_name>`)
**Sections**:
1. **App Info**: Status badge, builder, domain
2. **Replicas Table**: Status, port, container ID, CPU, memory metrics
3. **Environment Variables**: Keys shown, values hidden (toggle to reveal)
4. **Logs**: Dark terminal-style code block
5. **Deployment History**: Timeline with colored left border

**Table Features**:
- Hover row: `background: #1C2128`
- Monospace font for IDs, ports, timestamps
- Metric badges with color coding:
  - High (>80%): Red background
  - Medium (50-80%): Amber background
  - Normal (<50%): Default gray

### 3. Platform Metrics (`/metrics`) **NEW**
**Purpose**: Aggregate resource usage across all apps

**Layout**:
1. **Top Cards** (3 large metric cards):
   - Average CPU Usage across platform
   - Total Active Replicas
   - Total Apps
   - Each with gradient top border accent

2. **All Replicas Table**:
   - Every replica across all apps
   - Sorted by CPU usage (highest first)
   - Clickable app names link to detail page

3. **Per-App Summary**:
   - Grid of cards showing average CPU per app
   - Replica count per app

**Auto-refresh**: Every 15 seconds (more frequent than other pages)

## 🎭 Visual Identity

**Inspiration**: GitHub dark mode + Linear polish + Railway status indicators + Stripe data density

**Key Differentiators**:
1. **Intentional Color System**: Every shade has a purpose, not random grays
2. **Motion Design**: Pulse animations on live indicators, smooth transitions throughout
3. **Information Hierarchy**: Size, weight, color guide the eye naturally
4. **Premium Feel**: Subtle glows, glass morphism header, smooth shadows
5. **Attention to Detail**: Hover states, focus rings, loading states all considered

## 🔧 Technical Implementation

**CSS Variables**: All colors defined as CSS custom properties for consistency

**Transitions**: `cubic-bezier(0.4, 0, 0.2, 1)` for natural, smooth easing

**Glass Morphism**: Header uses `backdrop-filter: blur(12px)` with rgba transparency

**Pulse Animation**: 
```css
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(63, 185, 80, 0.4); }
    50% { box-shadow: 0 0 0 6px transparent; }
}
```

**Auto-refresh**: JavaScript `fetch()` updates data without full page reload every 30s (15s on metrics page)

## 🚀 Live URLs

- Homepage: http://127.0.0.1:5000
- App Detail: http://127.0.0.1:5000/app/<app_name>
- Platform Metrics: http://127.0.0.1:5000/metrics

## 📊 Data Flow

All data pulled through existing `core/database.py` and `core/docker_ops.py` - no direct SQL queries or duplicated logic.

- Apps list: `database.list_apps()`, `database.get_replicas()`
- App details: `database.get_app()`, `database.get_deployment_history()`, `database.get_configs()`
- Metrics: `docker_ops.get_container_metrics()`
- Logs: `docker_ops.get_container_logs()`

---

**Result**: A polished, production-ready dashboard that looks intentionally designed, not AI-generated.
