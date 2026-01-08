<script setup>
import { onMounted, ref } from "vue";
import { getCases, updateCaseStatus, scoreTxn, createCase } from "./api";
import { login } from "./api";


const cases = ref([]);
const statusFilter = ref("");

const loading = ref(false);
const error = ref("");

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

async function refresh() {
  loading.value = true;
  error.value = "";
  try {
    cases.value = await getCases(statusFilter.value);
  } catch (e) {
    error.value = e.message || String(e);
  } finally {
    loading.value = false;
  }
}

async function mark(caseId, newStatus) {
  error.value = "";
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
  error.value = "";
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

onMounted(async () => {
  try {
    await login("admin", "admin123");
    await refresh();
  } catch (e) {
    error.value = e.message || String(e);
  }
});





</script>

<template>
  <div class="container">
    <h2>Fraud Monitor</h2>
    <p class="muted">Score a transaction → open a case → review and update status.</p>

    <div class="card" style="margin-bottom: 14px;">
      <div class="row">
        <label class="muted">Status filter</label>
        <select v-model="statusFilter">
          <option value="">All</option>
          <option value="OPEN">OPEN</option>
          <option value="CONFIRMED_FRAUD">CONFIRMED_FRAUD</option>
          <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
        </select>
        <button class="secondary" @click="refresh">Refresh</button>
      </div>

      <div v-if="error" style="margin-top:10px; color:#b91c1c;">
        {{ error }}
      </div>

      <div v-if="loading" class="muted" style="margin-top:10px;">Loading...</div>

      <table v-if="!loading">
        <thead>
          <tr>
            <th>ID</th>
            <th>Txn</th>
            <th>User</th>
            <th>Amount</th>
            <th>Risk</th>
            <th>Status</th>
            <th>Reasons</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in cases" :key="c.id">
            <td>{{ c.id }}</td>
            <td>{{ c.txn_id }}</td>
            <td>{{ c.user_id }}</td>
            <td>{{ c.amount }} {{ c.currency }}</td>
            <td>{{ Number(c.risk_score).toFixed(2) }}</td>
            <td><span :class="badgeClass(c.status)">{{ c.status }}</span></td>
            <td class="muted">{{ c.reasons }}</td>
            <td>
              <div class="row">
                <button class="secondary" @click="mark(c.id, 'OPEN')">Open</button>
                <button class="secondary" @click="mark(c.id, 'CONFIRMED_FRAUD')">Fraud</button>
                <button class="secondary" @click="mark(c.id, 'FALSE_POSITIVE')">FP</button>
              </div>
            </td>
          </tr>
          <tr v-if="cases.length === 0">
            <td colspan="8" class="muted">No cases.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <h3>Score a transaction</h3>
      <div class="row">
        <input v-model="txn.txn_id" placeholder="txn_id" />
        <input v-model="txn.user_id" placeholder="user_id" />
        <input v-model.number="txn.amount" type="number" placeholder="amount" />
        <input v-model="txn.currency" placeholder="currency" style="width: 90px;" />
        <input v-model="txn.country" placeholder="country" style="width: 90px;" />
        <input v-model="txn.device_id" placeholder="device_id" />
        <input v-model="txn.ip" placeholder="ip" />
      </div>

      <div class="row" style="margin-top: 10px;">
        <button @click="doScore">Score</button>
        <button class="secondary" :disabled="!scoreResult" @click="openCaseFromScore">
          Open case from score
        </button>
      </div>

      <div v-if="scoreResult" style="margin-top: 10px;">
        <div><b>Risk:</b> {{ Number(scoreResult.risk_score).toFixed(2) }}</div>
        <div class="muted">Reasons: {{ scoreResult.reasons.join(", ") }}</div>
      </div>
    </div>
  </div>
</template>
