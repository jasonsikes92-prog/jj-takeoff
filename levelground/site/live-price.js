// Keeps the advertised price honest once the founding 10 are gone.
//
// The pages are authored with the founding price in the markup, so while spots
// remain this does nothing at all — no flash, no layout shift. It only rewrites
// copy in the sold-out case. If the request fails the page is left as authored;
// Stripe Checkout still shows the real amount before anyone pays.
(function () {
  function soldOut(price) {
    var amt = document.querySelector('.price-top .amt');
    if (amt) amt.textContent = price;

    var was = document.querySelector('.price-top .was');
    if (was) was.textContent = 'Founding spots are gone — standard price';

    var btn = document.getElementById('foundingBtn');
    if (btn) btn.textContent = 'Get my report';

    // "from $99" on the two report cards
    var cards = document.querySelectorAll('.card .price b');
    for (var i = 0; i < cards.length; i++) cards[i].textContent = price;

    // start.html banner + its submit button
    var banner = document.querySelector('.founding');
    if (banner) {
      banner.innerHTML = '<b>' + price + ' per report</b> — the founding 10 are gone. ' +
        "Full refund if you're not satisfied, no questions asked.";
    }
    var submits = document.querySelectorAll('form button[type=submit]');
    for (var j = 0; j < submits.length; j++) {
      if (submits[j].textContent.indexOf('founding') !== -1) {
        submits[j].textContent = 'Reserve my spot';
      }
    }
  }

  fetch('/api/pricing')
    .then(function (r) { return r.json(); })
    .then(function (p) {
      if (!p || p.tier !== 'standard' || !p.amount) return;
      soldOut('$' + Math.round(p.amount / 100));
    })
    .catch(function () {});
})();
