/**
 * Common Shared Utilities & Layout Components for Sri Lanka FloodWatch
 */

import { api } from './api.js';
import { i18n } from './i18n.js';
import { notificationUI, notificationPrefs } from './notification_preferences.js';

export const common = {
  i18n,
  notificationPrefs,
  notificationUI,

  /**
   * Get currently selected location ID with fallback to URL search params, localStorage, or default ID
   */
  getSelectedLocationId(defaultId = 1) {
    try {
      if (typeof window !== 'undefined') {
        const urlParams = new URLSearchParams(window.location.search);
        const urlId = urlParams.get('location_id') || urlParams.get('station') || urlParams.get('id');
        if (urlId && !isNaN(parseInt(urlId, 10))) {
          return parseInt(urlId, 10);
        }
        const stored = localStorage.getItem('floodwatch_selected_location_id');
        if (stored && !isNaN(parseInt(stored, 10))) {
          return parseInt(stored, 10);
        }
      }
    } catch (e) {}
    return defaultId;
  },

  /**
   * Store selected location ID in localStorage, optionally update URL, and dispatch location change event
   */
  setSelectedLocationId(locationId, updateUrl = true) {
    if (!locationId || isNaN(parseInt(locationId, 10))) return defaultId || 1;
    const id = parseInt(locationId, 10);
    try {
      if (typeof window !== 'undefined') {
        localStorage.setItem('floodwatch_selected_location_id', String(id));
        if (updateUrl) {
          const url = new URL(window.location.href);
          url.searchParams.set('location_id', id);
          url.searchParams.delete('station');
          url.searchParams.delete('id');
          window.history.replaceState({ location_id: id }, '', url.toString());
        }
        window.dispatchEvent(new CustomEvent('floodwatch:location_changed', { detail: { location_id: id } }));
      }
    } catch (e) {}
    return id;
  },

  /**
   * Determine risk tier object with CSS class names and localized labels
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
        label: this.i18n ? this.i18n.getRiskLabel('CRITICAL') : 'Critical Risk',
        shortLabel: this.i18n ? this.i18n.getRiskShortLabel('CRITICAL') : 'CRIT',
        badgeBg: 'bg-rose-100 text-rose-800'
      };
    } else if (normLevel === 'HIGH' || (!riskLevel && probability >= 0.60)) {
      return {
        key: 'high',
        className: 'risk-high',
        dotColor: '#f97316',
        textColor: '#c2410c',
        label: this.i18n ? this.i18n.getRiskLabel('HIGH') : 'High Risk',
        shortLabel: this.i18n ? this.i18n.getRiskShortLabel('HIGH') : 'HIGH',
        badgeBg: 'bg-orange-100 text-orange-800'
      };
    } else if (normLevel === 'MODERATE' || normLevel === 'MOD' || (!riskLevel && probability >= 0.35)) {
      return {
        key: 'moderate',
        className: 'risk-moderate',
        dotColor: '#f59e0b',
        textColor: '#b45309',
        label: this.i18n ? this.i18n.getRiskLabel('MODERATE') : 'Moderate Risk',
        shortLabel: this.i18n ? this.i18n.getRiskShortLabel('MODERATE') : 'MOD',
        badgeBg: 'bg-amber-100 text-amber-800'
      };
    } else {
      return {
        key: 'low',
        className: 'risk-low',
        dotColor: '#10b981',
        textColor: '#047857',
        label: this.i18n ? this.i18n.getRiskLabel('LOW') : 'Low Risk',
        shortLabel: this.i18n ? this.i18n.getRiskShortLabel('LOW') : 'LOW',
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
        link.classList.add('bg-primary-container', 'text-on-primary', 'font-semibold', 'active');
        link.classList.remove('text-on-surface-variant');
        link.setAttribute('aria-current', 'page');
      } else {
        link.classList.remove('bg-primary-container', 'text-on-primary', 'font-semibold', 'active');
        link.classList.add('text-on-surface-variant');
        link.removeAttribute('aria-current');
      }
    });

    // Initialize Mobile Navigation Drawer & Hamburger
    this.initMobileNav(headerEl, activePath);

    // Update live clock
    this.updateClock();
    setInterval(() => this.updateClock(), 10000);

    // Update active alert badge in header telemetry
    this.updateActiveAlertBadge();
    setInterval(() => this.updateActiveAlertBadge(), 30000);

    // Initialize Theme Switcher in Header
    this.initThemeToggle(headerEl);

    // Initialize Language Selector in Header
    this.initLanguageSelector(headerEl);

    // Initialize Notification Preference UI
    this.notificationUI.init();

    // Global toggle bridges
    window.toggleTheme = () => this.toggleTheme();
    window.openNotificationSettings = () => this.notificationUI.openModal();
    window.setLanguage = (lang) => this.i18n.setLanguage(lang);

    // Update nav link text when language changes
    window.addEventListener('floodwatch:language_changed', () => {
      this.updateHeaderTranslations(headerEl, activePath);
    });
    this.updateHeaderTranslations(headerEl, activePath);
  },

  /**
   * Update header navigation links and labels based on active language
   */
  updateHeaderTranslations(headerEl, activePath) {
    if (!this.i18n) return;
    const navLinks = headerEl.querySelectorAll('nav a');
    navLinks.forEach(link => {
      const path = link.getAttribute('data-path') || link.getAttribute('href');
      if (path.includes('index.html') || path === 'live-dashboard') {
        link.textContent = this.i18n.t('nav.home');
      } else if (path.includes('map.html') || path === 'flood-map') {
        link.textContent = this.i18n.t('nav.map');
      } else if (path.includes('district.html') || path === 'location-details') {
        link.textContent = this.i18n.t('nav.details');
      } else if (path.includes('alerts.html') || path === 'alerts-history') {
        link.textContent = this.i18n.t('nav.alerts');
      }
    });

    const langSelect = document.getElementById('headerLanguageSelect');
    if (langSelect) {
      langSelect.value = this.i18n.getLanguage();
    }
  },

  /**
   * Initialize Public Language Selector in Navigation Header
   */
  initLanguageSelector(headerEl) {
    let langSelect = document.getElementById('headerLanguageSelect');
    if (!langSelect) {
      const rightSegment = headerEl.querySelector('.header-container > div:last-child');
      if (rightSegment) {
        const wrapper = document.createElement('div');
        wrapper.className = 'lang-selector-wrapper flex items-center gap-1 bg-surface-container/60 px-2 py-1 rounded-lg border border-outline-variant/30 text-xs';
        wrapper.innerHTML = `
          <span class="material-symbols-outlined text-[16px] text-outline">language</span>
          <select id="headerLanguageSelect" class="bg-transparent border-none text-on-surface font-semibold focus:outline-none cursor-pointer text-xs" aria-label="Select Language">
            <option value="en">English</option>
            <option value="si">සිංහල</option>
            <option value="ta">தமிழ்</option>
          </select>
        `;
        rightSegment.insertBefore(wrapper, rightSegment.firstChild);
        langSelect = wrapper.querySelector('#headerLanguageSelect');
      }
    }

    if (langSelect) {
      langSelect.value = this.i18n.getLanguage();
      langSelect.onchange = (e) => {
        const selectedLang = e.target.value;
        this.i18n.setLanguage(selectedLang);
      };
    }
  },

  /**
   * Initialize Mobile Drawer Menu and Toggle Button
   */
  initMobileNav(headerEl, activePath) {
    // 1. Ensure mobile menu button exists in header
    let menuBtn = document.getElementById('mobileMenuBtn');
    if (!menuBtn) {
      const rightSegment = headerEl.querySelector('.header-container > div:last-child');
      if (rightSegment) {
        menuBtn = document.createElement('button');
        menuBtn.id = 'mobileMenuBtn';
        menuBtn.className = 'mobile-menu-btn';
        menuBtn.setAttribute('aria-label', 'Toggle navigation menu');
        menuBtn.setAttribute('aria-expanded', 'false');
        menuBtn.innerHTML = `<span class="material-symbols-outlined text-[22px]">menu</span>`;
        rightSegment.appendChild(menuBtn);
      }
    }

    // 2. Ensure mobile drawer & backdrop exist in DOM
    let backdrop = document.getElementById('mobileNavBackdrop');
    let drawer = document.getElementById('mobileNavDrawer');

    if (!drawer) {
      drawer = document.createElement('div');
      drawer.id = 'mobileNavDrawer';
      drawer.className = 'mobile-nav-drawer';
      drawer.setAttribute('role', 'dialog');
      drawer.setAttribute('aria-modal', 'true');
      drawer.setAttribute('aria-label', 'Mobile navigation menu');

      const navItems = [
        { path: 'live-dashboard', href: 'index.html', label: 'Live Dashboard', icon: 'dashboard' },
        { path: 'flood-map', href: 'map.html', label: 'Flood Map', icon: 'map' },
        { path: 'location-details', href: 'district.html', label: 'Location Details', icon: 'analytics' },
        { path: 'alerts-history', href: 'alerts.html', label: 'Alerts & History', icon: 'notifications_active' }
      ];

      const linksHtml = navItems.map(item => {
        const isActive = item.path === activePath || item.href === activePath;
        return `
          <a class="nav-link ${isActive ? 'active' : ''}" data-path="${item.path}" href="${item.href}" ${isActive ? 'aria-current="page"' : ''}>
            <span class="flex items-center gap-2.5">
              <span class="material-symbols-outlined text-[20px] ${isActive ? 'text-white' : 'text-secondary'}">${item.icon}</span>
              <span>${item.label}</span>
            </span>
            <span class="material-symbols-outlined text-[18px] opacity-70">chevron_right</span>
          </a>
        `;
      }).join('');

      drawer.innerHTML = `
        <div class="flex flex-col gap-1.5">
          ${linksHtml}
        </div>
        <div class="mobile-nav-footer">
          <div class="flex items-center justify-between">
            <span class="flex items-center gap-1.5 font-medium">
              <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Live Telemetry Active</span>
            </span>
            <span class="font-data-timestamp text-xs text-outline">Open-Meteo Synced</span>
          </div>
          <div class="text-[11px] text-outline pt-1">
            Flood+ — Sri Lanka Early Warning System
          </div>
        </div>
      `;

      document.body.appendChild(drawer);
    }

    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'mobileNavBackdrop';
      backdrop.className = 'mobile-nav-backdrop';
      document.body.appendChild(backdrop);
    }

    // 3. Setup event listeners
    const toggleDrawer = (open) => {
      const isOpen = open !== undefined ? open : !drawer.classList.contains('open');
      if (isOpen) {
        drawer.classList.add('open');
        backdrop.classList.add('active');
        document.body.style.overflow = 'hidden';
        if (menuBtn) {
          menuBtn.setAttribute('aria-expanded', 'true');
          const icon = menuBtn.querySelector('.material-symbols-outlined');
          if (icon) icon.textContent = 'close';
        }
      } else {
        drawer.classList.remove('open');
        backdrop.classList.remove('active');
        document.body.style.overflow = '';
        if (menuBtn) {
          menuBtn.setAttribute('aria-expanded', 'false');
          const icon = menuBtn.querySelector('.material-symbols-outlined');
          if (icon) icon.textContent = 'menu';
        }
      }
    };

    if (menuBtn) {
      menuBtn.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleDrawer();
      };
    }

    backdrop.onclick = () => toggleDrawer(false);
    backdrop.addEventListener('touchstart', () => toggleDrawer(false), { passive: true });

    // Close on navigation link click
    drawer.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => toggleDrawer(false));
    });

    // Close on Escape key
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && drawer.classList.contains('open')) {
        toggleDrawer(false);
      }
    });

    // Auto-close on resize to desktop
    window.addEventListener('resize', () => {
      if (window.innerWidth > 1024 && drawer.classList.contains('open')) {
        toggleDrawer(false);
      }
    });

    // Global toggle bridge
    window.toggleMobileNav = (open) => toggleDrawer(open);
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
    this.initEmergencyToggle(headerEl);
  },

  /**
   * Initialize Low-Bandwidth / Emergency Mode switch button in header
   */
  initEmergencyToggle(headerEl) {
    if (!headerEl || document.getElementById('emergencyToggleBtn')) return;
    const rightSegment = headerEl.querySelector('.header-container > div:last-child');
    if (rightSegment) {
      const btn = document.createElement('a');
      btn.id = 'emergencyToggleBtn';
      btn.href = 'emergency.html';
      btn.className = 'px-2.5 py-1 rounded-lg text-xs font-bold border border-rose-500/40 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20 transition-all flex items-center gap-1';
      btn.setAttribute('aria-label', 'Low-Bandwidth Emergency Mode');
      btn.innerHTML = `<span class="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span> <span>Emergency</span>`;
      rightSegment.insertBefore(btn, rightSegment.firstChild);
    }
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

