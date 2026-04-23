function getCart() { return JSON.parse(localStorage.getItem("pos_cart") || "[]"); }
function saveCart(cart) { localStorage.setItem("pos_cart", JSON.stringify(cart)); }
function clearCart() { localStorage.removeItem("pos_cart"); }
function money(n) { return (Number(n) || 0).toFixed(2); }

function showToast(msg, type = "success") {
  const colours = { success: "bg-green-600", error: "bg-red-600", info: "bg-blue-600" };
  const toast = document.createElement("div");
  toast.className = `fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl text-white font-medium shadow-lg
                     transition-all duration-300 opacity-0 translate-y-2 ${colours[type] || colours.success}`;
  toast.textContent = msg;
  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.remove("opacity-0", "translate-y-2"));
  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function renderCart() {
  const cart = getCart();
  const list = document.querySelector("#cartList");
  const subtotalEl = document.querySelector("#subtotal");
  const totalEl = document.querySelector("#total");
  const discountEl = document.querySelector("#discountLine");
  const changeEl = document.querySelector("#changeDisplay");

  if (!list) return;

  list.innerHTML = "";

  if (!cart.length) {
    list.innerHTML = `<div class="text-center text-gray-400 py-16">
      <p class="text-5xl mb-3">🛒</p>
      <p class="text-lg font-medium">Cart is empty</p>
      <a href="/" class="mt-3 inline-block text-blue-600 hover:underline text-sm">← Browse products</a>
    </div>`;
    subtotalEl && (subtotalEl.textContent = "0.00");
    totalEl && (totalEl.textContent = "0.00");
    discountEl && (discountEl.style.display = "none");
    changeEl && (changeEl.textContent = "0.00");
    return;
  }

  let subtotal = 0, discountTotal = 0;

  cart.forEach(item => {
    const price = Number(item.price) || 0;
    const quantity = Number(item.quantity) || 1;
    const dp = Number(item.discount_percent) || 0;
    const lineGross = price * quantity;
    const lineDiscount = lineGross * (dp / 100);
    const lineNet = lineGross - lineDiscount;
    subtotal += lineGross;
    discountTotal += lineDiscount;

    const row = document.createElement("div");
    row.className = "border border-gray-100 rounded-xl p-4 flex flex-col gap-3";
    row.innerHTML = `
      <div class="flex justify-between items-start gap-2">
        <div>
          <p class="font-semibold text-gray-800">${item.name}</p>
          <p class="text-xs text-gray-400">${item.sku}${item.size ? " · " + item.size : ""}${item.color ? " · " + item.color : ""}</p>
        </div>
        <button class="text-gray-300 hover:text-red-500 transition-colors text-lg leading-none" data-remove title="Remove">✕</button>
      </div>

      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center border rounded-lg overflow-hidden">
          <button class="px-3 py-1.5 bg-gray-50 hover:bg-gray-100 font-bold text-gray-600 transition-colors" data-dec>−</button>
          <span class="w-10 text-center font-medium text-sm">${quantity}</span>
          <button class="px-3 py-1.5 bg-gray-50 hover:bg-gray-100 font-bold text-gray-600 transition-colors" data-inc>+</button>
        </div>
        <div class="flex items-center gap-2 text-sm text-gray-500">
          <span>Discount</span>
          <input data-discount type="number" min="0" max="100" value="${dp}"
            class="w-16 p-1.5 border rounded-lg text-center text-sm focus:outline-none focus:ring-2 focus:ring-blue-300" />
          <span>%</span>
        </div>
        <div class="text-right">
          ${dp > 0 ? `<p class="text-xs text-gray-400 line-through">€${money(lineGross)}</p>` : ""}
          <p class="font-bold text-gray-800">€${money(lineNet)}</p>
        </div>
      </div>
    `;

    row.querySelector("[data-inc]").addEventListener("click", () => {
      const c = getCart(); const t = c.find(x => x.variant_id === item.variant_id);
      if (t) { t.quantity += 1; saveCart(c); renderCart(); }
    });
    row.querySelector("[data-dec]").addEventListener("click", () => {
      const c = getCart(); const t = c.find(x => x.variant_id === item.variant_id);
      if (t) { t.quantity = Math.max(1, t.quantity - 1); saveCart(c); renderCart(); }
    });
    row.querySelector("[data-remove]").addEventListener("click", () => {
      saveCart(getCart().filter(x => x.variant_id !== item.variant_id)); renderCart();
    });
    row.querySelector("[data-discount]").addEventListener("input", e => {
      const c = getCart(); const t = c.find(x => x.variant_id === item.variant_id);
      if (t) { t.discount_percent = Math.max(0, Math.min(100, Number(e.target.value || 0))); saveCart(c); renderCart(); }
    });

    list.appendChild(row);
  });

  const total = subtotal - discountTotal;
  if (subtotalEl) subtotalEl.textContent = money(subtotal);
  if (totalEl) totalEl.textContent = money(total);

  if (discountEl) {
    discountEl.style.display = discountTotal > 0 ? "flex" : "none";
    const dEl = document.querySelector("#discountAmount");
    if (dEl) dEl.textContent = money(discountTotal);
  }

  updateChange();
}

function updateChange() {
  const cart = getCart();
  const total = cart.reduce((sum, item) => {
    const gross = item.price * item.quantity;
    return sum + gross - gross * ((item.discount_percent || 0) / 100);
  }, 0);

  const paid = Number(document.querySelector("#amountPaid")?.value || 0);
  const change = Math.max(0, paid - total);
  const changeEl = document.querySelector("#changeDisplay");
  if (changeEl) changeEl.textContent = money(change);
}

// ─── Payment method toggle ────────────────────────────────────────────────────
function initPaymentToggle() {
  document.querySelectorAll(".payment-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".payment-btn").forEach(b => {
        b.classList.remove("ring-2", "ring-offset-1", "ring-blue-500", "opacity-100");
        b.classList.add("opacity-60");
      });
      btn.classList.add("ring-2", "ring-offset-1", "ring-blue-500", "opacity-100");
      btn.classList.remove("opacity-60");
      btn.querySelector("input").checked = true;
    });
  });
  // Activate default
  document.querySelector(".payment-btn input:checked")
    ?.closest(".payment-btn")?.click();
}

// ─── Checkout ────────────────────────────────────────────────────────────────
async function checkout() {
  const cart = getCart();
  if (!cart.length) { showToast("Cart is empty", "error"); return; }

  const btn = document.querySelector("#btnCheckout");
  btn.disabled = true;
  btn.textContent = "Processing…";

  const payment = document.querySelector("input[name='payment']:checked")?.value || "Dinheiro";
  const amountPaid = Number(document.querySelector("#amountPaid")?.value || 0);

  const payload = {
    payment_method: payment,
    amount_paid: amountPaid,
    items: cart.map(x => ({
      variant_id: x.variant_id,
      quantity: x.quantity,
      discount_percent: x.discount_percent || 0,
    })),
  };

  try {
    const res = await fetch("/api/sale", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok || data.error) {
      showToast("Error: " + (data.error || "Unknown error"), "error");
      return;
    }

    clearCart();
    renderCart();

    // Show receipt modal
    const changeText = data.change > 0 ? `\nChange: €${data.change.toFixed(2)}` : "";
    showReceiptModal(data);

  } catch (err) {
    showToast("Network error – could not complete sale", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Complete Sale";
  }
}

function showReceiptModal(data) {
  const modal = document.createElement("div");
  modal.className = "fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4";
  modal.innerHTML = `
    <div class="bg-white rounded-2xl shadow-2xl p-8 max-w-sm w-full text-center space-y-4">
      <div class="text-5xl">✅</div>
      <h2 class="text-2xl font-bold text-gray-800">Sale Complete!</h2>
      <p class="text-gray-500 text-sm">Sale #${data.sale_id} · ${data.payment_method}</p>
      <div class="bg-gray-50 rounded-xl p-4 space-y-1 text-sm text-left">
        <div class="flex justify-between"><span class="text-gray-500">Subtotal</span><span>€${data.subtotal.toFixed(2)}</span></div>
        ${data.discount_total > 0 ? `<div class="flex justify-between text-red-500"><span>Discount</span><span>−€${data.discount_total.toFixed(2)}</span></div>` : ""}
        <div class="flex justify-between font-bold text-base border-t pt-1 mt-1"><span>Total</span><span>€${data.total.toFixed(2)}</span></div>
        ${data.amount_paid > 0 ? `<div class="flex justify-between text-gray-500"><span>Paid</span><span>€${data.amount_paid.toFixed(2)}</span></div>` : ""}
        ${data.change > 0 ? `<div class="flex justify-between text-green-600 font-medium"><span>Change</span><span>€${data.change.toFixed(2)}</span></div>` : ""}
      </div>
      <button id="closeReceipt" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-xl transition-colors">
        New Sale
      </button>
    </div>
  `;
  document.body.appendChild(modal);
  document.querySelector("#closeReceipt").addEventListener("click", () => modal.remove());
}

document.addEventListener("DOMContentLoaded", () => {
  renderCart();
  initPaymentToggle();
  document.querySelector("#btnCheckout")?.addEventListener("click", checkout);
  document.querySelector("#amountPaid")?.addEventListener("input", updateChange);
});
