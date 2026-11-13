const API = (window.EDITH_API_BASE || (window.location.port === "5500" ? "http://127.0.0.1:8000/api/v1" : "/api/v1")).replace(/\/$/, "");

const state = {
  token: null,
  user: null,
  groupCode: "EDITH-TRIP-01",
  group: null,
  members: [],
  expenses: [],
  balances: null,
  fundSummary: null,
  myContributions: [],
  allContributions: [],
  fundTransactions: [],
  showAllMembersSchedule: false,
};

const $ = (id) => document.getElementById(id);
const money = (n) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(n || 0));
const dateToday = () => new Date().toISOString().slice(0, 10);

function headers() {
  return {
    "Content-Type": "application/json",
    ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
  };
}

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: { ...headers(), ...(options.headers || {}) },
  });
  const data = await res.json().catch(() => ({ detail: "Unexpected server response" }));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2800);
}

function initials(name) {
  return (name || "E").trim().split(/\s+/).map(x => x[0]).join("").slice(0, 2).toUpperCase();
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function showView(name) {
  document.querySelectorAll(".view").forEach(x => x.classList.remove("active-view"));
  $(`view-${name}`).classList.add("active-view");
  document.querySelectorAll(".nav-link").forEach(x => x.classList.toggle("active", x.dataset.view === name));
  
  const titles = {
    overview: ["DASHBOARD", "Overview"],
    fund: ["SAVINGS LEDGER", "Trip Fund"],
    expenses: ["EXPENSE SPLITTER", "Split Expenses"],
    trip: ["TRAVEL PLAN", "Trip Itinerary"],
  };
  
  $("page-kicker").textContent = titles[name][0];
  $("page-title").textContent = titles[name][1];
  
  if (name === "fund") refreshFund();
  if (name === "expenses") refreshExpenses();
  if (name === "trip") renderTrip();
}

function logout() {
  sessionStorage.clear();
  state.token = null;
  state.user = null;
  $("app-shell").classList.add("hidden");
  $("login-screen").classList.remove("hidden");
}

function loginSuccess(data) {
  state.token = data.access_token;
  state.user = data.user;
  sessionStorage.setItem("edith_token", state.token);
  sessionStorage.setItem("edith_user", JSON.stringify(state.user));
  
  $("login-screen").classList.add("hidden");
  $("app-shell").classList.remove("hidden");
  $("user-name").textContent = state.user.name;
  $("user-role").textContent = state.user.role === "admin" ? "Administrator" : "Crew Member";
  $("user-avatar").textContent = initials(state.user.name);

  // Show admin specific controls
  const isAdmin = state.user.role === "admin";
  $("admin-collect-btn")?.classList.toggle("hidden", !isAdmin);
  $("open-disbursement-modal")?.classList.toggle("hidden", !isAdmin);
  $("toggle-all-contributions-btn")?.classList.toggle("hidden", !isAdmin);
  $("audit-btn")?.classList.toggle("hidden", !isAdmin);

  loadApp();
}

async function loadApp() {
  try {
    const groups = await api("/groups/mine");
    const group = groups.groups.find(g => g.group_code === state.groupCode) || groups.groups[0];
    if (!group) {
      toast("You are not assigned to a trip group yet.");
      return;
    }
    state.group = group;
    state.groupCode = group.group_code;
    $("group-code-label").textContent = state.groupCode;
    if ($("mobile-group-code")) $("mobile-group-code").textContent = state.groupCode;

    const [summary, members] = await Promise.all([
      api(`/groups/${encodeURIComponent(state.groupCode)}/summary`),
      api(`/groups/${encodeURIComponent(state.groupCode)}/members`),
    ]);

    state.group = summary.group;
    state.members = members.members;

    populateDropdowns();

    await Promise.all([
      refreshFund(),
      refreshExpenses(),
    ]);

    renderOverview();
    renderTrip();
  } catch (e) {
    toast(e.message);
  }
}

function populateDropdowns() {
  // Populate collect-user-id dropdown for Admin
  const adminSelect = $("collect-user-id");
  if (adminSelect) {
    adminSelect.innerHTML = '<option value="">Choose member...</option>' + 
      state.members.map(m => `<option value="${m.id}">${escapeHtml(m.name)}</option>`).join("");
  }

  // Populate expense payer & participant chips
  const opts = state.members.map(m => `<option value="${m.id}">${escapeHtml(m.name)}</option>`).join("");
  $("expense-payer").innerHTML = opts;
  $("expense-participants").innerHTML = opts;
  [...$("expense-participants").options].forEach(o => o.selected = true);
  renderParticipantChips();
}

/* ==================== OVERVIEW MODULE ==================== */

function renderOverview() {
  const g = state.group || {};
  $("overview-trip-title").textContent = g.trip_title || g.name || "EDITH Annual Trip";
  $("overview-destination").textContent = g.trip_destination || "Manali & Spiti Valley";
  
  if (g.trip_start_date && g.trip_end_date) {
    $("overview-dates").textContent = `${g.trip_start_date} to ${g.trip_end_date}`;
  } else {
    $("overview-dates").textContent = "Travel dates not finalized";
  }

  const target = state.fundSummary?.fund_target || 96000;
  const collected = state.fundSummary?.fund_collected || 0;
  const balance = state.fundSummary?.kitty_balance ?? (collected - (state.fundSummary?.fund_disbursed || 0));

  $("stat-collected").textContent = money(collected);
  $("stat-balance").textContent = money(balance);
  $("stat-target-meta").textContent = `Target: ${money(target)} (₹2,000/mo × 4 members)`;
  $("stat-members").textContent = `${state.members.length} / 4`;

  const pct = target > 0 ? Math.min(100, Math.max(0, (collected / target) * 100)) : 0;
  const remaining = Math.max(0, target - collected);

  $("fund-progress").style.width = `${pct}%`;
  $("fund-progress-label").textContent = `${pct.toFixed(1)}% Collected`;
  $("fund-remaining").textContent = `${money(remaining)} Remaining`;

  renderOverviewBalances();
}

function renderOverviewBalances() {
  const box = $("overview-balances");
  if (!state.balances || !Object.keys(state.balances).length) {
    box.innerHTML = '<p class="muted">No shared expenses logged yet.</p>';
    return;
  }
  box.innerHTML = Object.entries(state.balances).map(([userId, bal]) => {
    const mem = state.members.find(m => m.id === userId);
    const name = mem ? mem.name : "Member";
    const isPos = bal > 0;
    const isZero = bal === 0;
    const colorClass = isZero ? "muted" : (isPos ? "positive-text" : "negative-text");
    const sign = isPos ? "+" : "";
    return `
      <div class="balance-mini-card">
        <b>${escapeHtml(name)}</b>
        <strong class="${colorClass}">${sign}${money(bal)}</strong>
      </div>
    `;
  }).join("");
}

/* ==================== TRIP FUND MODULE ==================== */

async function refreshFund() {
  try {
    const summary = await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/summary`);
    state.fundSummary = summary;

    const myContribs = await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/contributions/my`);
    state.myContributions = myContribs.contributions || [];

    const txs = await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/transactions`);
    state.fundTransactions = txs.transactions || [];

    if (state.user?.role === "admin") {
      const allContribs = await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/contributions/all`);
      state.allContributions = allContribs.contributions || [];
    }

    renderFund();
  } catch (e) {
    console.error("Fund refresh error:", e);
  }
}

function renderFund() {
  const fs = state.fundSummary || {};
  const collected = fs.fund_collected || 0;
  const disbursed = fs.fund_disbursed || 0;
  const balance = fs.kitty_balance ?? (collected - disbursed);

  $("fund-balance-large").textContent = money(balance);
  $("fund-total-large").textContent = money(collected);
  $("fund-disbursed-large").textContent = money(disbursed);

  // Badge count for verified payments
  const myVerifiedCount = state.myContributions.filter(c => c.status === "verified").length;
  $("my-verified-badge").textContent = `${myVerifiedCount} / 12 Paid`;

  // Render Member Contributions
  const isAdmin = state.user?.role === "admin";
  const recordsToRender = (isAdmin && state.showAllMembersSchedule) ? state.allContributions : state.myContributions;

  $("schedule-section-title").textContent = (isAdmin && state.showAllMembersSchedule)
    ? "All 4 Members' Savings Schedule"
    : "My Monthly Contributions";

  if (!recordsToRender.length) {
    $("my-contributions-list").innerHTML = '<p class="muted">No savings schedule generated yet.</p>';
  } else {
    $("my-contributions-list").innerHTML = recordsToRender.map(c => {
      const isPaid = c.status === "verified";
      const isSubmitted = c.status === "submitted";
      const badgeHtml = isPaid
        ? '<span class="badge-paid">✓ Paid</span>'
        : (isSubmitted ? '<span class="badge-pending">Submitted (Review)</span>' : '<span class="badge-pending">Pending</span>');

      // Admin fast 1-click action or member submit action
      let actionBtn = "";
      if (isAdmin && !isPaid) {
        actionBtn = `<button class="secondary-btn btn-sm" onclick="directVerifyContribution('${c.id}')">✓ Mark Paid</button>`;
      } else if (!isPaid && !isSubmitted && c.user_id === state.user?.id) {
        actionBtn = `<button class="secondary-btn btn-sm" onclick="openFundSubmitModal('${c.id}', ${c.month_index}, ${c.amount_due})">Submit UTR</button>`;
      }

      // Member name label if showing all members
      const memberName = c.member_name ? `<span class="contrib-member-name">${escapeHtml(c.member_name)}</span>` : "";

      return `
        <div class="contrib-card">
          <div class="contrib-card-head">
            <span class="contrib-month">Month ${c.month_index} (${c.cycle_month || '2026'})</span>
            ${badgeHtml}
          </div>
          <div class="contrib-amount-row">
            <span class="contrib-amount">${money(c.amount_due || c.amount || 2000)}</span>
            ${memberName}
          </div>
          <div class="contrib-card-footer">
            <small class="muted">${c.utr_reference ? `Ref: ${escapeHtml(c.utr_reference)}` : 'Due: 10th of month'}</small>
            ${actionBtn}
          </div>
        </div>
      `;
    }).join("");
  }

  // Render Fund Disbursements
  if (!state.fundTransactions.length) {
    $("fund-transactions-list").innerHTML = '<p class="muted">No payments made from the fund yet.</p>';
  } else {
    $("fund-transactions-list").innerHTML = state.fundTransactions.map(tx => `
      <div class="disb-card">
        <div>
          <b>${escapeHtml(tx.description || tx.recipient_name || 'Common Expense')}</b>
          <small>${tx.created_at ? tx.created_at.slice(0, 10) : ''} · Logged by Admin</small>
        </div>
        <span class="disb-amount-negative">-${money(tx.amount)}</span>
      </div>
    `).join("");
  }
}

// 1-Click Fast Direct Verification by Admin
window.directVerifyContribution = async function(contribId) {
  try {
    await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/contributions/${contribId}/verify`, {
      method: "PUT",
    });
    toast("Payment marked as verified and added to fund!");
    await refreshFund();
    renderOverview();
  } catch (e) {
    toast(e.message);
  }
};

// Admin Direct Collection Modal
function openAdminCollectModal() {
  $("admin-collect-error").textContent = "";
  $("admin-collect-dialog").showModal();
}

async function submitAdminCollection(ev) {
  ev.preventDefault();
  const error = $("admin-collect-error");
  error.textContent = "";

  const userId = $("collect-user-id").value;
  if (!userId) {
    error.textContent = "Please select a member.";
    return;
  }

  try {
    const payload = {
      user_id: userId,
      month_index: Number($("collect-month-index").value),
      amount: Number($("collect-amount").value),
      payment_mode: $("collect-mode").value,
      notes: $("collect-notes").value.trim() || "Collected directly by Admin",
    };

    const res = await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/contributions/admin-collect`, {
      method: "POST",
      body: JSON.stringify(payload),
    });

    $("admin-collect-dialog").close();
    toast(res.message || "Payment recorded successfully!");
    await refreshFund();
    renderOverview();
  } catch (e) {
    error.textContent = e.message;
  }
}

// Member UTR Reference Submission
window.openFundSubmitModal = function(contribId, monthIndex, amount) {
  $("submit-contrib-id").value = contribId;
  $("submit-contrib-desc").textContent = `Month ${monthIndex} payment of ${money(amount)}. Enter transaction reference.`;
  $("submit-date").value = dateToday();
  $("submit-utr").value = "";
  $("submit-notes").value = "";
  $("fund-submit-error").textContent = "";
  $("fund-submit-dialog").showModal();
};

async function submitFundReference(ev) {
  ev.preventDefault();
  const id = $("submit-contrib-id").value;
  const error = $("fund-submit-error");
  error.textContent = "";

  try {
    await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/contributions/${id}/submit`, {
      method: "POST",
      body: JSON.stringify({
        utr_reference: $("submit-utr").value.trim(),
        payment_date: $("submit-date").value,
        notes: $("submit-notes").value.trim(),
      }),
    });
    $("fund-submit-dialog").close();
    toast("Reference submitted! Admin will confirm.");
    await refreshFund();
  } catch (e) {
    error.textContent = e.message;
  }
}

// Fund Spending Disbursement Form
function openDisbursementModal() {
  $("disb-date").value = dateToday();
  $("fund-disb-error").textContent = "";
  $("fund-disbursement-dialog").showModal();
}

async function submitDisbursement(ev) {
  ev.preventDefault();
  const error = $("fund-disb-error");
  error.textContent = "";

  try {
    await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/disbursements`, {
      method: "POST",
      body: JSON.stringify({
        amount: Number($("disb-amount").value),
        category: $("disb-category").value,
        recipient: $("disb-recipient").value.trim(),
        description: $("disb-desc").value.trim(),
        disbursement_date: $("disb-date").value,
      }),
    });
    $("fund-disbursement-dialog").close();
    toast("Payment recorded and deducted from fund balance.");
    await refreshFund();
    renderOverview();
  } catch (e) {
    error.textContent = e.message;
  }
}

/* ==================== EXPENSE SPLITTER MODULE ==================== */

async function refreshExpenses() {
  try {
    const [expData, balData] = await Promise.all([
      api(`/groups/${encodeURIComponent(state.groupCode)}/expenses`),
      api(`/groups/${encodeURIComponent(state.groupCode)}/balances`),
    ]);
    state.expenses = expData.expenses || [];
    state.balances = balData.balances || {};
    renderExpenses(balData);
    renderOverviewBalances();
  } catch (e) {
    console.error("Expense refresh error:", e);
  }
}

function renderExpenses(balData) {
  const total = state.expenses.reduce((s, x) => s + Number(x.amount || 0), 0);
  $("stat-expenses").textContent = money(total);
  $("expense-total").textContent = money(total);

  const myId = state.user?.id;
  const myBal = Number(state.balances[myId] || 0);
  $("you-are-owed").textContent = myBal > 0 ? money(myBal) : "₹0";
  $("you-owe").textContent = myBal < 0 ? money(Math.abs(myBal)) : "₹0";

  // Render Expense List
  const listEl = $("expense-list");
  if (!state.expenses.length) {
    listEl.innerHTML = '<p class="muted">No shared expenses logged yet. Tap "+ Add Expense" to get started.</p>';
  } else {
    listEl.innerHTML = state.expenses.map(e => {
      const payer = state.members.find(m => m.id === e.paid_by_user_id);
      const payerName = payer ? payer.name : "Member";
      const categoryIcons = {
        "Food & Dining": "◈",
        "Accommodation": "⌂",
        "Fuel": "▲",
        "Transport / Cab": "◬",
        "Activities": "◎",
        "Shopping": "◇",
        "Other": "○"
      };
      const icon = categoryIcons[e.category] || "○";
      return `
        <div class="expense-row-item">
          <div class="expense-icon-badge">${icon}</div>
          <div class="expense-main-info">
            <b>${escapeHtml(e.title)}</b>
            <small>Paid by ${escapeHtml(payerName)} · ${e.expense_date ? e.expense_date.slice(0, 10) : ''} · ${escapeHtml(e.category || 'Expense')}</small>
          </div>
          <div class="expense-amount-side">
            <strong>${money(e.amount)}</strong>
            <small>${escapeHtml(e.split_type)}</small>
          </div>
        </div>
      `;
    }).join("");
  }

  // Render Balances List
  const balBox = $("balance-list");
  balBox.innerHTML = Object.entries(state.balances).map(([uid, bal]) => {
    const mem = state.members.find(m => m.id === uid);
    const name = mem ? mem.name : "Member";
    const isPos = bal > 0;
    const isZero = bal === 0;
    const colorClass = isZero ? "muted" : (isPos ? "positive-text" : "negative-text");
    const sign = isPos ? "+" : "";
    return `
      <div class="balance-item-row">
        <span>${escapeHtml(name)}</span>
        <b class="${colorClass}">${sign}${money(bal)}</b>
      </div>
    `;
  }).join("");

  // Render Suggested Settlements
  const settlements = balData?.suggested_settlements || [];
  const setBox = $("settlement-list");
  if (!settlements.length) {
    setBox.innerHTML = '<p class="muted">All balances are settled up.</p>';
  } else {
    setBox.innerHTML = settlements.map(s => {
      const fromMem = state.members.find(m => m.id === s.from_user_id);
      const toMem = state.members.find(m => m.id === s.to_user_id);
      const fromName = fromMem ? fromMem.name : "Member";
      const toName = toMem ? toMem.name : "Member";
      return `
        <div class="settle-item">
          <span><b>${escapeHtml(fromName)}</b> pays <b>${escapeHtml(toName)}</b></span>
          <div style="display:flex;align-items:center;gap:8px;">
            <strong class="negative-text">${money(s.amount)}</strong>
            <button class="settle-btn" onclick="openSettleModal('${s.from_user_id}', '${s.to_user_id}', ${s.amount}, '${escapeHtml(fromName)}', '${escapeHtml(toName)}')">Settle</button>
          </div>
        </div>
      `;
    }).join("");
  }
}

// Participant Chips Selection
function renderParticipantChips() {
  const container = $("expense-participants-chips");
  if (!container) return;
  const select = $("expense-participants");
  const selectedValues = new Set([...select.selectedOptions].map(o => o.value));

  container.innerHTML = state.members.map(m => {
    const isSel = selectedValues.has(m.id);
    return `
      <div class="participant-chip ${isSel ? 'selected' : ''}" data-user-id="${m.id}" role="button" tabindex="0">
        <span class="chip-avatar">${initials(m.name)}</span>
        <span class="chip-name">${escapeHtml(m.name)}</span>
        <span class="chip-check">✓</span>
      </div>
    `;
  }).join("");

  container.querySelectorAll(".participant-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const uid = chip.dataset.userId;
      const opt = [...select.options].find(o => o.value === uid);
      if (opt) {
        opt.selected = !opt.selected;
        chip.classList.toggle("selected", opt.selected);
        renderSplitEditor();
      }
    });
  });
}

function selectAllParticipants(selectState = true) {
  const select = $("expense-participants");
  [...select.options].forEach(o => o.selected = selectState);
  document.querySelectorAll(".participant-chip").forEach(chip => {
    chip.classList.toggle("selected", selectState);
  });
  renderSplitEditor();
}

function renderSplitEditor() {
  const mode = $("split-type").value;
  const selected = [...$("expense-participants").selectedOptions];
  const box = $("custom-splits");
  if (mode === "equal") {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }
  box.classList.remove("hidden");
  box.innerHTML = selected.map(o => `
    <div class="split-row">
      <span>${escapeHtml(o.text)}</span>
      <input type="number" min="0" step="${mode === "percentage" ? "0.01" : "1"}" data-split-user="${o.value}" placeholder="${mode === "percentage" ? "%" : "₹"}" required>
    </div>
  `).join("") || '<small class="muted">Select participants first.</small>';
}

function openExpenseModal() {
  if (!state.members.length) {
    toast("Member list is loading...");
    return;
  }
  $("expense-date").value = dateToday();
  $("expense-form-error").textContent = "";
  selectAllParticipants(true);
  $("expense-dialog").showModal();
}

async function submitExpense(ev) {
  ev.preventDefault();
  const error = $("expense-form-error");
  error.textContent = "";

  try {
    const participants = [...$("expense-participants").selectedOptions].map(o => o.value);
    const splitType = $("split-type").value;
    const payload = {
      title: $("expense-title").value.trim(),
      category: $("expense-category").value,
      amount: Number($("expense-amount").value),
      paid_by_user_id: $("expense-payer").value,
      split_type: splitType,
      participant_user_ids: participants,
      expense_date: $("expense-date").value,
      notes: $("expense-notes").value.trim(),
    };

    if (!payload.participant_user_ids.length) {
      error.textContent = "Select at least one participant sharing this expense.";
      return;
    }

    if (splitType === "custom") {
      const splits = [];
      let sum = 0;
      document.querySelectorAll("[data-split-user]").forEach(inp => {
        const amt = Number(inp.value || 0);
        sum += amt;
        splits.push({ user_id: inp.dataset.splitUser, share_amount: amt });
      });
      if (Math.abs(sum - payload.amount) > 0.01) {
        error.textContent = `Custom shares sum to ₹${sum}, but expense amount is ₹${payload.amount}.`;
        return;
      }
      payload.splits = splits;
    } else if (splitType === "percentage") {
      const splits = [];
      let sum = 0;
      document.querySelectorAll("[data-split-user]").forEach(inp => {
        const pct = Number(inp.value || 0);
        sum += pct;
        splits.push({ user_id: inp.dataset.splitUser, share_percentage: pct });
      });
      if (Math.abs(sum - 100) > 0.01) {
        error.textContent = `Percentages sum to ${sum}%, must equal 100%.`;
        return;
      }
      payload.splits = splits;
    }

    await api(`/groups/${encodeURIComponent(state.groupCode)}/expenses`, {
      method: "POST",
      body: JSON.stringify(payload),
    });

    $("expense-dialog").close();
    toast("Expense saved and balances updated!");
    await refreshExpenses();
    renderOverview();
  } catch (e) {
    error.textContent = e.message;
  }
}

// Settle Debt Modal
window.openSettleModal = function(fromId, toId, amount, fromName, toName) {
  $("settle-from-id").value = fromId;
  $("settle-to-id").value = toId;
  $("settle-direction-desc").textContent = `${fromName} paying ${toName}`;
  $("settle-amount").value = amount;
  $("settle-date").value = dateToday();
  $("settle-note").value = "";
  $("settle-error").textContent = "";
  $("settle-dialog").showModal();
};

async function submitSettlement(ev) {
  ev.preventDefault();
  const error = $("settle-error");
  error.textContent = "";

  try {
    await api(`/groups/${encodeURIComponent(state.groupCode)}/settlements`, {
      method: "POST",
      body: JSON.stringify({
        from_user_id: $("settle-from-id").value,
        to_user_id: $("settle-to-id").value,
        amount: Number($("settle-amount").value),
        settlement_date: $("settle-date").value,
        note: $("settle-note").value.trim(),
      }),
    });
    $("settle-dialog").close();
    toast("Settlement recorded. Balances refreshed.");
    await refreshExpenses();
    renderOverview();
  } catch (e) {
    error.textContent = e.message;
  }
}

/* ==================== ITINERARY MODULE ==================== */

function renderTrip() {
  const g = state.group || {};
  $("trip-title-display").textContent = g.trip_title || g.name || "EDITH Annual Trip";
  $("trip-budget-display").textContent = money(g.planned_trip_budget || 96000);
  $("trip-notes-display").textContent = g.trip_notes || "No notes added yet.";

  if (g.trip_start_date && g.trip_end_date) {
    $("trip-dates-display").textContent = `${g.trip_start_date} to ${g.trip_end_date}`;
  } else {
    $("trip-dates-display").textContent = "Set travel dates";
  }

  const stops = g.trip_stops || [];
  const container = $("trip-stops");
  if (!stops.length) {
    container.innerHTML = '<div class="empty-state">No destinations added yet. Tap "Edit Route" to plan your stops.</div>';
  } else {
    container.innerHTML = stops.map((s, idx) => `
      <div class="stop-card">
        <div>
          <h3>Stop ${s.stop_number || idx + 1}: ${escapeHtml(s.destination_name || s.destination)}</h3>
          <p>${s.arrival_date ? `Arrives: ${s.arrival_date}` : ''} ${s.nights ? `· ${s.nights} nights` : ''} ${s.transit_mode ? `· Transit: ${s.transit_mode}` : ''}</p>
        </div>
      </div>
    `).join("");
  }
}

function openTripDialog() {
  const g = state.group || {};
  $("trip-title-input").value = g.trip_title || g.name || "";
  $("trip-start").value = g.trip_start_date || "";
  $("trip-end").value = g.trip_end_date || "";
  $("trip-budget-input").value = g.planned_trip_budget || 96000;
  $("trip-notes-input").value = g.trip_notes || "";
  $("trip-form-error").textContent = "";

  const container = $("stop-editor");
  container.innerHTML = "";
  const stops = g.trip_stops || [];
  stops.forEach(addStopInputRow);
  $("trip-dialog").showModal();
}

function addStopInputRow(stop = {}) {
  const container = $("stop-editor");
  const div = document.createElement("div");
  div.className = "stop-edit-card";
  div.innerHTML = `
    <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
      <b style="font-size:12px;">Stop Destination</b>
      <button type="button" class="secondary-btn btn-sm" onclick="this.closest('.stop-edit-card').remove()">Remove</button>
    </div>
    <input class="stop-name" placeholder="Destination name" value="${escapeHtml(stop.destination_name || stop.destination || '')}" required>
    <div class="form-row" style="margin-top:8px;">
      <input type="date" class="stop-date" value="${stop.arrival_date || ''}">
      <input type="number" class="stop-nights" min="0" placeholder="Nights" value="${stop.nights ?? 1}">
    </div>
  `;
  container.appendChild(div);
}

async function submitTripPlan(ev) {
  ev.preventDefault();
  const error = $("trip-form-error");
  error.textContent = "";

  const stops = [];
  document.querySelectorAll(".stop-edit-card").forEach((card, idx) => {
    const dest = card.querySelector(".stop-name").value.trim();
    if (dest) {
      stops.push({
        stop_number: idx + 1,
        destination_name: dest,
        arrival_date: card.querySelector(".stop-date").value || null,
        nights: Number(card.querySelector(".stop-nights").value || 1),
      });
    }
  });

  try {
    await api(`/groups/${encodeURIComponent(state.groupCode)}/trip-plan`, {
      method: "PATCH",
      body: JSON.stringify({
        trip_title: $("trip-title-input").value.trim(),
        trip_start_date: $("trip-start").value || null,
        trip_end_date: $("trip-end").value || null,
        planned_trip_budget: Number($("trip-budget-input").value || 0),
        notes: $("trip-notes-input").value.trim(),
        stops: stops.map(s => ({
          destination: s.destination_name,
          arrival_date: s.arrival_date,
          departure_date: null,
          transport: "",
          accommodation: "",
          notes: `${s.nights} nights`,
        })),
      }),
    });
    $("trip-dialog").close();
    toast("Trip details saved!");
    await loadApp();
  } catch (e) {
    error.textContent = e.message;
  }
}

/* ==================== AUDIT LOGS ==================== */

async function openAuditDialog() {
  $("audit-dialog").showModal();
  const stream = $("audit-log-stream");
  stream.innerHTML = '<p class="muted">Loading audit history...</p>';

  try {
    const res = await api("/admin/audit-logs?limit=40");
    const logs = res.logs || [];
    if (!logs.length) {
      stream.innerHTML = '<p class="muted">No audit events recorded yet.</p>';
      return;
    }
    stream.innerHTML = logs.map(l => `
      <div class="audit-item">
        <div style="display:flex;justify-content:space-between;color:var(--muted);margin-bottom:4px;">
          <span><b>${escapeHtml(l.actor_name || 'System')}</b> (${escapeHtml(l.action)})</span>
          <span>${l.timestamp ? l.timestamp.slice(0, 19).replace('T', ' ') : ''}</span>
        </div>
        <p style="margin:0;">${escapeHtml(l.notes || '')}</p>
      </div>
    `).join("");
  } catch (e) {
    stream.innerHTML = `<p class="error-text">${escapeHtml(e.message)}</p>`;
  }
}

/* ==================== EVENT LISTENERS ==================== */

// Login Form
$("login-form")?.addEventListener("submit", async ev => {
  ev.preventDefault();
  const error = $("login-error");
  error.textContent = "";

  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: $("login-email").value.trim(),
        password: $("login-password").value,
      }),
    });
    loginSuccess(data);
  } catch (e) {
    error.textContent = e.message;
  }
});

// Logout Buttons
$("logout-btn")?.addEventListener("click", logout);
$("mobile-logout-btn")?.addEventListener("click", logout);

// Navigation
document.querySelectorAll(".nav-link").forEach(b => b.addEventListener("click", () => showView(b.dataset.view)));
document.querySelectorAll("[data-go]").forEach(b => b.addEventListener("click", () => showView(b.dataset.go)));
$("refresh-btn")?.addEventListener("click", loadApp);

// Expense Form & Participants
$("open-expense-modal")?.addEventListener("click", openExpenseModal);
$("expense-form")?.addEventListener("submit", submitExpense);
$("split-type")?.addEventListener("change", renderSplitEditor);
$("select-all-participants")?.addEventListener("click", () => selectAllParticipants(true));
$("clear-participants")?.addEventListener("click", () => selectAllParticipants(false));

// Admin Direct Collection Modal
$("admin-collect-btn")?.addEventListener("click", openAdminCollectModal);
$("admin-collect-form")?.addEventListener("submit", submitAdminCollection);

// Fund Spending Disbursement
$("open-disbursement-modal")?.addEventListener("click", openDisbursementModal);
$("fund-disbursement-form")?.addEventListener("submit", submitDisbursement);

// Member UTR Form
$("fund-submit-form")?.addEventListener("submit", submitFundReference);

// Toggle All Members in Fund Schedule
$("toggle-all-contributions-btn")?.addEventListener("click", () => {
  state.showAllMembersSchedule = !state.showAllMembersSchedule;
  $("toggle-all-contributions-btn").textContent = state.showAllMembersSchedule ? "Show My Schedule Only" : "Show All 4 Members";
  renderFund();
});

// Settlement Form
$("settle-form")?.addEventListener("submit", submitSettlement);

// Trip Plan
$("edit-trip-btn")?.addEventListener("click", openTripDialog);
$("add-stop-btn")?.addEventListener("click", () => addStopInputRow());
$("trip-form")?.addEventListener("submit", submitTripPlan);

// Audit Dialog & Close Buttons
$("audit-btn")?.addEventListener("click", openAuditDialog);
document.querySelectorAll("[data-close]").forEach(b => b.addEventListener("click", () => $(b.dataset.close).close()));

// Auto-restore session on page load
(async () => {
  const token = sessionStorage.getItem("edith_token");
  const user = sessionStorage.getItem("edith_user");
  if (token && user) {
    loginSuccess({ access_token: token, user: JSON.parse(user) });
  }
})();
