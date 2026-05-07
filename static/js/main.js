/**
 * ShopPulse - cross-page wiring for tracking and add-to-cart buttons.
 */
(function () {
  document.addEventListener('DOMContentLoaded', function () {

    // --- Add-to-cart buttons (delegated) -----------------------------
    document.body.addEventListener('click', function (e) {
      const btn = e.target.closest('[data-add-to-cart]');
      if (!btn) return;
      e.preventDefault();
      const qtySel = btn.dataset.qtyFrom;
      let qty = 1;
      if (qtySel) {
        const qEl = document.querySelector(qtySel);
        if (qEl) qty = Math.max(1, parseInt(qEl.value, 10) || 1);
      }
      window.SPCart && SPCart.addToCart({
        product_id: parseInt(btn.dataset.productId, 10),
        sku: btn.dataset.productSku,
        name: btn.dataset.productName,
        slug: btn.dataset.productSlug,
        price: parseFloat(btn.dataset.productPrice),
        image_url: btn.dataset.productImage,
        category: btn.dataset.productCategory,
        quantity: qty
      });
    });

    // --- Product card click tracking ---------------------------------
    document.querySelectorAll('[data-track-product-click]').forEach(el => {
      el.addEventListener('click', () => {
        if (!window.SPAnalytics) return;
        SPAnalytics.trackEvent('product_click', {
          product_id: parseInt(el.dataset.productId, 10),
          product_sku: el.dataset.productSku,
          category: el.dataset.productCategory
        });
      });
    });

    // --- Featured / hero CTA tracking --------------------------------
    document.querySelectorAll('[data-track]').forEach(el => {
      el.addEventListener('click', () => {
        if (!window.SPAnalytics) return;
        const type = el.dataset.track;
        const payload = {};
        if (el.dataset.cta) payload.metadata = { cta: el.dataset.cta };
        if (el.dataset.category) payload.category = el.dataset.category;
        SPAnalytics.trackEvent(type, payload);
      });
    });

    // --- Filter / sort tracking on product list ----------------------
    document.querySelectorAll('[data-filter-name]').forEach(el => {
      el.addEventListener('change', () => {
        if (!window.SPAnalytics) return;
        const name = el.dataset.filterName;
        SPAnalytics.trackEvent(name === 'sort' ? 'sort_used' : 'filter_used', {
          filter_name: name,
          filter_value: el.value
        });
      });
    });

    // --- Product impressions (one event per card per page) ----------
    if (window.SPAnalytics) {
      document.querySelectorAll('[data-track-impression]').forEach(el => {
        SPAnalytics.trackEvent('product_impression', {
          product_id: parseInt(el.dataset.productId, 10),
          product_sku: el.dataset.productSku,
          category: el.dataset.productCategory
        });
      });
    }

    // --- Search submit tracking (forms with name="q") ---------------
    document.querySelectorAll('form').forEach(form => {
      const qInput = form.querySelector('input[name="q"]');
      if (!qInput) return;
      form.addEventListener('submit', () => {
        const q = (qInput.value || '').trim();
        if (q && window.SPAnalytics) {
          SPAnalytics.trackEvent('search_submit', { search_query: q });
        }
      });
    });
  });
})();
