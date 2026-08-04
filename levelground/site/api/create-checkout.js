const crypto = require('crypto');
const { stripe, TIERS, FOUNDING_SPOTS, foundingSpotsUsed } = require('../lib/stripe');

// Tags these sessions in the Stripe Dashboard so the self-serve button can be
// compared against the links Jason sends by hand.
const INTEGRATION_ID = 'lg_report_checkout_qvbxmnrt';

// Is this Jason (emailing someone a link) rather than a visitor clicking the
// button? Only he may pin a tier — see the guard below.
function authorized(req) {
  const expected = process.env.LG_ADMIN_TOKEN;
  if (!expected) return false;

  const header = req.headers.authorization || '';
  const presented = header.startsWith('Bearer ') ? header.slice(7) : '';

  const a = Buffer.from(presented);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }
  const isAdmin = authorized(req);
  const { email, name, tier, reference } = req.body || {};

  // Public callers may not name their own price. Without this, anyone could
  // POST {"tier":"founding"} forever and buy a $299 report for $99.
  if (tier && !isAdmin) {
    res.status(403).json({ error: 'Tier cannot be set' });
    return;
  }
  if (tier && !TIERS[tier]) {
    res.status(400).json({ error: 'Unknown tier' });
    return;
  }

  // Email is optional for the public button — Stripe Checkout collects it.
  // When it is supplied (Jason prefilling a link), it has to be real.
  if (email !== undefined && (typeof email !== 'string' || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))) {
    res.status(400).json({ error: 'Valid email required' });
    return;
  }

  try {
    // Default to whatever the founding cap says; an explicit tier lets Jason
    // honour a price he already promised someone.
    let chosen = tier;
    let used = null;
    if (!chosen) {
      used = await foundingSpotsUsed();
      chosen = used < FOUNDING_SPOTS ? 'founding' : 'standard';
    }
    const { amount, label } = TIERS[chosen];

    const origin = process.env.SITE_ORIGIN || 'https://www.getlevelground.com';

    const session = await stripe().checkout.sessions.create({
      mode: 'payment',
      ...(email ? { customer_email: email } : {}),
      integration_identifier: INTEGRATION_ID,
      line_items: [{
        quantity: 1,
        price_data: {
          currency: 'usd',
          unit_amount: amount,
          product_data: {
            name: label,
            description: 'An independent review of your plans and your builder’s bid by a working custom-home builder.'
          }
        }
      }],
      metadata: {
        product: 'risk_gap_report',
        tier: chosen,
        client_name: (name || '').trim().slice(0, 100),
        reference: (reference || '').trim().slice(0, 100)
      },
      success_url: `${origin}/paid.html?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${origin}/#pricing`
    });

    res.status(200).json({
      url: session.url,
      id: session.id,
      tier: chosen,
      amount,
      founding_spots_used: used
    });
  } catch (err) {
    console.error('create-checkout error', err.message);
    res.status(500).json({ error: 'Could not create checkout session' });
  }
};
