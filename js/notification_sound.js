/**
 * Sri Lanka FloodWatch — Hydrological Warning Sound & Ringtone Engine
 * Synthesizes high-clarity emergency warning tones and chimes using the Web Audio API.
 * Ensures 100% native browser audio playback without relying on external MP3 asset downloads.
 */

class NotificationSoundEngine {
  constructor() {
    this.audioCtx = null;
    this.isUnlocked = false;
  }

  /**
   * Initializes or resumes the AudioContext upon user gesture
   */
  initContext() {
    if (!this.audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        this.audioCtx = new AudioContextClass();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
    this.isUnlocked = true;
    return this.audioCtx;
  }

  /**
   * Plays a distinct alert tone based on severity
   * @param {'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW' | 'CHIME'} severity 
   */
  async playAlertTone(severity = 'HIGH') {
    try {
      const ctx = this.initContext();
      if (!ctx) return;

      const norm = (severity || '').toUpperCase();

      if (norm === 'CRITICAL') {
        // High-urgency dual-tone siren pulse (880Hz -> 1175Hz oscillating)
        this.playSiren(ctx, 3, 880, 1175);
      } else if (norm === 'HIGH') {
        // Urgent 3-beep warning chime (750Hz)
        this.playBeeps(ctx, 3, 750, 0.15, 0.08);
      } else if (norm === 'MODERATE') {
        // 2-tone melodic advisory chime (523Hz -> 659Hz)
        this.playTwoToneChime(ctx, 523.25, 659.25);
      } else {
        // Subtle confirmation chime (440Hz -> 880Hz ascending)
        this.playConfirmationChime(ctx);
      }
    } catch (e) {
      console.warn('[SoundEngine] Could not play notification audio:', e);
    }
  }

  /**
   * Emergency pulsing siren for CRITICAL alerts
   */
  playSiren(ctx, pulses = 3, freqLow = 700, freqHigh = 1100) {
    const now = ctx.currentTime;
    for (let i = 0; i < pulses; i++) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sawtooth';
      const startTime = now + i * 0.45;
      const midTime = startTime + 0.22;
      const endTime = startTime + 0.44;

      osc.frequency.setValueAtTime(freqLow, startTime);
      osc.frequency.exponentialRampToValueAtTime(freqHigh, midTime);
      osc.frequency.exponentialRampToValueAtTime(freqLow, endTime);

      gain.gain.setValueAtTime(0, startTime);
      gain.gain.linearRampToValueAtTime(0.3, startTime + 0.05);
      gain.gain.setValueAtTime(0.3, endTime - 0.05);
      gain.gain.linearRampToValueAtTime(0, endTime);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(startTime);
      osc.stop(endTime);
    }
  }

  /**
   * Rhythmic warning beeps for HIGH alerts
   */
  playBeeps(ctx, count = 3, freq = 750, duration = 0.15, gap = 0.08) {
    const now = ctx.currentTime;
    for (let i = 0; i < count; i++) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now + i * (duration + gap));

      const startTime = now + i * (duration + gap);
      const endTime = startTime + duration;

      gain.gain.setValueAtTime(0, startTime);
      gain.gain.linearRampToValueAtTime(0.35, startTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, endTime);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(startTime);
      osc.stop(endTime);
    }
  }

  /**
   * 2-tone melodic chime for MODERATE advisories
   */
  playTwoToneChime(ctx, freq1 = 523.25, freq2 = 659.25) {
    const now = ctx.currentTime;
    [freq1, freq2].forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(freq, now + idx * 0.18);

      const startTime = now + idx * 0.18;
      const endTime = startTime + 0.28;

      gain.gain.setValueAtTime(0, startTime);
      gain.gain.linearRampToValueAtTime(0.25, startTime + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.001, endTime);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(startTime);
      osc.stop(endTime);
    });
  }

  /**
   * Smooth ascending confirmation chime when enabling notifications
   */
  playConfirmationChime(ctx) {
    const now = ctx.currentTime;
    const notes = [523.25, 659.25, 783.99]; // C5, E5, G5
    notes.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now + idx * 0.09);

      const startTime = now + idx * 0.09;
      const endTime = startTime + 0.25;

      gain.gain.setValueAtTime(0, startTime);
      gain.gain.linearRampToValueAtTime(0.2, startTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, endTime);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(startTime);
      osc.stop(endTime);
    });
  }
}

export const notificationSound = new NotificationSoundEngine();

// Auto-unlock audio context on first user click or tap anywhere
if (typeof window !== 'undefined') {
  const unlockListener = () => {
    notificationSound.initContext();
    window.removeEventListener('click', unlockListener);
    window.removeEventListener('touchstart', unlockListener);
  };
  window.addEventListener('click', unlockListener, { passive: true });
  window.addEventListener('touchstart', unlockListener, { passive: true });
}
