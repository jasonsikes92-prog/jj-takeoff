const Stripe = require('stripe');

// Pinned so a Stripe-side version bump can never change behaviour without a deploy.
const API_VERSION = '2026-06-24.dahlia';

// Report tiers. The server is the only place a price is ever decided — the
// browser never sends an amount.
const TIERS = {
  founding: { amount: 9900, label: 'Risk & Gap Report — founding price' },
  standard: { amount: 29900, label: 'Risk & Gap Report' }
};

const FOUNDING_SPOTS = 10;

let client;

function stripe() {
  if (!client) {
    const key = process.env.STRIPE_SECRET_KEY;
    if (!key) throw new Error('STRIPE_SECRET_KEY is not set');
    client = new Stripe(key, { apiVersion: API_VERSION });
  }
  return client;
}

// How many reports have actually been paid for, per Stripe. Stripe is the
// source of truth so the founding cap survives without a database.
async function foundingSpotsUsed() {
  let used = 0;
  let startingAfter;

  for (let page = 0; page < 5; page++) {
    const params = { limit: 100, status: 'complete' };
    if (startingAfter) params.starting_after = startingAfter;

    const sessions = await stripe().checkout.sessions.list(params);
    for (const s of sessions.data) {
      if (s.metadata && s.metadata.product === 'risk_gap_report' && s.payment_status === 'paid') {
        used++;
      }
    }
    if (!sessions.has_more || sessions.data.length === 0) return used;
    startingAfter = sessions.data[sessions.data.length - 1].id;
  }

  return used;
}

module.exports = { stripe, TIERS, FOUNDING_SPOTS, foundingSpotsUsed, API_VERSION };
