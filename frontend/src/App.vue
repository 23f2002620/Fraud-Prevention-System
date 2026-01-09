<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { getCases, updateCaseStatus, scoreTxn, createCase } from "./api";

const cases = ref([]);
const statusFilter = ref("");
const loading = ref(false);
const error = ref("");
const lastUpdated = ref(null);

const txn = ref({
  txn_id: "demo-txn-1",
  user_id: "demo-user-1",
  amount: 1000,
  currency: "INR",
  country: "IN",
  device_id: "device-1",
  ip: "1.2.3.4"
});

const scoreResult = ref(null);

/* ======================
   DATA FETCH
====================== */
async function refresh() {
  if (loading.value) return;

  loading.value = true;
  error.value = "";
  try {
    cases.value = await getCases(statusFilter.value);
    lastUpdated.value = new Date();
  } catch (e) {
    error.value = e.message || String(e);
  } finally {
    loading.value = false;
  }
}

// background polling without hiding the table
async function poll() {
  if (loading.value) return;
  try {
    const latest = await getCases(statusFilter.value);
    cases.value = latest;
    lastUpdated.value = new Date();
  } catch (e) {
    // keep current data, just surface the error
    error.value = e.message || String(e);
  }
}

async function mark(caseId, newStatus) {
  try {
    await updateCaseStatus(caseId, newStatus);
    await refresh();
  } catch (e) {
    error.value = e.message || String(e);
  }
}

function badgeClass(s) {
  if (s === "CONFIRMED_FRAUD") return "badge fraud";
  if (s === "FALSE_POSITIVE") return "badge fp";
  return "badge open";
}

const openCount = computed(() => cases.value.filter(c => c.status === "OPEN").length);
const fraudCount = computed(() => cases.value.filter(c => c.status === "CONFIRMED_FRAUD").length);
const fpCount = computed(() => cases.value.filter(c => c.status === "FALSE_POSITIVE").length);
const totalCases = computed(() => cases.value.length);
const avgRisk = computed(() => {
  if (!cases.value.length) return 0;
  const total = cases.value.reduce((sum, c) => sum + Number(c.risk_score || 0), 0);
  return total / cases.value.length;
});
const highRiskCount = computed(() => cases.value.filter(c => Number(c.risk_score || 0) >= 0.7).length);
const lastUpdatedLabel = computed(() => lastUpdated.value ? lastUpdated.value.toLocaleTimeString() : "—");
const riskLevel = computed(() => {
  const r = avgRisk.value;
  if (r < 0.3) return "risk-low";
  if (r < 0.7) return "risk-med";
  return "risk-high";
});

async function doScore() {
  error.value = "";
  scoreResult.value = null;
  try {
    scoreResult.value = await scoreTxn(txn.value);
  } catch (e) {
    error.value = e.message || String(e);
  }
}

async function openCaseFromScore() {
  if (!scoreResult.value) return;
  try {
    await createCase({
      txn_id: txn.value.txn_id,
      user_id: txn.value.user_id,
      amount: Number(txn.value.amount),
      currency: txn.value.currency,
      risk_score: scoreResult.value.risk_score,
      reasons: scoreResult.value.reasons
    });
    await refresh();
  } catch (e) {
    error.value = e.message || String(e);
  }
}

/* ======================
   AUTO REFRESH (POLLING)
====================== */
let poller = null;

onMounted(() => {
  refresh(); // initial load
  poller = setInterval(poll, 2000); // smooth live updates without full reload
});

onUnmounted(() => {
  if (poller) clearInterval(poller);
});
</script>

<template>
  <div class="page-root">
    <div class="container">
    <header class="header">
      <div>
        <h1>Fraud Monitoring Dashboard</h1>
        <p class="subtitle">
          Real-time transaction scoring & case management
        </p>
      </div>
      <div class="header-meta">
        <div class="live-pill">
          <span class="dot"></span>
          Live stream
        </div>
        <div class="muted">Updated: {{ lastUpdatedLabel }}</div>
      </div>
    </header>

    <section class="stats-grid">
      <div class="stat stat-neutral">
        <p class="stat-label">Total cases</p>
        <div class="stat-value">{{ totalCases }}</div>
      </div>
      <div class="stat stat-open">
        <p class="stat-label">Open</p>
        <div class="stat-value text-blue">{{ openCount }}</div>
      </div>
      <div class="stat stat-fraud">
        <p class="stat-label">Confirmed fraud</p>
        <div class="stat-value text-red">{{ fraudCount }}</div>
      </div>
      <div class="stat stat-fp">
        <p class="stat-label">False positives</p>
        <div class="stat-value text-green">{{ fpCount }}</div>
      </div>
      <div :class="['stat', 'stat-risk', riskLevel]">
        <p class="stat-label">Avg risk</p>
        <div class="stat-value">{{ Number(avgRisk).toFixed(2) }}</div>
      </div>
      <div :class="['stat', 'stat-risk', riskLevel]">
        <p class="stat-label">High risk (&ge; 0.7)</p>
        <div class="stat-value text-amber">{{ highRiskCount }}</div>
      </div>
    </section>

    <!-- CASE LIST -->
    <section class="card">
      <div class="card-header">
        <div>
          <h2>Cases</h2>
          <p class="muted small">Track investigations and triage quickly</p>
        </div>

        <div class="filters">
          <select v-model="statusFilter" @change="refresh">
            <option value="">All statuses</option>
            <option value="OPEN">OPEN</option>
            <option value="CONFIRMED_FRAUD">CONFIRMED_FRAUD</option>
            <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
          </select>
          <button @click="refresh" class="btn secondary">Refresh</button>
        </div>
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <div v-if="loading" class="skeleton-table">
        <div class="skeleton-row" v-for="i in 4" :key="i"></div>
      </div>

      <div v-else class="table-scroll">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Transaction</th>
              <th>User</th>
              <th>Amount</th>
              <th>Risk</th>
              <th>Status</th>
              <th>Reasons</th>
              <th>Actions</th>
            </tr>
          </thead>

          <transition-group name="rows" tag="tbody">
            <tr v-for="c in cases" :key="c.id">
              <td class="muted">#{{ c.id }}</td>
              <td>
                <div class="cell-title">{{ c.txn_id }}</div>
                <div class="muted small">Currency: {{ c.currency }}</div>
              </td>
              <td>
                <div class="cell-title">{{ c.user_id }}</div>
                <div class="muted small">Device: {{ c.device_id || "n/a" }}</div>
              </td>
              <td>{{ c.amount }}</td>
              <td>
                <div class="risk-meter">
                  <div class="risk-fill" :style="{ width: `${Math.min(Number(c.risk_score || 0) * 100, 100)}%` }"></div>
                </div>
                <div class="muted small">{{ Number(c.risk_score || 0).toFixed(2) }}</div>
              </td>
              <td>
                <span :class="badgeClass(c.status)">
                  {{ c.status }}
                </span>
              </td>
              <td class="muted reasons">
                {{ Array.isArray(c.reasons) ? c.reasons.join(", ") : c.reasons }}
              </td>
              <td class="actions">
                <div class="actions-group">
                  <button class="btn small" @click="mark(c.id, 'OPEN')">Open</button>
                  <button class="btn small danger" @click="mark(c.id, 'CONFIRMED_FRAUD')">Fraud</button>
                  <button class="btn small warn" @click="mark(c.id, 'FALSE_POSITIVE')">FP</button>
                </div>
              </td>
            </tr>

            <tr v-if="cases.length === 0" key="empty">
              <td colspan="8" class="empty">
                <div class="empty-box">
                  <p class="cell-title">No cases yet</p>
                  <p class="muted small">Transactions will appear as they are scored.</p>
                </div>
              </td>
            </tr>
          </transition-group>
        </table>
      </div>
    </section>

    <!-- SCORING -->
    <section class="card score-section">
      <div class="card-header">
        <div>
          <h2>Score Transaction</h2>
          <p class="muted small">Simulate a transaction and instantly see how the engine responds.</p>
        </div>
        <div class="pill">Manual test</div>
      </div>

      <div class="score-layout">
        <div class="score-form">
          <div class="form-grid">
            <input v-model="txn.txn_id" placeholder="Transaction ID" />
            <input v-model="txn.user_id" placeholder="User ID" />
            <input v-model.number="txn.amount" type="number" placeholder="Amount" />
            <input v-model="txn.currency" placeholder="Currency" />
            <input v-model="txn.country" placeholder="Country" />
            <input v-model="txn.device_id" placeholder="Device ID" />
            <input v-model="txn.ip" placeholder="IP Address" />
          </div>

          <div class="actions-row">
            <button class="btn primary" @click="doScore">Score</button>
            <button
              class="btn secondary"
              :disabled="!scoreResult"
              @click="openCaseFromScore"
            >
              Open Case
            </button>
          </div>
        </div>

        <div class="score-preview">
          <h3 class="preview-title">Live score preview</h3>
          <p class="muted small">Payload sent to the scoring API:</p>
          <pre class="payload-preview">{{ JSON.stringify(txn, null, 2) }}</pre>

          <div v-if="scoreResult" class="score-box">
            <div class="score-value">
              <div class="muted small">Risk Score</div>
              <div class="score-number">{{ Number(scoreResult.risk_score).toFixed(2) }}</div>
            </div>
            <div class="muted">
              Reasons: {{ scoreResult.reasons.join(", ") }}
            </div>
          </div>
          <div v-else class="muted small score-placeholder">
            Run a score to see the fraud engine output.
          </div>
        </div>
      </div>
    </section>
    </div>
  </div>
</template>
