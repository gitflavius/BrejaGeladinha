// ─── State ─────────────────────────────────────────────────────────────────────
let cart = [];
let selectedBranch = null;
let selectedCategory = 'all';

function cartTotal() {
  return cart.reduce((s, i) => s + i.price * i.qty, 0);
}

function cartCount() {
  return cart.reduce((s, i) => s + i.qty, 0);
}

function setCartLabel() {
  const label = document.getElementById('cart-total-label');
  if (label) {
    label.textContent = `${cartCount()} itens • R$ ${cartTotal().toFixed(2).replace('.', ',')}`;
  }
}

function addToCart(name, price) {
  const existing = cart.find(i => i.name === name);
  if (existing) {
    existing.qty += 1;
  } else {
    cart.push({ name, price: parseFloat(price), qty: 1 });
  }
  setCartLabel();
}

function normalizeCategoryLabel(category) {
  if (category === 'Energeticos') return 'Energéticos';
  return category;
}

function updateCategoryButtons() {
  document.querySelectorAll('.category-btn').forEach(btn => {
    const isActive = btn.dataset.category === selectedCategory;
    btn.classList.toggle('active', isActive);
  });
}

function updateBranchButtons() {
  document.querySelectorAll('.branch-btn').forEach(btn => {
    const isActive = btn.dataset.branch === (selectedBranch === null ? 'all' : String(selectedBranch));
    btn.classList.toggle('active', isActive);
  });
}

function applyFilters() {
  const cards = document.querySelectorAll('.product-card');

  cards.forEach(card => {
    const cardBranch = card.dataset.branch;
    const cardCategory = card.dataset.category;

    const matchesBranch =
      selectedBranch === null ||
      cardBranch === String(selectedBranch) ||
      cardBranch === 'none';

    const matchesCategory =
      selectedCategory === 'all' ||
      cardCategory === selectedCategory;

    card.style.display = matchesBranch && matchesCategory ? '' : 'none';
  });

  document.querySelectorAll('.product-section').forEach(section => {
    const visibleCards = [...section.querySelectorAll('.product-card')]
      .filter(card => card.style.display !== 'none');

    section.style.display = visibleCards.length ? '' : 'none';
  });

  const branchLabel = document.getElementById('branch-label');
  if (branchLabel) {
    const btn = document.querySelector(`.branch-btn[data-branch="${selectedBranch === null ? 'all' : selectedBranch}"]`);
    branchLabel.textContent = btn ? btn.dataset.branchName : 'todas as filiais';
  }

  const title = document.getElementById('products-title');
  if (title) {
    title.textContent = selectedCategory === 'all'
      ? 'Produtos'
      : normalizeCategoryLabel(selectedCategory);
  }

  updateBranchButtons();
  updateCategoryButtons();
}

async function checkout(customerName) {
  const items = cart.map(i => ({ name: i.name, price: i.price, qty: i.qty }));

  const res = await fetch('/api/orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer: customerName,
      items,
      branch_id: selectedBranch
    }),
  });

  const data = await res.json();

  const pixRes = await fetch('/api/pix-preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ total: data.total, order_id: data.order_id }),
  });

  const pixData = await pixRes.json();

  const pixCode = document.getElementById('pix-code');
  const pixOrderLabel = document.getElementById('pix-order-label');

  if (pixCode) pixCode.value = pixData.pix_code;
  if (pixOrderLabel) pixOrderLabel.textContent = `Pedido #${pixData.order_id}`;

  const pixModal = document.getElementById('pix-modal');
  if (pixModal) pixModal.classList.add('open');
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.branch-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      selectedBranch = btn.dataset.branch === 'all' ? null : parseInt(btn.dataset.branch, 10);

      const hiddenBranch = document.getElementById('selected-branch-id');
      const branchLabel = document.getElementById('selected-branch-label');

      if (hiddenBranch) hiddenBranch.value = selectedBranch || '';
      if (branchLabel) {
        branchLabel.textContent = selectedBranch ? `Filial: ${btn.dataset.branchName}` : '';
      }

      applyFilters();
    });
  });

document.querySelectorAll('.category-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    selectedCategory = btn.dataset.category;
    
    // ✅ ADICIONE ESTAS LINHAS:
    btn.scrollIntoView({ 
      behavior: 'smooth',
      block: 'nearest',
      inline: 'center'
    });
    
    applyFilters();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
});


  document.querySelectorAll('.add-item').forEach(btn => {
    btn.addEventListener('click', () => {
      addToCart(btn.dataset.name, btn.dataset.price);
    });
  });

  const checkoutBtn = document.getElementById('checkout-btn');
  if (checkoutBtn) {
    checkoutBtn.addEventListener('click', () => {
      if (cart.length === 0) {
        alert('Adicione itens ao carrinho primeiro.');
        return;
      }
      document.getElementById('checkout-modal').classList.add('open');
    });
  }

  const openCart = document.getElementById('open-cart');
  if (openCart) {
    openCart.addEventListener('click', () => {
      if (cart.length === 0) {
        alert('Adicione itens ao carrinho primeiro.');
        return;
      }
      document.getElementById('checkout-modal').classList.add('open');
    });
  }

  const confirmForm = document.getElementById('checkout-form');
  if (confirmForm) {
    confirmForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('customer-name').value.trim() || 'Cliente';
      document.getElementById('checkout-modal').classList.remove('open');
      await checkout(name);
    });
  }

  const closePix = document.getElementById('close-pix');
  if (closePix) {
    const pixModal = document.getElementById('pix-modal');
    closePix.addEventListener('click', () => {
      pixModal.classList.remove('open');
      cart = [];
      setCartLabel();
    });
  }

  const copyBtn = document.getElementById('copy-pix-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const code = document.getElementById('pix-code');
      if (code) {
        navigator.clipboard.writeText(code.value);
        copyBtn.textContent = 'Copiado!';
      }
    });
  }

  setCartLabel();
  applyFilters();
});