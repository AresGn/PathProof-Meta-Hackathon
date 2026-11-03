// Landing page: language switch and scroll reveal only. The demo itself lives
// in demo.html and js/app.js.
import { applyTranslations, setLanguage } from "./i18n.js";
import { initReveal } from "./motion.js";

for (const btn of document.querySelectorAll("[data-set-lang]")) {
  btn.addEventListener("click", () => {
    setLanguage(btn.dataset.setLang);
    applyTranslations();
  });
}

applyTranslations();
initReveal();
