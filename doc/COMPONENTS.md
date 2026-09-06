# Zomato ETL Analytics — Component Reference

Each entry below is a self-contained component: the markup taken from `index.html`
and the matching rules from `style.css`. Tokens (`--c-*`) and the CSS reset live in
[Global Setup](#global-setup) at the bottom and are shared by every component.

---

## App Shell
___

### HTML

```html
<div class="app">

  <header class="app-header"> ... </header>

  <div class="app-body">
    <div class="app-body-navigation"> ... </div>
    <div class="app-body-main-content"> ... </div>
    <div class="app-body-sidebar"> ... </div>
  </div>

</div>
```

### CSS

```css
.app {
  min-height: 100vh;
  width: 100%;
  max-width: none;
  background-color: var(--c-gray-800);
  padding: 2vw 4vw 6vw;
  display: flex;
  flex-direction: column;
}

.app-body {
  height: 100%;
  display: grid;
  grid-template-columns:
    minmax(min-content, 175px)
    minmax(max-content, 1fr)
    minmax(min-content, 400px);
  column-gap: 4rem;
  padding-top: 2.5rem;
}
```

---

## Header
___

### HTML

```html
<header class="app-header">

  <div class="app-header-logo"> ...logo... </div>

  <div class="app-header-navigation">
    <div class="tabs"> ...tabs... </div>
  </div>

  <div class="app-header-actions">
    <button class="user-profile"> ... </button>
    <div class="app-header-actions-buttons">
      <button class="icon-button large">⌕</button>
      <button class="icon-button large">!</button>
    </div>
  </div>

  <div class="app-header-mobile">
    <button class="icon-button large">☰</button>
  </div>

</header>
```

### CSS

```css
.app-header {
  display: grid;
  grid-template-columns:
    minmax(min-content, 175px)
    minmax(max-content, 1fr)
    minmax(max-content, 400px);
  column-gap: 4rem;
  align-items: flex-end;
}

.app-header-logo { min-width: 0; }

.app-header-actions {
  display: flex;
  align-items: center;
}

.app-header-actions-buttons {
  display: flex;
  border-left: 1px solid var(--c-gray-600);
  margin-left: 2rem;
  padding-left: 2rem;
}

.app-header-actions-buttons > * + * { margin-left: 1rem; }

.app-header-mobile { display: none; }

@media (max-width: 1200px) {
  .app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--c-gray-600);
  }
  .app-header-navigation,
  .app-header-actions { display: none; }
  .app-header-mobile { display: flex; }
}
```

---

## Logo / Brand
___

### HTML

```html
<div class="logo">
  <span class="logo-icon">
    <span class="zomato-mark">Z</span>
  </span>
  <h1 class="logo-title">
    <span>Zomato</span>
    <span>ETL Analytics</span>
  </h1>
</div>
```

### CSS

```css
.logo {
  display: flex;
  align-items: center;
  padding-bottom: 1rem;
  padding-top: 1rem;
  border-bottom: 1px solid var(--c-gray-600);
}

.logo-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
}

.zomato-mark {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--c-zomato);
  color: white;
  font-weight: 700;
  font-size: 17px;
}

.logo-title {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
  margin-left: 0.75rem;
}

.logo-title span:first-child { color: var(--c-text-primary); }
.logo-title span:last-child  { color: var(--c-text-tertiary); font-size: .82em; }

@media (max-width: 500px) {
  .logo-title { font-size: .9rem; }
}
```

---

## Top Tabs
___

### HTML

```html
<div class="tabs">
  <a href="#" class="active">Overview</a>
  <a href="#">Customers</a>
  <a href="#">Operations</a>
  <a href="#">Pipeline</a>
  <a href="#">Restaurants</a>
</div>
```

### CSS

```css
.tabs {
  display: flex;
  justify-content: space-between;
  color: var(--c-text-tertiary);
  border-bottom: 1px solid var(--c-gray-600);
}

.tabs a {
  padding-top: 1rem;
  padding-bottom: 1rem;
  text-decoration: none;
  border-top: 2px solid transparent;
  display: inline-flex;
  transition: .25s ease;
}

.tabs a.active,
.tabs a:hover,
.tabs a:focus {
  color: var(--c-text-primary);
  border-color: var(--c-zomato);
}
```

---

## User Profile
___

### HTML

```html
<button class="user-profile">
  <span>Data Engineer</span>
  <span class="avatar">DE</span>
</button>
```

### CSS

```css
.user-profile {
  display: flex;
  align-items: center;
  border: 0;
  background: transparent;
  cursor: pointer;
  color: var(--c-text-tertiary);
  transition: .25s ease;
}

.user-profile:hover,
.user-profile:focus { color: var(--c-text-primary); }

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  overflow: hidden;
  margin-left: 1.5rem;
  flex-shrink: 0;
  background: var(--c-zomato);
  color: white;
  font-size: 11px;
  font-weight: 600;
}
```

---

## Icon Button
___

### HTML

```html
<button class="icon-button">→</button>
<button class="icon-button large">⌕</button>
```

### CSS

```css
.icon-button {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--c-gray-500);
  background-color: transparent;
  color: var(--c-text-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: .25s ease;
  flex-shrink: 0;
}

.icon-button.large {
  width: 42px;
  height: 42px;
  font-size: 1.25em;
}

.icon-button:hover,
.icon-button:focus {
  background-color: var(--c-gray-600);
  box-shadow:
    0 0 0 4px var(--c-gray-800),
    0 0 0 5px var(--c-text-tertiary);
}
```

---

## Sidebar Navigation (Left)
___

### HTML

```html
<div class="app-body-navigation">

  <nav class="navigation">
    <a href="#" class="active"><i>▦</i><span>Dashboard</span></a>
    <a href="#"><i>↓</i><span>Ingestion</span></a>
    <a href="#"><i>↻</i><span>Transform</span></a>
    <a href="#"><i>✓</i><span>Data Quality</span></a>
    <a href="#"><i>◫</i><span>Warehouse</span></a>
    <a href="#"><i>⌁</i><span>Reports</span></a>
  </nav>

  <footer class="footer">
    <h1>Zomato<small>©</small></h1>
    <div>
      Zomato ETL Platform<br>
      Analytics Dashboard<br>
      Static Demo
    </div>
  </footer>

</div>
```

### CSS

```css
.app-body-navigation {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.navigation {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  color: var(--c-text-tertiary);
}

.navigation a {
  display: flex;
  align-items: center;
  text-decoration: none;
  transition: .25s ease;
}

.navigation a + a { margin-top: 1.25rem; }

.navigation a:hover,
.navigation a:focus,
.navigation a.active {
  transform: translateX(4px);
  color: var(--c-text-primary);
}

.navigation i {
  width: 22px;
  margin-right: .75rem;
  font-size: 1.15em;
  font-style: normal;
  flex-shrink: 0;
}

.footer { margin-top: auto; }

.footer h1 {
  font-size: 1.5rem;
  line-height: 1.125;
  display: flex;
  align-items: flex-start;
}

.footer small { font-size: .5em; margin-left: .25em; }

.footer div {
  border-top: 1px solid var(--c-gray-600);
  margin-top: 1.5rem;
  padding-top: 1rem;
  font-size: .75rem;
  color: var(--c-text-tertiary);
}

@media (max-width: 1200px) {
  .app-body-navigation { display: none; }
}
```

---

## Section Header
___

### HTML

```html
<section class="analytics-section">
  <div class="analytics-section-header">
    <div>
      <h2>Delivery analytics</h2>
      <p>Orders, revenue and pipeline distribution</p>
    </div>
    <span class="analytics-period">Last 7 days</span>
  </div>
  ...
</section>
```

### CSS

```css
.service-section > h2 {
  font-size: 1.5rem;
  margin-bottom: 1.25rem;
}

.analytics-section { margin-top: 2.5rem; }

.analytics-section-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding-bottom: .75rem;
  border-bottom: 1px solid var(--c-gray-600);
}

.analytics-section-header h2 { font-size: 1.5rem; }

.analytics-section-header p,
.analytics-period,
.chart-card-header span {
  color: var(--c-text-tertiary);
  font-size: .75rem;
}

.analytics-period {
  border: 1px solid var(--c-gray-600);
  border-radius: 4px;
  padding: .35rem .6rem;
}
```

---

## Filter Toolbar
___

### HTML

```html
<div class="service-section-header">

  <div class="search-field">
    <span>⌕</span>
    <input type="text" placeholder="Restaurant, area or order">
  </div>

  <div class="dropdown-field">
    <select>
      <option>All Cities</option>
      <option>Bangalore</option>
      <option>Mumbai</option>
    </select>
    <span>⌄</span>
  </div>

  <button class="flat-button">Search</button>

</div>

<div class="mobile-only">
  <button class="flat-button">Toggle filters</button>
</div>
```

### CSS

```css
.service-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.service-section-header > * + * { margin-left: 1.25rem; }

.search-field {
  display: flex;
  flex-grow: 1;
  position: relative;
}

.search-field input {
  width: 100%;
  padding-top: .5rem;
  padding-bottom: .5rem;
  border: 0;
  border-bottom: 1px solid var(--c-gray-600);
  background-color: transparent;
  padding-left: 1.5rem;
  color: var(--white);
  outline: none;
}

.search-field > span {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  color: var(--c-text-tertiary);
}

.dropdown-field {
  display: flex;
  flex-grow: 1;
  position: relative;
}

.dropdown-field select {
  width: 100%;
  padding-top: .5rem;
  padding-bottom: .5rem;
  border: 0;
  border-bottom: 1px solid var(--c-gray-600);
  background-color: transparent;
  padding-right: 1.5rem;
  appearance: none;
  color: var(--c-text-tertiary);
}

.dropdown-field > span {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
}

.flat-button {
  border-radius: 6px;
  background-color: var(--c-gray-700);
  padding: .5em 1.5em;
  border: 0;
  color: var(--c-text-secondary);
  transition: .25s ease;
  cursor: pointer;
}

.flat-button:hover,
.flat-button:focus { background-color: var(--c-gray-600); }

.mobile-only { display: none; }

@media (max-width: 1000px) {
  .service-section-header { display: none; }
  .mobile-only { display: inline-flex; }
}
```

---

## KPI Tile
___

### HTML

```html
<div class="tiles">

  <article class="tile">
    <div class="tile-header">
      <i class="tile-icon">↗</i>
      <h3>
        <span>Total Orders</span>
        <span>Delivered orders</span>
      </h3>
    </div>

    <div class="metric">48,291</div>

    <a href="#">
      <span>View analytics</span>
      <span class="icon-button">→</span>
    </a>
  </article>

  <!-- tile 2 and tile 3 repeat the same structure -->

</div>
```

### CSS

```css
.tiles {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  column-gap: 1rem;
  row-gap: 1rem;
  margin-top: 1.25rem;
}

.tile {
  padding: 1rem;
  border-radius: 8px;
  background-color: var(--c-olive-500);
  color: var(--c-gray-900);
  min-height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  transition: .25s ease;
}

.tile:hover { transform: translateY(-5px); }

.tile:nth-child(2) { background-color: var(--c-green-500); }
.tile:nth-child(3) { background-color: var(--c-gray-300); }

.tile-header {
  display: flex;
  align-items: center;
}

.tile-icon {
  font-size: 2.5em;
  font-style: normal;
  line-height: 1;
}

.tile-header h3 {
  display: flex;
  flex-direction: column;
  line-height: 1.375;
  margin-left: .5rem;
}

.tile-header h3 span:first-child { font-weight: 600; }
.tile-header h3 span:last-child  { font-size: .825em; font-weight: 300; }

.metric {
  font-size: 2.35rem;
  font-weight: 500;
  letter-spacing: -.04em;
}

.tile a {
  text-decoration: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.tile a .icon-button {
  color: inherit;
  border-color: inherit;
}

@media (max-width: 700px) {
  .tiles { grid-template-columns: 1fr; }
}
```

---

## Chart Card (wrapper)
___

### HTML

```html
<div class="charts-grid">
  <article class="chart-card">
    <div class="chart-card-header">
      <h3>Daily orders</h3>
      <span>Orders</span>
    </div>
    <!-- one of: .bar-chart / .line-chart / .pie-chart-wrap -->
  </article>
  ...
</div>
```

### CSS

```css
.charts-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  margin-top: 1.25rem;
}

.chart-card {
  min-width: 0;
  min-height: 265px;
  padding: 1rem;
  border: 1px solid var(--c-gray-600);
  border-radius: 8px;
  background: var(--c-gray-800);
}

.chart-card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: .75rem;
}

.chart-card-header h3 {
  font-size: .95rem;
  font-weight: 500;
}

@media (max-width: 700px) {
  .charts-grid { grid-template-columns: 1fr; }
}
```

---

## Graph — Bar Chart
___

### HTML

```html
<div class="bar-chart" role="img" aria-label="Daily orders for Monday through Sunday">
  <div class="bar-column"><span class="bar-value">5.8k</span><i style="height: 52%"></i><label>Mon</label></div>
  <div class="bar-column"><span class="bar-value">6.4k</span><i style="height: 64%"></i><label>Tue</label></div>
  <div class="bar-column"><span class="bar-value">7.1k</span><i style="height: 78%"></i><label>Wed</label></div>
  <div class="bar-column"><span class="bar-value">6.7k</span><i style="height: 70%"></i><label>Thu</label></div>
  <div class="bar-column"><span class="bar-value">8.2k</span><i style="height: 92%"></i><label>Fri</label></div>
  <div class="bar-column"><span class="bar-value">7.6k</span><i style="height: 84%"></i><label>Sat</label></div>
  <div class="bar-column"><span class="bar-value">6.5k</span><i style="height: 67%"></i><label>Sun</label></div>
</div>
```

### CSS

```css
.bar-chart {
  height: 190px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: .45rem;
  margin-top: 1.5rem;
  padding-top: 1.25rem;
  border-bottom: 1px solid var(--c-gray-600);
  background: repeating-linear-gradient(to bottom,
    transparent 0, transparent 46px,
    rgba(150, 149, 147, .12) 47px, transparent 48px);
}

.bar-column {
  height: 100%;
  flex: 1;
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: flex-end;
  min-width: 0;
}

.bar-column i {
  display: block;
  width: min(22px, 80%);
  min-height: 10px;
  border-radius: 3px 3px 0 0;
  background: var(--c-green-500);
}

.bar-column:nth-child(3n) i { background: var(--c-olive-500); }
.bar-column:nth-child(5) i  { background: var(--c-zomato); }

.bar-column label,
.bar-value {
  font-size: .65rem;
  color: var(--c-text-tertiary);
}

.bar-value {
  margin-bottom: .25rem;
  color: var(--c-text-secondary);
}

.bar-column label {
  margin-top: .5rem;
  transform: translateY(1.2rem);
}
```

---

## Graph — Line Chart
___

### HTML

```html
<div class="line-chart" role="img" aria-label="Revenue trend rising from Monday through Sunday">
  <svg viewBox="0 0 320 170" preserveAspectRatio="none" aria-hidden="true">
    <path class="line-grid" d="M0 30H320 M0 85H320 M0 140H320" />
    <path class="line-area" d="M0 126 L53 112 L106 118 L159 74 L212 91 L265 48 L320 35 L320 170 L0 170 Z" />
    <path class="line-path" d="M0 126 L53 112 L106 118 L159 74 L212 91 L265 48 L320 35" />
    <circle cx="0" cy="126" r="4" /><circle cx="53" cy="112" r="4" /><circle cx="106" cy="118" r="4" />
    <circle cx="159" cy="74" r="4" /><circle cx="212" cy="91" r="4" /><circle cx="265" cy="48" r="4" />
    <circle cx="320" cy="35" r="4" />
  </svg>
  <div class="line-labels">
    <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
  </div>
</div>
```

### CSS

```css
.line-chart {
  height: 190px;
  position: relative;
  margin-top: 1.5rem;
  padding-bottom: 1.2rem;
}

.line-chart svg {
  width: 100%;
  height: 160px;
  overflow: visible;
}

.line-grid {
  fill: none;
  stroke: var(--c-gray-600);
  stroke-width: 1;
  stroke-dasharray: 3 5;
}

.line-area { fill: rgba(69, 255, 188, .12); }

.line-path {
  fill: none;
  stroke: var(--c-green-500);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.line-chart circle {
  fill: var(--c-gray-800);
  stroke: var(--c-green-500);
  stroke-width: 2;
}

.line-labels {
  display: flex;
  justify-content: space-between;
  color: var(--c-text-tertiary);
  font-size: .65rem;
}
```

---

## Graph — Pie Chart
___

### HTML

```html
<article class="chart-card pie-card">
  <div class="chart-card-header">
    <h3>Order status</h3>
    <span>Distribution</span>
  </div>

  <div class="pie-chart-wrap">
    <div class="pie-chart" role="img"
         aria-label="Order status: 74 percent delivered, 18 percent preparing, 8 percent cancelled">
      <span>48.3k<small>orders</small></span>
    </div>
    <div class="pie-legend">
      <span><i class="legend-delivered"></i>Delivered <strong>74%</strong></span>
      <span><i class="legend-preparing"></i>Preparing <strong>18%</strong></span>
      <span><i class="legend-cancelled"></i>Cancelled <strong>8%</strong></span>
    </div>
  </div>
</article>
```

### CSS

```css
.pie-chart-wrap {
  display: flex;
  align-items: center;
  justify-content: space-around;
  gap: 1rem;
  height: 190px;
  margin-top: 1.5rem;
}

.pie-chart {
  width: 142px;
  aspect-ratio: 1;
  border-radius: 50%;
  background: conic-gradient(
    var(--c-green-500) 0 74%,
    var(--c-olive-500) 74% 92%,
    var(--c-zomato) 92% 100%);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.pie-chart::before {
  content: "";
  width: 82px;
  aspect-ratio: 1;
  border-radius: 50%;
  background: var(--c-gray-800);
  grid-area: 1 / 1;
}

.pie-chart > span {
  grid-area: 1 / 1;
  z-index: 1;
  text-align: center;
  font-size: 1rem;
  font-weight: 600;
}

.pie-chart small {
  display: block;
  font-size: .6rem;
  font-weight: 400;
  color: var(--c-text-tertiary);
}

.pie-legend {
  display: flex;
  flex-direction: column;
  gap: .7rem;
  font-size: .7rem;
  color: var(--c-text-tertiary);
}

.pie-legend span {
  display: flex;
  align-items: center;
  white-space: nowrap;
}

.pie-legend i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: .45rem;
}

.legend-delivered { background: var(--c-green-500); }
.legend-preparing { background: var(--c-olive-500); }
.legend-cancelled { background: var(--c-zomato); }
```

---

## List Row (Restaurant Performance)
___

### HTML

```html
<section class="transfer-section">

  <div class="transfer-section-header">
    <h2>Latest restaurant performance</h2>
    <div class="filter-options">
      <p>Top restaurants by revenue</p>
      <button class="icon-button">≡</button>
      <button class="icon-button">+</button>
    </div>
  </div>

  <div class="transfers">

    <div class="transfer">
      <div class="transfer-logo restaurant-logo">T</div>
      <dl class="transfer-details">
        <div><dt>Truffles</dt><dd>Restaurant</dd></div>
        <div><dt>2,481</dt><dd>Orders</dd></div>
        <div><dt>4.5 ★</dt><dd>Rating</dd></div>
      </dl>
      <div class="transfer-number">₹782K</div>
    </div>

    <!-- more .transfer rows -->

  </div>

</section>
```

### CSS

```css
.transfer-section { margin-top: 2.5rem; }

.transfer-section-header {
  display: flex;
  align-items: center;
  width: 100%;
  padding-bottom: .75rem;
  border-bottom: 1px solid var(--c-gray-600);
}

.transfer-section-header h2 { font-size: 1.5rem; }

.filter-options {
  margin-left: 1.25rem;
  padding-left: 1.25rem;
  border-left: 1px solid var(--c-gray-600);
  display: flex;
  align-items: center;
  flex: 1 1 auto;
}

.filter-options p {
  color: var(--c-text-tertiary);
  font-size: .875rem;
}

.filter-options p + * {
  margin-left: auto;
  margin-right: .75rem;
}

.transfers {
  display: flex;
  flex-direction: column;
  margin-top: 1.5rem;
}

.transfer {
  display: flex;
  align-items: center;
  width: 100%;
  font-size: .875rem;
}

.transfer + .transfer { margin-top: 2rem; }

.transfer-logo {
  background-color: var(--c-gray-200);
  border-radius: 4px;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.restaurant-logo {
  background-color: var(--c-zomato);
  color: white;
  font-size: 1rem;
  font-weight: 600;
}

.transfer-details {
  margin-left: 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 1;
}

.transfer-details > div { width: calc(100% / 3 - 1rem); }
.transfer-details > div + div { margin-left: 1rem; }
.transfer-details dt { font-weight: 500; }
.transfer-details dd { color: var(--c-text-tertiary); margin-top: 2px; }

.transfer-number {
  margin-left: 2rem;
  font-size: 1.125rem;
  flex-shrink: 0;
  width: 15%;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1000px) {
  .transfer { align-items: flex-start; flex-direction: column; }
  .transfer-details { flex-wrap: wrap; margin-left: 0; margin-top: 1rem; }
  .transfer-details > div { width: 100%; }
  .transfer-details > div + div { margin-left: 0; margin-top: 1rem; }
  .transfer-number { margin-left: 0; margin-top: 1.25rem; width: 100%; justify-content: flex-start; }
}
```

---

## Sidebar (Right) — Pipeline Health
___

### HTML

```html
<div class="app-body-sidebar">
  <section class="payment-section">

    <h2>Pipeline Health</h2>

    <div class="payment-section-header">
      <p>Latest ETL pipeline run</p>
      <div>
        <button class="card-button active">ETL</button>
        <button class="card-button">DBT</button>
      </div>
    </div>

    <div class="payments"> ...pipeline cards... </div>
    <div class="faq"> ...data quality... </div>
    <div class="payment-section-footer"> ...footer... </div>

  </section>
</div>
```

### CSS

```css
.payment-section > h2 { font-size: 1.5rem; }

.payment-section-header {
  display: flex;
  align-items: center;
  margin-top: 1rem;
}

.payment-section-header p {
  color: var(--c-text-tertiary);
  font-size: .875rem;
}

.payment-section-header > div {
  padding-left: 1rem;
  margin-left: auto;
  display: flex;
  align-items: center;
}

.payment-section-header > div > * + * { margin-left: .5rem; }

.card-button {
  display: flex;
  width: 55px;
  height: 34px;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background-color: transparent;
  transition: .25s ease;
  border-radius: 4px;
  border: 2px solid var(--c-gray-600);
  color: var(--c-text-primary);
  cursor: pointer;
  font-size: .7rem;
  font-weight: 600;
}

.card-button:focus,
.card-button:hover,
.card-button.active {
  color: var(--c-gray-800);
  background-color: var(--c-white);
  border-color: var(--c-white);
}

@media (max-width: 700px) {
  .payment-section { margin-top: 3rem; }
}
```

---

## Card — Pipeline Status
___

### HTML

```html
<div class="payments">

  <div class="payment">
    <div class="card green">
      <span>EXTRACT</span>
      <span>48,932</span>
    </div>
    <div class="payment-details">
      <h3>Rows ingested</h3>
      <div>
        <span>48,932</span>
        <button class="icon-button">→</button>
      </div>
    </div>
  </div>

  <!-- .card olive (VALIDATE) and .card gray (DBT) repeat -->

</div>
```

### CSS

```css
.payments {
  display: flex;
  flex-direction: column;
  margin-top: 1.5rem;
}

.payment {
  display: flex;
  align-items: center;
}

.payment + .payment { margin-top: 1rem; }

.card {
  width: 125px;
  padding: .375rem;
  aspect-ratio: 3 / 2;
  flex-shrink: 0;
  border-radius: 6px;
  color: var(--c-gray-800);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: .75rem;
  font-weight: 600;
}

.card.green { background-color: var(--c-green-500); }
.card.olive { background-color: var(--c-olive-500); }
.card.gray  { background-color: var(--c-gray-300); }

.card span:last-child { align-self: flex-end; }

.payment-details {
  display: flex;
  width: 100%;
  flex-direction: column;
  margin-left: 1.5rem;
}

.payment-details h3 {
  font-size: 1rem;
  color: var(--c-text-tertiary);
  font-weight: 400;
}

.payment-details > div {
  margin-top: .75rem;
  padding-top: .75rem;
  padding-bottom: .75rem;
  border-top: 1px solid var(--c-gray-600);
  border-bottom: 1px solid var(--c-gray-600);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 1;
}

.payment-details > div > span { font-size: 1.5rem; }

@media (max-width: 500px) {
  .payment { align-items: flex-start; flex-direction: column; }
  .payment-details { margin-left: 0; margin-top: 1rem; }
}
```

---

## Data Quality Summary
___

### HTML

```html
<div class="faq">
  <p>Data quality summary</p>

  <div class="quality-row"><label>Valid rows</label><strong>48,291</strong></div>
  <div class="quality-row"><label>Rejected rows</label><strong>641</strong></div>
  <div class="quality-row"><label>Rejection rate</label><strong>1.31%</strong></div>
  <div class="quality-row"><label>Duplicates</label><strong>214</strong></div>
</div>
```

### CSS

```css
.faq {
  margin-top: 1.5rem;
  display: flex;
  flex-direction: column;
}

.faq > p {
  color: var(--c-text-tertiary);
  font-size: .875rem;
}

.quality-row {
  margin-top: .75rem;
  padding-top: .75rem;
  padding-bottom: .75rem;
  border-top: 1px solid var(--c-gray-600);
  border-bottom: 1px solid var(--c-gray-600);
  font-size: .875rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.quality-row + .quality-row {
  border-top: 0;
  margin-top: 0;
}

.quality-row label { color: var(--c-text-tertiary); }
.quality-row strong { font-weight: 400; color: var(--c-text-primary); }
```

---

## Sidebar Footer
___

### HTML

```html
<div class="payment-section-footer">
  <button class="save-button">Healthy</button>
  <button class="settings-button">
    <span>Last run: 08:42</span>
  </button>
</div>
```

### CSS

```css
.payment-section-footer {
  display: flex;
  align-items: center;
  margin-top: 1.5rem;
}

.save-button {
  border: 1px solid var(--c-green-500);
  color: var(--c-green-500);
  border-radius: 6px;
  padding: .75em 2.5em;
  background-color: transparent;
  cursor: pointer;
}

.settings-button {
  display: flex;
  align-items: center;
  color: var(--c-text-tertiary);
  background-color: transparent;
  border: 0;
  padding: 0;
  margin-left: 1.5rem;
  cursor: pointer;
}
```

---

## Global Setup
___

### HTML

```html
<head>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@100;200;300;400;500;600;700;800;900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="app"> ... </div>
</body>
```

### CSS

```css
/* Reset */
*, *::before, *::after { box-sizing: border-box; }
*:not(dialog) { margin: 0; }

body { line-height: 1.5; -webkit-font-smoothing: antialiased; }

img, picture, video, canvas, svg { display: block; max-width: 100%; }
input, button, textarea, select { font: inherit; }

/* Tokens */
:root {
  --c-gray-900: #000000;
  --c-gray-800: #1f1f1f;
  --c-gray-700: #2e2e2e;
  --c-gray-600: #313131;
  --c-gray-500: #969593;
  --c-gray-400: #a6a6a6;
  --c-gray-300: #bdbbb7;
  --c-gray-200: #f1f1f1;
  --c-gray-100: #ffffff;

  --c-green-500: #45ffbc;
  --c-olive-500: #e3ffa8;
  --c-zomato: #e23744;

  --c-white: var(--c-gray-100);

  --c-text-primary:   var(--c-gray-100);
  --c-text-secondary: var(--c-gray-200);
  --c-text-tertiary:  var(--c-gray-500);
}

html { background: var(--c-gray-900); }

body {
  line-height: 1.5;
  min-height: 100vh;
  font-family: "Be Vietnam Pro", sans-serif;
  background-color: var(--c-gray-900);
  color: var(--c-text-primary);
  display: flex;
  padding: 0;
  justify-content: center;
}

a { color: inherit; }

/* Global focus ring */
input:focus,
select:focus,
a:focus,
button:focus {
  outline: 0;
  box-shadow:
    0 0 0 2px var(--c-gray-800),
    0 0 0 4px var(--c-gray-300);
}
```

---

## Responsive Breakpoints
___

| Width | Effect |
| --- | --- |
| `> 1200px` | Full three-column shell: left nav, main, right sidebar |
| `≤ 1200px` | Header actions → mobile menu button; left nav hidden; body becomes one column |
| `≤ 1000px` | Filter toolbar hidden, `Toggle filters` shown; restaurant rows stack |
| `≤ 700px`  | App padding `20px`; KPI tiles and chart cards go single-column; sidebar gains top space |
| `≤ 500px`  | Logo type shrinks; pipeline rows stack fully |
