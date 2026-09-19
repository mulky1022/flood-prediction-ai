/**
 * Phase 15 — WhatsApp & SMS Alert Subscription Frontend Component.
 * 
 * Provides interactive subscription UI for mobile users to receive SMS/WhatsApp flood risk alerts
 * for their selected station in English, Sinhala, or Tamil.
 */

import { api } from './api.js';
import { i18n } from './i18n.js';

export class NotificationSubComponent {
  constructor(options = {}) {
    this.containerId = options.containerId || 'notification-sub-container';
    this.locationId = options.locationId || 'RATNAPURA_001';
  }

  render(containerEl = null) {
    const container = containerEl || document.getElementById(this.containerId);
    if (!container) return;

    const locName = i18n.getStationName(this.locationId, this.locationId);

    container.innerHTML = `
      <div class="rounded-2xl border border-slate-700 bg-slate-800/80 p-5 text-slate-100 shadow-xl max-w-md mx-auto">
        <div class="flex items-center gap-2 mb-3">
          <svg class="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
          </svg>
          <div>
            <h3 class="font-extrabold text-base text-white">Get WhatsApp / SMS Flood Alerts</h3>
            <p class="text-xs text-slate-400">Direct early warnings for <span class="font-semibold text-sky-400">${locName}</span></p>
          </div>
        </div>

        <form id="sub-form" class="space-y-3">
          <!-- Channel Selection -->
          <div>
            <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">Notification Channel</label>
            <div class="grid grid-cols-2 gap-2">
              <label class="flex items-center gap-2 p-2.5 rounded-xl border border-slate-700 bg-slate-900/60 cursor-pointer hover:border-emerald-500/50">
                <input type="radio" name="sub-channel" value="whatsapp" checked class="text-emerald-500 focus:ring-emerald-500">
                <span class="text-xs font-bold text-emerald-400">WhatsApp</span>
              </label>
              <label class="flex items-center gap-2 p-2.5 rounded-xl border border-slate-700 bg-slate-900/60 cursor-pointer hover:border-sky-500/50">
                <input type="radio" name="sub-channel" value="sms" class="text-sky-500 focus:ring-sky-500">
                <span class="text-xs font-bold text-sky-400">SMS</span>
              </label>
            </div>
          </div>

          <!-- Destination Phone Number -->
          <div>
            <label for="sub-phone" class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">Mobile Phone Number</label>
            <input type="tel" id="sub-phone" placeholder="0771234567 or +94771234567" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white font-mono placeholder-slate-500 focus:border-emerald-500 focus:outline-none">
          </div>

          <!-- Language Selection -->
          <div>
            <label for="sub-lang" class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">Preferred Language</label>
            <select id="sub-lang" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs font-bold text-slate-200 focus:border-emerald-500 focus:outline-none">
              <option value="en">English</option>
              <option value="si">සිංහල (Sinhala)</option>
              <option value="ta">தமிழ் (Tamil)</option>
            </select>
          </div>

          <!-- Status Message -->
          <div id="sub-msg" class="hidden text-xs p-3 rounded-xl"></div>

          <!-- Submit Button -->
          <button type="submit" id="sub-submit-btn" class="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-black text-sm active:scale-95 transition-all shadow-lg flex items-center justify-center gap-2">
            Subscribe to Alerts
          </button>
        </form>
      </div>
    `;

    const form = container.querySelector('#sub-form');
    if (form) {
      form.addEventListener('submit', (e) => this.handleSubscribe(e));
    }
  }

  async handleSubscribe(e) {
    e.preventDefault();
    const phoneInput = document.getElementById('sub-phone');
    const langSelect = document.getElementById('sub-lang');
    const msgBox = document.getElementById('sub-msg');
    const submitBtn = document.getElementById('sub-submit-btn');

    const channelEl = document.querySelector('input[name="sub-channel"]:checked');
    const channel = channelEl ? channelEl.value : 'whatsapp';
    const phone = phoneInput ? phoneInput.value.trim() : '';
    const lang = langSelect ? langSelect.value : 'en';

    if (!phone) return;

    submitBtn.disabled = true;
    submitBtn.innerText = 'Subscribing...';

    try {
      const response = await fetch('/api/v1/notifications/subscriptions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          location_id: this.locationId,
          channel: channel,
          destination: phone,
          language: lang,
          minimum_risk_level: 'HIGH'
        })
      });

      const resData = await response.json();

      if (response.ok && resData.status === 'success') {
        msgBox.className = 'text-xs p-3 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 block';
        msgBox.innerHTML = `<strong>Subscribed!</strong> Alerts will be sent via ${channel.toUpperCase()} to ${resData.subscription.destination_masked}.`;
        form.reset();
      } else {
        const errorMsg = resData.detail ? (typeof resData.detail === 'string' ? resData.detail : resData.detail.message) : 'Subscription failed.';
        msgBox.className = 'text-xs p-3 rounded-xl bg-rose-500/20 text-rose-300 border border-rose-500/40 block';
        msgBox.innerText = errorMsg;
      }
    } catch (err) {
      msgBox.className = 'text-xs p-3 rounded-xl bg-rose-500/20 text-rose-300 border border-rose-500/40 block';
      msgBox.innerText = 'Network error during subscription. Please try again.';
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerText = 'Subscribe to Alerts';
    }
  }
}
