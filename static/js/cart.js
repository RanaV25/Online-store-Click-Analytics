/**
 * ShopPulse - LocalStorage cart.
 *
 * Cart shape:
 *   { items: [ {product_id, sku, name, slug, price, quantity, image_url, category} ],
 *     updated_at: <ISO string> }
 *
 * Every mutation also fires a cart-event back to the server (best-effort) so
 * future Azure pipelines can replay user behaviour.
 */
(function () {
  const KEY = 'sp_cart_v1';

  function nowIso() { return new Date().toISOString(); }

  function getCart() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return { items: [], updated_at: nowIso() };
      const parsed = JSON.parse(raw);
      if (!parsed.items) parsed.items = [];
      return parsed;
    } catch (e) {
      return { items: [], updated_at: nowIso() };
    }
  }

  function saveCart(cart) {
    cart.updated_at = nowIso();
    localStorage.setItem(KEY, JSON.stringify(cart));
    updateCartBadge();
  }

  function findIndex(cart, productId) {
    return cart.items.findIndex(i => String(i.product_id) === String(productId));
  }

  function getCartTotal() {
    const cart = getCart();
    return cart.items.reduce((s, it) => s + (Number(it.price) || 0) * (Number(it.quantity) || 0), 0);
  }

  function getCartItemsCount() {
    const cart = getCart();
    return cart.items.reduce((s, it) => s + (Number(it.quantity) || 0), 0);
  }

  function postCartEvent(eventType, item, qty) {
    if (!window.SPAnalytics) return;
    const payload = {
      session_id: SPAnalytics.getSessionId(),
      event_type: eventType,
      product_id: item ? item.product_id : null,
      product_name: item ? item.name : null,
      quantity: qty,
      unit_price: item ? item.price : null,
      cart_total: getCartTotal()
    };
    try {
      navigator.sendBeacon
        ? navigator.sendBeacon('/api/cart-event', new Blob([JSON.stringify(payload)], { type: 'application/json' }))
        : fetch('/api/cart-event', { method: 'POST', headers: { 'Content-Type': 'application/json' },
                                     body: JSON.stringify(payload), keepalive: true });
    } catch (e) { /* silent */ }

    // Mirror to click stream too so funnel queries are simple.
    SPAnalytics.trackEvent(eventType, {
      product_id: item ? item.product_id : null,
      product_sku: item ? item.sku : null,
      category: item ? item.category : null,
      cart_value: getCartTotal(),
      cart_items_count: getCartItemsCount()
    });
  }

  function addToCart(product) {
    const cart = getCart();
    const idx = findIndex(cart, product.product_id);
    if (idx >= 0) {
      cart.items[idx].quantity += (product.quantity || 1);
    } else {
      cart.items.push({
        product_id: product.product_id,
        sku: product.sku,
        name: product.name,
        slug: product.slug,
        price: Number(product.price),
        quantity: Number(product.quantity || 1),
        image_url: product.image_url,
        category: product.category
      });
    }
    saveCart(cart);
    postCartEvent('add_to_cart', cart.items[findIndex(cart, product.product_id)], product.quantity || 1);
    flashToast(`${product.name} added to cart`);
  }

  function removeFromCart(productId) {
    const cart = getCart();
    const idx = findIndex(cart, productId);
    if (idx < 0) return;
    const removed = cart.items[idx];
    cart.items.splice(idx, 1);
    saveCart(cart);
    postCartEvent('remove_from_cart', removed, removed.quantity);
    renderCart();
  }

  function updateQuantity(productId, quantity) {
    const cart = getCart();
    const idx = findIndex(cart, productId);
    if (idx < 0) return;
    quantity = Math.max(1, Number(quantity) || 1);
    cart.items[idx].quantity = quantity;
    saveCart(cart);
    postCartEvent('update_quantity', cart.items[idx], quantity);
    renderCart();
  }

  function clearCart() {
    const cart = getCart();
    if (!cart.items.length) return;
    saveCart({ items: [], updated_at: nowIso() });
    postCartEvent('clear_cart', null, 0);
    renderCart();
  }

  function updateCartBadge() {
    const badge = document.getElementById('cartBadge');
    if (!badge) return;
    const n = getCartItemsCount();
    badge.textContent = n;
    badge.style.display = n > 0 ? 'inline-block' : 'none';
  }

  function rupees(n) { return '₹' + (Math.round(Number(n) || 0)); }

  function renderCart() {
    const root = document.getElementById('cartRoot');
    const summaryRoot = document.getElementById('cartSummary');
    if (!root && !summaryRoot) return;
    const cart = getCart();

    if (root) {
      if (!cart.items.length) {
        root.innerHTML = `
          <div class="cart-empty">
            <i class="bi bi-cart-x display-4"></i>
            <p class="mt-3">Your cart is empty.</p>
            <a href="/products" class="btn btn-dark btn-sm">Continue shopping</a>
          </div>`;
      } else {
        root.innerHTML = cart.items.map(it => `
          <div class="d-flex align-items-center border-bottom py-3 gap-3">
            <img src="${it.image_url}" alt="" style="width:64px;height:64px;object-fit:cover;border-radius:8px;">
            <div class="flex-grow-1">
              <div class="fw-semibold">${it.name}</div>
              <div class="small text-muted">${it.category} &middot; ${rupees(it.price)} each</div>
            </div>
            <div class="d-flex align-items-center gap-2">
              <input type="number" min="1" value="${it.quantity}" class="form-control form-control-sm" style="width:80px;"
                     data-cart-qty="${it.product_id}">
              <div class="fw-semibold" style="min-width:70px;text-align:right;">${rupees(it.price * it.quantity)}</div>
              <button class="btn btn-sm btn-outline-danger" data-cart-remove="${it.product_id}">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </div>
        `).join('');

        root.querySelectorAll('[data-cart-qty]').forEach(el => {
          el.addEventListener('change', e => updateQuantity(el.dataset.cartQty, e.target.value));
        });
        root.querySelectorAll('[data-cart-remove]').forEach(el => {
          el.addEventListener('click', () => removeFromCart(el.dataset.cartRemove));
        });
      }
    }

    if (summaryRoot) {
      if (!cart.items.length) {
        summaryRoot.innerHTML = `<div class="text-muted small">Cart is empty.</div>`;
      } else {
        summaryRoot.innerHTML = `
          <ul class="list-unstyled mb-2">
            ${cart.items.map(it => `
              <li class="d-flex justify-content-between small">
                <span>${it.name} × ${it.quantity}</span>
                <span>${rupees(it.price * it.quantity)}</span>
              </li>`).join('')}
          </ul>
          <hr class="my-2">
          <div class="d-flex justify-content-between fw-semibold">
            <span>Total (${getCartItemsCount()} items)</span>
            <span>${rupees(getCartTotal())}</span>
          </div>`;
      }
    }

    const totalEl = document.getElementById('cartTotal');
    if (totalEl) totalEl.textContent = rupees(getCartTotal());
    const countEl = document.getElementById('cartCount');
    if (countEl) countEl.textContent = getCartItemsCount();
  }

  function flashToast(msg) {
    let host = document.getElementById('spToastHost');
    if (!host) {
      host = document.createElement('div');
      host.id = 'spToastHost';
      host.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:1080;';
      document.body.appendChild(host);
    }
    const el = document.createElement('div');
    el.className = 'toast align-items-center text-bg-dark border-0 show mb-2';
    el.role = 'alert';
    el.innerHTML = `<div class="d-flex"><div class="toast-body">${msg}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto"></button></div>`;
    host.appendChild(el);
    el.querySelector('.btn-close').onclick = () => el.remove();
    setTimeout(() => el.remove(), 2500);
  }

  window.SPCart = {
    getCart, saveCart, addToCart, removeFromCart, updateQuantity, clearCart,
    getCartTotal, getCartItemsCount, renderCart, updateCartBadge
  };

  document.addEventListener('DOMContentLoaded', () => {
    updateCartBadge();
    renderCart();
  });
})();
