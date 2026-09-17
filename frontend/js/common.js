/**
 * Common Shared Utilities & Layout Components for Sri Lanka FloodWatch
 */

import { api } from './api.js';

export const common = {
  /**
   * Determine risk tier object with CSS class names and labels
   * Uses backend risk_level if present, otherwise computes from probability if provided
   */
  getRiskDetails(riskLevel, probability = 0) {
    const normLevel = (riskLevel || '').toUpperCase();
    
    if (normLevel === 'CRITICAL' || (!riskLevel && probability >= 0.8)) {
      return {
        key: 'critical',
        className: 'risk-critical',
        dotColor: '#ef4444',
        textColor: '#b91c1c',
        label: 'Critical Risk',
        shortLabel: 'CRIT',
        badgeBg: 'bg-rose-100 text-rose-800'
      };
    } else if (normLevel === 'HIGH' || (!riskLevel && probability >= 0.65)) {
      return {
        key: 'high',
        className: 'risk-high',
        dotColor: '#f97316',
        textColor: '#c2410c',
        label: 'High Risk',
        shortLabel: 'HIGH',
        badgeBg: 'bg-orange-100 text-orange-800'
      };
    } else if (normLevel === 'MODERATE' || normLevel === 'MOD' || (!riskLevel && probability >= 0.35)) {
      return {
        key: 'moderate',
        className: 'risk-moderate',
        dotColor: '#f59e0b',
        textColor: '#b45309',
        label: 'Moderate Risk',
        shortLabel: 'MOD',
        badgeBg: 'bg-amber-100 text-amber-800'
      };
    } else {
      return {
        key: 'low',
        className: 'risk-low',
        dotColor: '#10b981',
        textColor: '#047857',
        label: 'Low Risk',
        shortLabel: 'LOW',
        badgeBg: 'bg-emerald-100 text-emerald-800'
      };
    }
  },

  /**
   * Generate HTML for standard Risk Badge
   */
  renderRiskBadge(riskLevel, probability) {
    const risk = this.getRiskDetails(riskLevel, probability);
    return `
      <span class="risk-badge ${risk.className}">
        <span class="risk-dot"></span>
        <span>${risk.label}</span>
      </span>
    `;
  },

  /**
   * Format ISO date/timestamp string or current time
   */
  formatTime(dateString) {
    try {
      const d = dateString ? new Date(dateString) : new Date();
      return d.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      });
    } catch (e) {
      return '--:--';
    }
  },

  /**
   * Format date as 'Sep 16, 2026'
   */
  formatDate(dateString) {
    try {
      const d = dateString ? new Date(dateString) : new Date();
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch (e) {
      return 'N/A';
    }
  },

  /**
   * Render or initialize the top Navigation Header
   */
  initHeader(activePath = 'live-dashboard') {
    const headerEl = document.querySelector('header');
    if (!headerEl) return;

    // Highlight active nav links
    const navLinks = headerEl.querySelectorAll('nav a');
    navLinks.forEach(link => {
      const path = link.getAttribute('data-path') || link.getAttribute('href');
      if (path === activePath || link.href.includes(activePath)) {
        link.classList.add('bg-primary-container', 'text-on-primary', 'font-semibold');
        link.classList.remove('text-on-surface-variant');
        link.setAttribute('aria-current', 'page');
      } else {
        link.classList.remove('bg-primary-container', 'text-on-primary', 'font-semibold');
        link.classList.add('text-on-surface-variant');
        link.removeAttribute('aria-current');
      }
    });

    // Update live clock
    this.updateClock();
    setInterval(() => this.updateClock(), 10000);

    // Update active alert badge in header telemetry
    this.updateActiveAlertBadge();
    setInterval(() => this.updateActiveAlertBadge(), 30000);

    // Initialize Theme Switcher in Header
    this.initThemeToggle(headerEl);

    // Global toggle bridge
    window.toggleTheme = () => this.toggleTheme();
  },

  /**
   * Initialize Theme switcher button in header
   */
  initThemeToggle(headerEl) {
    let themeBtn = document.getElementById('themeToggleBtn');
    if (!themeBtn) {
      const rightSegment = headerEl.querySelector('.header-container > div:last-child');
      if (rightSegment) {
        const btn = document.createElement('button');
        btn.id = 'themeToggleBtn';
        btn.className = 'theme-toggle-btn';
        btn.title = 'Toggle Dark / Light Mode';
        btn.setAttribute('aria-label', 'Toggle theme mode');
        btn.innerHTML = `<span class="material-symbols-outlined text-[18px]">dark_mode</span>`;
        btn.onclick = () => this.toggleTheme();
        rightSegment.appendChild(btn);
      }
    } else {
      themeBtn.onclick = () => this.toggleTheme();
    }
    this.syncThemeIcon();
  },

  /**
   * Retrieve current active theme ('dark' or 'light')
   */
  getTheme() {
    return document.documentElement.getAttribute('data-theme') || 
           (document.documentElement.classList.contains('dark') ? 'dark' : 'light');
  },

  /**
   * Apply theme and persist in localStorage
   */
  setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      if (document.body) document.body.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
      if (document.body) document.body.classList.remove('dark');
    }
    try {
      localStorage.setItem('floodwatch_theme', theme);
    } catch (e) {}
    this.syncThemeIcon();
  },

  /**
   * Toggle between dark and light mode
   */
  toggleTheme() {
    const current = this.getTheme();
    const next = current === 'dark' ? 'light' : 'dark';
    this.setTheme(next);
  },

  /**
   * Synchronize button icon with active theme
   */
  syncThemeIcon() {
    const btn = document.getElementById('themeToggleBtn');
    if (!btn) return;
    const isDark = this.getTheme() === 'dark';
    const icon = btn.querySelector('.material-symbols-outlined');
    if (icon) {
      icon.textContent = isDark ? 'light_mode' : 'dark_mode';
      icon.style.color = isDark ? '#fbbf24' : '#0284c7';
    }
  },

  /**
   * Update header timestamp display
   */
  updateClock() {
    const clockEl = document.getElementById('liveClock') || document.querySelector('.header-live-time');
    if (clockEl) {
      clockEl.textContent = this.formatTime();
    }
  },

  /**
   * Update Active Alert telemetry indicator in header
   */
  async updateActiveAlertBadge() {
    try {
      const data = await api.getActiveAlerts(10);
      const activeCount = data.active_count !== undefined ? data.active_count : (data.items ? data.items.length : 0);
      
      let badge = document.getElementById('headerActiveAlertsBadge');
      if (!badge) {
        const telemetryContainer = document.querySelector('.header-telemetry');
        if (telemetryContainer) {
          const div = document.createElement('div');
          div.id = 'headerActiveAlertsBadge';
          div.className = 'header-item cursor-pointer';
          div.onclick = () => window.location.href = 'alerts.html';
          telemetryContainer.appendChild(div);
          badge = div;
        }
      }

      if (badge) {
        if (activeCount > 0) {
          badge.innerHTML = `
            <span class="w-2 h-2 rounded-full bg-error animate-pulse"></span>
            <span class="text-error font-semibold text-xs">${activeCount} Active Alert${activeCount > 1 ? 's' : ''}</span>
          `;
          badge.style.display = 'flex';
        } else {
          badge.innerHTML = `
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span class="text-on-surface-variant text-xs">0 Active Alerts</span>
          `;
          badge.style.display = 'flex';
        }
      }
    } catch (e) {
      // Degrade gracefully if backend alert endpoint is loading
    }
  },

  /**
   * Safely format numbers
   */
  formatNumber(val, decimals = 1, fallback = 'N/A') {
    if (val === null || val === undefined || isNaN(val)) return fallback;
    return Number(val).toFixed(decimals);
  }
};

