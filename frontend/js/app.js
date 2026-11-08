const API = (window.EDITH_API_BASE || (window.location.port === "5500" ? "http://127.0.0.1:8000/api/v1" : "/api/v1")).replace(/\/$/, "");
const state = {
  token: null,
  user: null,
  groupCode: "EDITH-TRIP-01",
  group: null,
  members: [],
  expenses: [],
  balances: null,
  kittySummary: null,
  myContributions: [],
  allContributions: [],
  kittyTransactions: [],
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
    overview: ["YOUR GROUP AT A GLANCE", "Overview"],
    kitty: ["SAVINGS LEDGER & RECONCILIATION", "Savings kitty"],
    expenses: ["TRIP EXPENSES · SPLITWISE-STYLE", "Kitty Split"],
    trip: ["MULTI-STOP ITINERARY", "Trip planner"],
  };
  $("page-kicker").textContent = titles[name][0];
  $("page-title").textContent = titles[name][1];
  if (name === "kitty") refreshKitty();
  if (name === "expenses") refreshExpenses();
  if (name === "trip") renderTrip();
}

function loginSuccess(data) {
  state.token = data.access_token;
  state.user = data.user;
  sessionStorage.setItem("edith_token", state.token);
  sessionStorage.setItem("edith_user", JSON.stringify(state.user));
  $("login-screen").classList.add("hidden");
  $("app-shell").classList.remove("hidden");
  $("user-name").textContent = state.user.name;
  $("user-role").textContent = state.user.role === "admin" ? "Administrator" : "Group Member";
  $("user-avatar").textContent = initials(state.user.name);

  // Show admin specific controls
  if (state.user.role === "admin") {
    $("admin-verification-panel").classList.remove("hidden");
    $("open-disbursement-modal").classList.remove("hidden");
    $("open-reconcile-modal").classList.remove("hidden");
    $("audit-btn").classList.remove("hidden");
  } else {
    $("admin-verification-panel").classList.add("hidden");
    $("open-disbursement-modal").classList.add("hidden");
    $("open-reconcile-modal").classList.add("hidden");
    $("audit-btn").classList.add("hidden");
  }

  loadApp();
}

async function loadApp() {
  try {
    const groups = await api("/groups/mine");
    const group = groups.groups.find(g => g.group_code === state.groupCode) || groups.groups[0];
    if (!group) {
      toast("You are not assigned to a group yet.");
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

    await Promise.all([
      refreshKitty(),
      refreshExpenses(),
    ]);

    renderOverview();
    renderTrip();
    populateExpensePeople();
  } catch (e) {
    toast(e.message);
  }
}

/* ==================== OVERVIEW MODULE ==================== */

function renderOverview() {
  const target = state.kittySummary?.fund_target || 96000;
  const collected = state.kittySummary?.fund_collected || 0;
  const remaining = Math.max(0, target - collected);
  const pct = target ? Math.min(100, (collected / target) * 100) : 0;

  $("stat-target").textContent = money(target);
  $("stat-collected").textContent = money(collected);
  $("stat-members").textContent = `${state.members.length} / 4`;
  $("stat-expenses").textContent = money(state.balances?.total_expenses || 0);

  $("kitty-progress").style.width = `${pct}%`;
  $("kitty-progress-label").textContent = `${pct.toFixed(1)}% collected`;
  $("kitty-remaining").textContent = `${money(remaining)} remaining`;

  const stops = state.group?.trip_stops || [];
  $("overview-destination").textContent = stops.length
    ? stops.map(s => s.destination).join(" → ")
    : (state.group?.trip_destination || "Not planned yet");

  $("overview-dates").textContent = state.group?.trip_start_date && state.group?.trip_end_date
    ? `${state.group.trip_start_date} to ${state.group.trip_end_date}`
    : "Add your trip details";

  renderBalanceSnapshot();
}

function renderBalanceSnapshot() {
  const target = $("overview-balances");
  if (!state.balances?.member_balances?.length) {
    target.innerHTML = '<p class="muted">Add expenses to see group balances.</p>';
    return;
  }
  target.innerHTML = state.balances.member_balances.map(m => `
    <div class="mini-balance">
      <b>${escapeHtml(m.name)}</b>
      <span class="${m.net_balance >= 0 ? "positive" : "negative"}">
        ${m.net_balance >= 0 ? "Gets back " : "Owes "}${money(Math.abs(m.net_balance))}
      </span>
    </div>
  `).join("");
}

/* ==================== SAVINGS KITTY MODULE ==================== */

async function refreshKitty() {
  if (!state.token || !state.groupCode) return;
  try {
    const summary = await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/summary`);
    state.kittySummary = summary;

    const myContribs = await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/contributions/my`);
    state.myContributions = myContribs.contributions || [];

    const txs = await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/transactions`);
    state.kittyTransactions = txs.transactions || [];

    if (state.user?.role === "admin") {
      const allContribs = await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/contributions/all`);
      state.allContributions = allContribs.contributions || [];
    }

    renderKitty();
    renderOverview();
  } catch (e) {
    console.error("Kitty refresh error:", e);
  }
}

function renderKitty() {
  const ks = state.kittySummary || {};
  $("kitty-balance-large").textContent = money(ks.kitty_balance || 0);
  $("kitty-total-large").textContent = money(ks.fund_collected || 0);
  $("kitty-target-large").textContent = money(ks.fund_target || 96000);
  $("kitty-disbursed-large").textContent = money(ks.fund_disbursed || 0);
  $("reconcile-system-bal").textContent = money(ks.kitty_balance || 0);

  const verifiedCount = state.myContributions.filter(c => c.status === "verified").length;
  $("my-verified-badge").textContent = `${verifiedCount} / ${state.myContributions.length || 12} Verified`;

  // Render My Contribution Cards (12 Months)
  $("my-contributions-list").innerHTML = state.myContributions.length
    ? state.myContributions.map(c => {
      const statusBadges = {
        verified: '<span class="badge badge-verified">Verified</span>',
        submitted: '<span class="badge badge-submitted">Under Review</span>',
        pending: '<span class="badge badge-pending">Pending</span>',
        rejected: '<span class="badge badge-rejected">Rejected</span>',
      };
      const canSubmit = c.status === "pending" || c.status === "rejected";
      return `
        <div class="contrib-card">
          <div class="contrib-header">
            <span class="contrib-title">Month ${c.month_index} (${escapeHtml(c.cycle_month || "")})</span>
            ${statusBadges[c.status] || ""}
          </div>
          <div class="contrib-due">Due: ${escapeHtml(c.due_date || "10th of month")}</div>
          <div class="contrib-amount">${money(c.amount_due)}</div>
          ${c.utr_reference ? `<div class="contrib-utr">UTR: ${escapeHtml(c.utr_reference)}</div>` : ""}
          ${c.rejection_reason ? `<small class="error-text">Reason: ${escapeHtml(c.rejection_reason)}</small>` : ""}
          <div class="contrib-action">
            ${canSubmit
              ? `<button class="primary-btn btn-sm full" onclick="openSubmitModal('${c.id}', ${c.month_index}, ${c.amount_due})">Submit UTR Reference</button>`
              : `<small class="muted">${c.status === "verified" ? "Credited to Kitty" : "Awaiting admin confirmation"}</small>`}
          </div>
        </div>
      `;
    }).join("")
    : '<p class="muted">No contributions scheduled yet.</p>';

  // Render Admin Verification Queue (Admin Only)
  if (state.user?.role === "admin") {
    const pendingReview = (state.allContributions || []).filter(c => c.status === "submitted");
    $("admin-verification-list").innerHTML = pendingReview.length
      ? pendingReview.map(c => `
        <div class="verif-card">
          <div class="verif-info">
            <b>${escapeHtml(c.user_name)} · Month ${c.month_index} (${money(c.amount_due)})</b>
            <span>UTR: <code style="color:var(--mint);">${escapeHtml(c.utr_reference)}</code> · Submitted: ${String(c.submitted_at || "").slice(0, 10)}</span>
            ${c.proof_url ? `<br><a href="${escapeHtml(c.proof_url)}" target="_blank" style="color:var(--green);font-size:10px;">View Attached Receipt ↗</a>` : ""}
          </div>
          <div class="verif-actions">
            <button class="primary-btn btn-sm btn-approve" onclick="verifyContribution('${c.id}')">Approve & Credit</button>
            <button class="btn-sm btn-reject" onclick="rejectContribution('${c.id}')">Reject</button>
          </div>
        </div>
      `).join("")
      : '<p class="muted">No submitted payments awaiting verification.</p>';
  }

  // Render Kitty Common Disbursements
  $("kitty-transactions-list").innerHTML = state.kittyTransactions.length
    ? state.kittyTransactions.map(tx => {
      const isDisb = tx.transaction_type === "disbursement";
      const isCredit = tx.transaction_type === "contribution_credit";
      return `
        <div class="disb-card">
          <div>
            <b>${escapeHtml(tx.description || tx.category)}</b>
            <small>${escapeHtml(tx.created_at ? tx.created_at.slice(0, 10) : "")} ${tx.recipient ? "· Paid to: " + escapeHtml(tx.recipient) : ""}</small>
          </div>
          <div class="disb-amount" style="color:${isCredit ? 'var(--mint)' : '#fca5a5'};">
            ${isCredit ? '+' : '-'}${money(tx.amount)}
          </div>
        </div>
      `;
    }).join("")
    : '<p class="muted">No disbursements or common expenses recorded from Kitty yet.</p>';
}

function openSubmitModal(id, monthIndex, amount) {
  $("submit-contrib-id").value = id;
  $("submit-contrib-desc").textContent = `Submit payment reference for Month ${monthIndex} (${money(amount)})`;
  $("submit-date").value = dateToday();
  $("submit-utr").value = "";
  $("submit-proof-url").value = "";
  $("submit-notes").value = "";
  $("kitty-submit-error").textContent = "";
  $("kitty-submit-dialog").showModal();
}

async function verifyContribution(contribId) {
  if (!confirm("Confirm that funds have been received in the custodian bank account?")) return;
  try {
    await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/contributions/${contribId}/verify`, {
      method: "PUT",
    });
    toast("Contribution verified and credited to Kitty!");
    await refreshKitty();
  } catch (e) {
    toast(e.message);
  }
}

async function rejectContribution(contribId) {
  const reason = prompt("Enter the rejection reason (e.g. UTR not found on bank statement):");
  if (!reason) return;
  try {
    await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/contributions/${contribId}/reject`, {
      method: "PUT",
      body: JSON.stringify({ reason: reason.trim() }),
    });
    toast("Contribution rejected.");
    await refreshKitty();
  } catch (e) {
    toast(e.message);
  }
}

/* ==================== EXPENSES & KITTY SPLIT MODULE ==================== */

async function refreshExpenses() {
  if (!state.token || !state.groupCode) return;
  try {
    const [expenses, balances] = await Promise.all([
      api(`/groups/${encodeURIComponent(state.groupCode)}/expenses`),
      api(`/groups/${encodeURIComponent(state.groupCode)}/balances`),
    ]);
    state.expenses = expenses.expenses || [];
    state.balances = balances;
    renderExpenses();
    renderOverview();
  } catch (e) {
    $("expense-list").innerHTML = `<p class="error-text">${escapeHtml(e.message)}</p>`;
  }
}

function renderExpenses() {
  $("expense-total").textContent = money(state.balances?.total_expenses || 0);
  $("stat-expenses").textContent = money(state.balances?.total_expenses || 0);

  const me = state.balances?.member_balances?.find(x => x.user_id === state.user?.id);
  $("you-are-owed").textContent = money(Math.max(0, me?.net_balance || 0));
  $("you-owe").textContent = money(Math.max(0, -(me?.net_balance || 0)));

  $("expense-list").innerHTML = state.expenses.length
    ? state.expenses.map(e => {
      const payer = state.members.find(m => m.id === e.paid_by_user_id)?.name || "Member";
      const date = String(e.expense_date || "").slice(0, 10);
      const isReversed = e.status === "reversed";
      const canReverse = !isReversed && (e.created_by === state.user?.id || state.user?.role === "admin");
      const icons = { Accommodation: "⌂", Food: "☕", Transport: "↗", Fuel: "◉", Activities: "✦", Shopping: "◇", Other: "•" };
      return `
        <div class="expense-item" style="${isReversed ? 'opacity:0.5;text-decoration:line-through;' : ''}">
          <div class="expense-emoji">${icons[e.category] || "•"}</div>
          <div class="expense-info">
            <b>${escapeHtml(e.title)} ${isReversed ? '<span class="badge badge-rejected">Reversed</span>' : ''}</b>
            <small>${escapeHtml(payer)} paid · ${escapeHtml(date)} · ${escapeHtml(e.category)}</small>
            ${e.notes ? `<small class="muted">${escapeHtml(e.notes)}</small>` : ""}
          </div>
          <div class="expense-amount">
            ${money(e.amount)}
            <small>${e.split_type === "equal" ? "Equal split" : e.split_type === "percentage" ? "Percentage split" : "Custom split"}</small>
            ${canReverse ? `<button class="text-btn" style="color:var(--red);font-size:9px;" onclick="reverseExpense('${e.id}')">Reverse</button>` : ""}
          </div>
        </div>
      `;
    }).join("")
    : '<p class="muted">No trip expenses recorded yet. Add your first one.</p>';

  $("balance-list").innerHTML = (state.balances?.member_balances || []).map(m => `
    <div class="balance-row">
      <span>${escapeHtml(m.name)}</span>
      <strong class="${m.net_balance >= 0 ? "positive" : "negative"}">
        ${m.net_balance >= 0 ? "+" : "−"}${money(Math.abs(m.net_balance))}
      </strong>
    </div>
  `).join("") || '<p class="muted">No balances yet.</p>';

  $("settlement-list").innerHTML = (state.balances?.suggested_settlements || []).map(t => {
    const isDebtor = t.from_user_id === state.user?.id;
    return `
      <div class="settlement-line" style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <span>${escapeHtml(t.from_name)} owes ${escapeHtml(t.to_name)}</span>
          <b style="display:block;color:var(--mint);">${money(t.amount)}</b>
        </div>
        ${isDebtor ? `<button class="soft-btn btn-sm" onclick="openSettleModal('${t.from_user_id}', '${t.to_user_id}', '${escapeHtml(t.to_name)}', ${t.amount})">Pay Now</button>` : ""}
      </div>
    `;
  }).join("") || '<p class="muted">All settled up! No debts pending.</p>';
}

function openSettleModal(fromId, toId, toName, amount) {
  $("settle-from-id").value = fromId;
  $("settle-to-id").value = toId;
  $("settle-direction-desc").textContent = `Paying ${toName} to settle balance`;
  $("settle-amount").value = amount;
  $("settle-date").value = dateToday();
  $("settle-note").value = "Settled via UPI";
  $("settle-error").textContent = "";
  $("settle-dialog").showModal();
}

async function reverseExpense(expenseId) {
  const reason = prompt("Reason for reversing this expense entry:");
  if (!reason) return;
  try {
    await api(`/groups/${encodeURIComponent(state.groupCode)}/expenses/${expenseId}/reverse?reason=${encodeURIComponent(reason)}`, {
      method: "POST",
    });
    toast("Expense reversed.");
    await refreshExpenses();
  } catch (e) {
    toast(e.message);
  }
}

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

function populateExpensePeople() {
  const opts = state.members.map(m => `<option value="${m.id}">${escapeHtml(m.name)}</option>`).join("");
  $("expense-payer").innerHTML = opts;
  $("expense-participants").innerHTML = opts;
  [...$("expense-participants").options].forEach(o => o.selected = true);
  renderParticipantChips();
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

function openExpenseDialog() {
  if (!state.members.length) {
    toast("Group member list is not available.");
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
      notes: $("expense-notes").value,
    };
    if (splitType !== "equal") {
      const values = [...document.querySelectorAll("[data-split-user]")];
      payload.splits = values.map(input => splitType === "percentage"
        ? { user_id: input.dataset.splitUser, share_percentage: Number(input.value) }
        : { user_id: input.dataset.splitUser, share_amount: Number(input.value) }
      );
      if (payload.splits.length !== participants.length || payload.splits.some(x => Object.values(x).some(v => v === undefined || v === null || Number.isNaN(v)))) {
        throw new Error("Enter a split value for every selected participant.");
      }
      const total = payload.splits.reduce((sum, x) => sum + (splitType === "percentage" ? x.share_percentage : x.share_amount), 0);
      const expected = splitType === "percentage" ? 100 : payload.amount;
      if (Math.abs(total - expected) > 0.0001) {
        throw new Error(`Split values must add up to ${expected}${splitType === "percentage" ? "%" : " rupees"}.`);
      }
    }
    await api(`/groups/${encodeURIComponent(state.groupCode)}/expenses`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    $("expense-dialog").close();
    $("expense-form").reset();
    toast("Expense saved.");
    await refreshExpenses();
  } catch (e) {
    error.textContent = e.message;
  }
}

/* ==================== TRIP PLANNER MODULE ==================== */

function renderTrip() {
  if (!state.group) return;
  const stops = state.group.trip_stops || [];
  $("trip-title-display").textContent = state.group.trip_title || state.group.name;
  $("trip-dates-display").textContent = [state.group.trip_start_date, state.group.trip_end_date].filter(Boolean).join(" → ") || "Dates not set";
  $("trip-budget-display").textContent = money(state.group.planned_trip_budget || 0);
  $("trip-notes-display").textContent = state.group.trip_notes || "No notes added.";
  $("trip-stops").innerHTML = stops.length
    ? stops.map((s, i) => `
      <article class="stop-card">
        <p class="eyebrow">STOP ${String(i + 1).padStart(2, "0")}</p>
        <h3>${escapeHtml(s.destination)}</h3>
        <p>${escapeHtml(s.arrival_date || "Date TBD")}${s.departure_date ? " → " + escapeHtml(s.departure_date) : ""}</p>
        ${s.transport ? `<p>Transport: ${escapeHtml(s.transport)}</p>` : ""}
        ${s.accommodation ? `<p>Stay: ${escapeHtml(s.accommodation)}</p>` : ""}
        ${s.notes ? `<p>${escapeHtml(s.notes)}</p>` : ""}
      </article>
    `).join("")
    : '<div class="empty-state">No destinations added yet. Add your first stop to start planning.</div>';
}

function addStopEditor(data = {}) {
  const wrap = document.createElement("div");
  wrap.className = "stop-edit-card";
  wrap.innerHTML = `
    <div class="stop-edit-head"><b>DESTINATION STOP</b><button type="button" class="text-btn remove-stop">Remove</button></div>
    <label>Destination<input class="stop-destination" required maxlength="160" value="${escapeHtml(data.destination || "")}" placeholder="e.g. Manali"></label>
    <div class="form-row">
      <label>Arrival<input class="stop-arrival" type="date" value="${escapeHtml(data.arrival_date || "")}"></label>
      <label>Departure<input class="stop-departure" type="date" value="${escapeHtml(data.departure_date || "")}"></label>
    </div>
    <div class="form-row">
      <label>Transport<input class="stop-transport" value="${escapeHtml(data.transport || "")}" placeholder="Train, flight, car..."></label>
      <label>Accommodation<input class="stop-accommodation" value="${escapeHtml(data.accommodation || "")}" placeholder="Hotel / stay"></label>
    </div>
    <label>Notes<textarea class="stop-notes" rows="2">${escapeHtml(data.notes || "")}</textarea></label>
  `;
  wrap.querySelector(".remove-stop").addEventListener("click", () => wrap.remove());
  $("stop-editor").appendChild(wrap);
}

function openTripDialog() {
  const g = state.group || {};
  $("trip-title-input").value = g.trip_title || g.name || "Our Trip";
  $("trip-start").value = g.trip_start_date || "";
  $("trip-end").value = g.trip_end_date || "";
  $("trip-budget-input").value = g.planned_trip_budget || 0;
  $("trip-notes-input").value = g.trip_notes || "";
  $("stop-editor").innerHTML = "";
  (g.trip_stops || []).forEach(s => addStopEditor(s));
  if (!(g.trip_stops || []).length) addStopEditor();
  $("trip-form-error").textContent = "";
  $("trip-dialog").showModal();
}

async function saveTrip(ev) {
  ev.preventDefault();
  const error = $("trip-form-error");
  error.textContent = "";
  try {
    const stops = [...document.querySelectorAll(".stop-edit-card")].map(card => ({
      destination: card.querySelector(".stop-destination").value.trim(),
      arrival_date: card.querySelector(".stop-arrival").value || null,
      departure_date: card.querySelector(".stop-departure").value || null,
      transport: card.querySelector(".stop-transport").value,
      accommodation: card.querySelector(".stop-accommodation").value,
      notes: card.querySelector(".stop-notes").value,
    }));
    const payload = {
      trip_title: $("trip-title-input").value.trim(),
      trip_start_date: $("trip-start").value || null,
      trip_end_date: $("trip-end").value || null,
      planned_trip_budget: Number($("trip-budget-input").value || 0),
      stops,
      notes: $("trip-notes-input").value,
    };
    await api(`/groups/${encodeURIComponent(state.groupCode)}/trip-plan`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    const refreshed = await api(`/groups/${encodeURIComponent(state.groupCode)}/summary`);
    state.group = refreshed.group;
    $("trip-dialog").close();
    renderTrip();
    renderOverview();
    toast("Trip plan updated.");
  } catch (e) {
    error.textContent = e.message;
  }
}

/* ==================== AUDIT & FORM SUBMISSIONS ==================== */

async function openAuditDialog() {
  $("audit-dialog").showModal();
  $("audit-log-stream").innerHTML = '<p class="muted">Loading audit entries...</p>';
  try {
    const data = await api("/admin/audit-logs?limit=50");
    $("audit-log-stream").innerHTML = data.audit_logs?.length
      ? data.audit_logs.map(log => `
        <div class="audit-item">
          <div class="audit-header">
            <span><b class="audit-action">${escapeHtml(log.action)}</b> by ${escapeHtml(log.actor_name)}</span>
            <span>${String(log.timestamp || "").replace("T", " ").slice(0, 19)}</span>
          </div>
          <div class="audit-notes">${escapeHtml(log.notes || "No details")}</div>
          ${log.after_state ? `<pre>${escapeHtml(JSON.stringify(log.after_state, null, 2))}</pre>` : ""}
        </div>
      `).join("")
      : '<p class="muted">No audit logs recorded yet.</p>';
  } catch (e) {
    $("audit-log-stream").innerHTML = `<p class="error-text">${escapeHtml(e.message)}</p>`;
  }
}

// Global Event Listeners
window.openSubmitModal = openSubmitModal;
window.verifyContribution = verifyContribution;
window.rejectContribution = rejectContribution;
window.reverseExpense = reverseExpense;
window.openSettleModal = openSettleModal;

$("login-form").addEventListener("submit", async ev => {
  ev.preventDefault();
  $("login-error").textContent = "";
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: $("login-email").value,
        password: $("login-password").value,
      }),
    });
    loginSuccess(data);
  } catch (e) {
    $("login-error").textContent = e.message;
  }
});

function logout() {
  sessionStorage.clear();
  state.token = null;
  state.user = null;
  $("app-shell").classList.add("hidden");
  $("login-screen").classList.remove("hidden");
}

$("logout-btn").addEventListener("click", logout);

document.querySelectorAll(".nav-link").forEach(b => b.addEventListener("click", () => showView(b.dataset.view)));
document.querySelectorAll("[data-go]").forEach(b => b.addEventListener("click", () => showView(b.dataset.go)));
$("refresh-btn").addEventListener("click", loadApp);

$("open-expense-modal").addEventListener("click", openExpenseDialog);
$("expense-form").addEventListener("submit", submitExpense);
$("split-type").addEventListener("change", renderSplitEditor);
$("expense-participants").addEventListener("change", renderSplitEditor);

$("edit-trip-btn").addEventListener("click", openTripDialog);
$("trip-form").addEventListener("submit", saveTrip);
$("add-stop-btn").addEventListener("click", () => addStopEditor());

// Kitty Submit Form
$("kitty-submit-form").addEventListener("submit", async ev => {
  ev.preventDefault();
  const id = $("submit-contrib-id").value;
  const error = $("kitty-submit-error");
  error.textContent = "";
  try {
    await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/contributions/${id}/submit`, {
      method: "POST",
      body: JSON.stringify({
        utr_reference: $("submit-utr").value.trim(),
        payment_date: $("submit-date").value,
        proof_url: $("submit-proof-url").value.trim() || null,
        notes: $("submit-notes").value.trim(),
      }),
    });
    $("kitty-submit-dialog").close();
    toast("UTR reference submitted for admin verification.");
    await refreshKitty();
  } catch (e) {
    error.textContent = e.message;
  }
});

// Kitty Disbursement Form
$("open-disbursement-modal")?.addEventListener("click", () => {
  $("disb-amount").value = "";
  $("disb-date").value = dateToday();
  $("disb-recipient").value = "";
  $("disb-desc").value = "";
  $("kitty-disb-error").textContent = "";
  $("kitty-disbursement-dialog").showModal();
});

$("kitty-disbursement-form")?.addEventListener("submit", async ev => {
  ev.preventDefault();
  const error = $("kitty-disb-error");
  error.textContent = "";
  try {
    await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/disbursements`, {
      method: "POST",
      body: JSON.stringify({
        amount: Number($("disb-amount").value),
        category: $("disb-category").value,
        description: $("disb-desc").value.trim(),
        recipient: $("disb-recipient").value.trim(),
        disbursement_date: $("disb-date").value,
      }),
    });
    $("kitty-disbursement-dialog").close();
    toast("Disbursement recorded and deducted from Kitty balance.");
    await refreshKitty();
  } catch (e) {
    error.textContent = e.message;
  }
});

// Kitty Bank Reconciliation Form
$("open-reconcile-modal")?.addEventListener("click", () => {
  $("reconcile-actual-bal").value = state.kittySummary?.kitty_balance || 0;
  $("reconcile-notes").value = "";
  $("reconcile-apply-adjust").checked = false;
  $("reconcile-error").textContent = "";
  $("kitty-reconcile-dialog").showModal();
});

$("kitty-reconcile-form")?.addEventListener("submit", async ev => {
  ev.preventDefault();
  const error = $("reconcile-error");
  error.textContent = "";
  try {
    const res = await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/reconcile`, {
      method: "POST",
      body: JSON.stringify({
        actual_bank_balance: Number($("reconcile-actual-bal").value),
        notes: $("reconcile-notes").value.trim(),
        apply_adjustment: $("reconcile-apply-adjust").checked,
      }),
    });
    $("kitty-reconcile-dialog").close();
    toast(`Audit completed. Status: ${res.status} (Variance: ₹${res.variance})`);
    await refreshKitty();
  } catch (e) {
    error.textContent = e.message;
  }
});

// Settlement Proposal Form
$("settle-form")?.addEventListener("submit", async ev => {
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
    toast("Settlement payment proposed. Recipient can now confirm receipt.");
    await refreshExpenses();
  } catch (e) {
    error.textContent = e.message;
  }
});

// Reminders & Audit Log Buttons
$("send-reminders-btn")?.addEventListener("click", async () => {
  try {
    const res = await api(`/groups/${encodeURIComponent(state.groupCode)}/kitty/reminders?month_index=1`, {
      method: "POST",
    });
    toast(res.message);
  } catch (e) {
    toast(e.message);
  }
});

$("audit-btn")?.addEventListener("click", openAuditDialog);
$("select-all-participants")?.addEventListener("click", () => selectAllParticipants(true));
$("clear-participants")?.addEventListener("click", () => selectAllParticipants(false));
$("mobile-logout-btn")?.addEventListener("click", logout);
document.querySelectorAll("[data-close]").forEach(b => b.addEventListener("click", () => $(b.dataset.close).close()));

// Auto-restore session on page load
(async () => {
  const token = sessionStorage.getItem("edith_token");
  const user = sessionStorage.getItem("edith_user");
  if (token && user) {
    loginSuccess({ access_token: token, user: JSON.parse(user) });
  }
})();
