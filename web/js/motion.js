// Scroll-reveal for static sections. Content stays visible without JS,
// without IntersectionObserver, and for people who ask for less motion.
const REVEAL_THRESHOLD = 0.12;  // share of the element visible before it appears

export function initReveal() {
  const targets = [...document.querySelectorAll(".reveal")];
  const canAnimate =
    "IntersectionObserver" in window &&
    !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!canAnimate) return;
  document.documentElement.classList.add("motion-ready");
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add("in");
      observer.unobserve(entry.target);
    }
  }, { threshold: REVEAL_THRESHOLD });
  for (const target of targets) observer.observe(target);
}
