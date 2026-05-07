/**
 * ShopPulse - Lightweight clickstream client.
 *
 * Identity:
 *   - user_id   : anonymous, persisted across sessions (LocalStorage).
 *   - session_id: rotates after 30 minutes of inactivity.
 *
 * Transport: navigator.sendBeacon when available; fetch keepalive otherwise.
 * Failures are silent so the storefront UX is never blocked by analytics.
 *
 * MLOps note: every event captured here would, in production, be forwarded
 * to Azure Event Hubs and persisted to ADLS Gen2 as the raw input layer for
 * the demand-prediction model.
 */
(function () {
  const SID_KEY = 'sp_session_id';
  const UID_KEY = 'sp_user_id';
  const SID_TS_KEY = 'sp_session_ts';
  const SESSION_IDLE_MS = 30 * 60 * 1000; // 30 minutes

  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function getAnonymousUserId() {
    let uid = localStorage.getItem(UID_KEY);
    if (!uid) { uid = uuid(); localStorage.setItem(UID_KEY, uid); }
    return uid;
  }

  function getSessionId() {
    const now = Date.now();
    const ts = parseInt(localStorage.getItem(SID_TS_KEY) || '0', 10);
    let sid = localStorage.getItem(SID_KEY);
    if (!sid || (now - ts) > SESSION_IDLE_MS) {
      sid = uuid();
      localStorage.setItem(SID_KEY, sid);
    }
    localStorage.setItem(SID_TS_KEY, String(now));
    return sid;
  }

  function detectDeviceType() {
    const ua = navigator.userAgent || '';
    if (/Tablet|iPad/i.test(ua)) return 'tablet';
    if (/Mobi|Android|iPhone/i.test(ua)) return 'mobile';
    return 'desktop';
  }

  function detectBrowser() {
    const ua = navigator.userAgent || '';
    if (/Edg\//.test(ua)) return 'Edge';
    if (/Chrome\//.test(ua) && !/Chromium/.test(ua)) return 'Chrome';
    if (/Firefox\//.test(ua)) return 'Firefox';
    if (/Safari\//.test(ua) && !/Chrome\//.test(ua)) return 'Safari';
    return 'Other';
  }

  function getTrafficSource() {
    try {
      const params = new URLSearchParams(window.location.search);
      const utm = params.get('utm_source');
      if (utm) return utm;
      if (document.referrer) {
        try { return new URL(document.referrer).hostname || 'referral'; }
        catch (e) { return 'referral'; }
      }
      return 'direct';
    } catch (e) { return 'direct'; }
  }

  function send(payload) {
    try {
      const body = JSON.stringify(payload);
      if (navigator.sendBeacon) {
        const blob = new Blob([body], { type: 'application/json' });
        navigator.sendBeacon('/api/track-event', blob);
      } else {
        fetch('/api/track-event', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: body,
          keepalive: true
        }).catch(() => {});
      }
    } catch (e) { /* silent */ }
  }

  function trackEvent(eventType, payload) {
    payload = payload || {};
    const base = {
      event_id: uuid(),
      event_type: eventType,
      session_id: getSessionId(),
      user_id: getAnonymousUserId(),
      page_url: window.location.pathname + window.location.search,
      page_title: document.title,
      referrer: document.referrer || '',
      device_type: detectDeviceType(),
      browser: detectBrowser(),
      traffic_source: getTrafficSource()
    };
    send(Object.assign(base, payload));
  }

  function trackPageView() {
    trackEvent('page_view', {});
  }

  window.SPAnalytics = {
    getSessionId, getAnonymousUserId, trackEvent, trackPageView,
    detectDeviceType, getTrafficSource
  };

  document.addEventListener('DOMContentLoaded', trackPageView);
})();
