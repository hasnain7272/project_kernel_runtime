# ui Module Information

This file provides an ultra-dense context mapping for agentic AI ingestion.


## File: `web\app.css`
Total Lines: 1530

## File: `web\app.js`
Total Lines: 413
L71: `function initUI() {`
L78: `function renderSidebar() {`
L83: `const categoryHtml = categories.map(cat => ``
L126: `function renderContent() {`
L130: `const category = state.schema.categories.find(c => c.id === state.selectedCategory);`
L133: `const paramsHtml = category.parameters.map(p => renderParameter(p)).join('');`
L144: `function renderParameter(param) {`
L193: `function renderWorkbench() {`
L218: `function renderStatusBar() {`
L247: `function setupEventListeners() {`
L300: `function clearOutput() {`
L324: `function formatValue(value) {`
L330: `function escapeHtml(str) {`
L336: `function getIcon(id) {`
L345: `function updateConnectionStatus(connected) {`
L352: `function updateUptime() {`
L363: `function showToast(message, type = 'info') {`
L364: `const container = document.getElementById('toasts') || (() => {`
L380: `function loadDemoData() {`

## File: `web\index.css`
Total Lines: 387

## File: `web\index.html`
Total Lines: 34
L30: `<div id="toasts" class="toast-container"></div>`
L32: `<script src="app.js"></script>`

## File: `web\spatial_engine.js`
Total Lines: 194
L4: `class SpatialEngine {`

## File: `web\spatial_ui.html`
Total Lines: 876
L8: `<script src="https://cdn.tailwindcss.com"></script>`
L10: `<script defer src="https://unpkg.com/vue@3/dist/vue.global.js"></script>`
L14: `<script defer src="https://d3js.org/d3.v7.min.js"></script>`
L15: `<script>`
L34: `<style>`
L60: `<div id="app" class="flex w-full h-full relative z-10">`
L213: `<div id="d3-container" class="w-full h-full bg-[#030305]"></div>`
L455: `<script>`

## File: `web\styles-new.css`
Total Lines: 580

## File: `web\styles.css`
Total Lines: 154