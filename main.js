// Карточка вопроса стоит на месте, пока её читают: лента перерисовывается (новые сообщения встают над карточкой,
// под ней растёт полоса очереди), и карточку сталкивало вниз или дёргало у низа. Держим её верх там, где он был;
// прокрутил сам — новое место запоминается, карточка ушла из вида — не держим.
const USER = 700;   // мс после колеса, касания или клавиш: прокрутка — от человека, её не правим

export default function register() {
  let feed = null, key = null, y = null, userAt = 0, mo = null, ro = null;

  const visible = (f) => {
    const box = f.getBoundingClientRect();
    return [...f.querySelectorAll(".ask-card")].find((c) => {
      if (c.hidden) return false;
      const r = c.getBoundingClientRect();
      return r.height > 0 && r.bottom > box.top && r.top < box.bottom;
    });
  };
  const idOf = (c) => (c.dataset.asker || c.dataset.session || "") + ":" + (c.dataset.ask || "");
  const topOf = (c) => c.getBoundingClientRect().top - feed.getBoundingClientRect().top;
  const find = () => (key ? [...feed.querySelectorAll(".ask-card")].find((c) => !c.hidden && idOf(c) === key) : null);

  function remember() {
    const c = feed && visible(feed);
    key = c ? idOf(c) : null;
    y = c ? topOf(c) : null;
  }

  function hold() {
    if (!feed || !feed.isConnected) return attach();
    if (Date.now() - userAt < USER) return remember();
    const c = find();
    if (!c || y == null) return remember();
    const dy = topOf(c) - y;
    if (Math.abs(dy) >= 1) feed.scrollTop += dy;
    if (!visible(feed)) remember();
  }

  function attach() {
    const f = document.querySelector("main .feed");
    if (f === feed) return;
    feed = f;
    key = y = null;
    if (!feed) return;
    const user = () => { userAt = Date.now(); };
    for (const ev of ["wheel", "touchmove", "keydown", "pointerdown"]) feed.addEventListener(ev, user, { passive: true });
    // прокрутка не от человека (страница тянет ленту к низу) — вернуть карточку
    feed.addEventListener("scroll", () => (Date.now() - userAt < USER ? remember() : hold()), { passive: true });
    remember();
  }

  // наблюдатель размеров — заново после каждой перерисовки: страница заводит свой (тянуть к низу) при перерисовке,
  // а наблюдатели зовутся по порядку создания — наш должен быть последним, чтобы поправить после неё
  function watch() {
    ro?.disconnect();
    if (!feed) return;
    ro = new ResizeObserver(hold);
    const inner = feed.querySelector(".feed-inner");
    if (inner) ro.observe(inner);
    ro.observe(feed);
  }

  mo = new MutationObserver(() => { attach(); watch(); hold(); });
  mo.observe(document.body, { childList: true, subtree: true });
  document.addEventListener("keydown", (e) => { if (e.target?.closest?.("main .feed")) userAt = Date.now(); });
  attach();
  watch();
}
