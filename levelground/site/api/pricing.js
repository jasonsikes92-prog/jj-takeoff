const { TIERS, FOUNDING_SPOTS, foundingSpotsUsed } = require('../lib/stripe');

// Read-only: what a visitor would be charged right now. Deliberately does NOT
// return the sold count — the pages don't need it, and it's sales data.
module.exports = async (req, res) => {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    const used = await foundingSpotsUsed();
    const tier = used < FOUNDING_SPOTS ? 'founding' : 'standard';

    // Counting sessions on every page view would be wasteful, so let the CDN
    // hold it briefly — but max-age=0 keeps browsers revalidating. Without that,
    // a visitor's browser can pin a stale price for the life of its cache, which
    // is the exact thing this endpoint exists to prevent.
    res.setHeader('Cache-Control', 'public, max-age=0, s-maxage=60, stale-while-revalidate=300');
    res.status(200).json({ tier, amount: TIERS[tier].amount });
  } catch (err) {
    console.error('pricing error', err.message);
    res.status(500).json({ error: 'Could not load pricing' });
  }
};
