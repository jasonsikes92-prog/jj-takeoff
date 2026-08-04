import Stripe from 'stripe';

// Edge runtime on purpose. Vercel's Node runtime always parses a JSON body and
// exposes no raw bytes (no req.rawBody, stream already drained, and
// `config.api.bodyParser` is ignored) — so a Stripe signature can never be
// verified there. Edge hands us a Web Request, and request.text() is the exact
// payload Stripe signed. Verified against Vercel CLI 57 / @vercel/node.
export const config = { runtime: 'edge' };

// No apiVersion needed: this client only verifies signatures locally and never
// calls the Stripe API, so there is no version to pin here.
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
  httpClient: Stripe.createFetchHttpClient()
});

// Edge has no Node crypto; verification uses SubtleCrypto, which is async.
const cryptoProvider = Stripe.createSubtleCryptoProvider();

export default async function handler(request) {
  if (request.method !== 'POST') {
    return Response.json({ error: 'Method not allowed' }, { status: 405 });
  }

  const secret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!secret) {
    console.error('STRIPE_WEBHOOK_SECRET is not set');
    return Response.json({ error: 'Server error' }, { status: 500 });
  }

  let event;
  try {
    const body = await request.text();
    event = await stripe.webhooks.constructEventAsync(
      body,
      request.headers.get('stripe-signature'),
      secret,
      undefined,
      cryptoProvider
    );
  } catch (err) {
    console.error('Webhook signature verification failed', err.message);
    return Response.json({ error: 'Invalid signature' }, { status: 400 });
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const s = event.data.object;
        if (s.payment_status === 'paid') {
          console.log('PAID', {
            session: s.id,
            email: s.customer_details?.email,
            name: s.metadata?.client_name,
            reference: s.metadata?.reference,
            tier: s.metadata?.tier,
            amount: s.amount_total
          });
        }
        break;
      }
      case 'charge.refunded':
        console.log('REFUNDED', { charge: event.data.object.id });
        break;
      default:
        break;
    }
  } catch (err) {
    // A 500 tells Stripe to retry.
    console.error('Webhook handling error', event.type, err.message);
    return Response.json({ error: 'Handler error' }, { status: 500 });
  }

  return Response.json({ received: true });
}
