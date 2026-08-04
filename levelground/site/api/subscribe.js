const GROUP_ID = '192298904311563903'; // Level Ground Leads

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  const { email, name } = req.body || {};
  if (!email || typeof email !== 'string' || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    res.status(400).json({ error: 'Valid email required' });
    return;
  }
  if (!name || typeof name !== 'string' || !name.trim()) {
    res.status(400).json({ error: 'Name required' });
    return;
  }

  try {
    const mlRes = await fetch('https://connect.mailerlite.com/api/subscribers', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${process.env.MAILERLITE_API_KEY}`
      },
      body: JSON.stringify({ email, fields: { name: name.trim() }, groups: [GROUP_ID] })
    });

    if (!mlRes.ok) {
      const detail = await mlRes.text();
      console.error('MailerLite error', mlRes.status, detail);
      res.status(502).json({ error: 'Subscribe failed' });
      return;
    }

    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('Subscribe handler error', err);
    res.status(500).json({ error: 'Server error' });
  }
};
