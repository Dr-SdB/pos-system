// ─── Cart helpers ───────────────────────────────────────────────────────────
function getCart() {
  return JSON.parse(localStorage.getItem("pos_cart") || "[]");
}
function saveCart(cart) {
  localStorage.setItem("pos_cart", JSON.stringify(cart));
  updateCartBadge();
}

function addToCart(item) {
  const cart = getCart();
  const existing = cart.find(x => x.variant_id === item.variant_id);
  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({ ...item, quantity: 1, discount_percent: 0 });
  }
  saveCart(cart);
}

function updateCartBadge() {
  const badge = document.querySelector("#cartBadge");
  if (!badge) return;
  const count = getCart().reduce((sum, x) => sum + x.quantity, 0);
  badge.textContent = count;
  badge.classList.toggle("hidden", count === 0);
}

// ─── Toast notification ─────────────────────────────────────────────────────
function showToast(msg, type = "success") {
  const colours = { success: "bg-green-600", error: "bg-red-600", info: "bg-blue-600" };
  const toast = document.createElement("div");
  toast.className = `fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl text-white font-medium shadow-lg
                     transition-all duration-300 opacity-0 translate-y-2 ${colours[type] || colours.success}`;
  toast.textContent = msg;
  document.body.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.remove("opacity-0", "translate-y-2");
  });
  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}

// ─── Fetch & render products ─────────────────────────────────────────────────
async function fetchProducts(params = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`/api/products?${qs}`);
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

function renderProducts(results) {
  const container = document.querySelector("#productsList");
  if (!container) return;
  container.innerHTML = "";

  if (!results.length) {
    container.innerHTML = `<div class="col-span-full text-center text-gray-400 py-12">
      <p class="text-4xl mb-2">🔍</p><p class="text-lg">No products found.</p>
    </div>`;
    return;
  }

  results.forEach(p => {
    const inStock = p.stock > 0;
    const card = document.createElement("div");
    card.className = "bg-white rounded-xl shadow-sm border border-gray-100 p-4 flex flex-col gap-3 hover:shadow-md transition-shadow";

    card.innerHTML = `
      <div class="flex justify-between items-start gap-2">
        <div>
          <h2 class="font-semibold text-gray-800">${p.product_name}</h2>
          <p class="text-xs text-gray-400 mt-0.5">${p.sku}</p>
        </div>
        ${p.martial_art ? `<span class="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full whitespace-nowrap">${p.martial_art}</span>` : ""}
      </div>

      <div class="flex gap-3 text-sm text-gray-600">
        ${p.size ? `<span class="bg-gray-100 px-2 py-0.5 rounded">📐 ${p.size}</span>` : ""}
        ${p.color ? `<span class="bg-gray-100 px-2 py-0.5 rounded">🎨 ${p.color}</span>` : ""}
      </div>

      <div class="flex items-center justify-between">
        <span class="text-xl font-bold text-green-600">€${p.price.toFixed(2)}</span>
        <span class="text-sm font-medium ${inStock ? "text-green-600" : "text-red-500"}">
          ${inStock ? `✓ ${p.stock} in stock` : "✗ Out of stock"}
        </span>
      </div>

      <button class="btn-add-cart w-full py-2 rounded-lg font-medium transition-colors
        ${inStock ? "bg-blue-600 hover:bg-blue-700 text-white" : "bg-gray-200 text-gray-400 cursor-not-allowed"}"
        ${inStock ? "" : "disabled"}>
        ${inStock ? "Add to Cart" : "Out of Stock"}
      </button>
    `;

    if (inStock) {
      card.querySelector(".btn-add-cart").addEventListener("click", () => {
        addToCart({
          variant_id: p.id,
          name: p.product_name,
          sku: p.sku,
          size: p.size,
          color: p.color,
          price: Number(p.price),
        });
        showToast(`${p.product_name} added to cart ✓`);
      });
    }

    container.appendChild(card);
  });
}

// ─── Search page init ─────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  updateCartBadge();

  const input = document.querySelector("#searchInput");
  const filterSize = document.querySelector("#filterSize");
  const filterColor = document.querySelector("#filterColor");
  const filterMartial = document.querySelector("#filterMartial");

  if (!input) return;

  async function runSearch() {
    const params = { search: input.value.trim() };
    if (filterSize?.value && filterSize.value !== "all") params.size = filterSize.value;
    if (filterColor?.value && filterColor.value !== "all") params.color = filterColor.value;
    if (filterMartial?.value && filterMartial.value !== "all") params.martial_art = filterMartial.value;

    try {
      const data = await fetchProducts(params);
      renderProducts(data.results);
    } catch {
      showToast("Failed to load products", "error");
    }
  }

  await runSearch();

  let timer = null;
  input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(runSearch, 250); });
  filterSize?.addEventListener("change", runSearch);
  filterColor?.addEventListener("change", runSearch);
  filterMartial?.addEventListener("change", runSearch);
});
