// main.js — Interaktivitas portofolio AI Agent Developer

window.addEventListener("load", function () {
  initSmoothScroll();
  initNavToggle();
  initRevealOnScroll();
  initTypewriter();
});

// ===== SMOOTH SCROLL =====
function initSmoothScroll() {
  const links = document.querySelectorAll('a[href^="#"]');
  links.forEach(function (link) {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute("href"));
      if (target) {
        target.scrollIntoView({ behavior: "smooth" });
      }
    });
  });
}

// ===== TOGGLE NAV MOBILE =====
function initNavToggle() {
  const toggle = document.getElementById("nav-toggle");
  const menu = document.getElementById("nav-menu");
  if (!toggle || !menu) return;

  toggle.addEventListener("click", function () {
    const isOpen = menu.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(isOpen));
  });
}

// ===== REVEAL ON SCROLL =====
function initRevealOnScroll() {
  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  document.querySelectorAll(".reveal").forEach(function (el) {
    observer.observe(el);
  });
}

// ===== TYPEWRITER EFFECT ON HERO TITLE =====
function initTypewriter() {
  const typewriterEl = document.getElementById("typewriter");
  if (!typewriterEl) return;

  const phrases = ["Developer", "AI Engineer", "Automation Specialist"];
  let phraseIndex = 0;
  let charIndex = 0;
  let isDeleting = false;

  function type() {
    const currentPhrase = phrases[phraseIndex];

    if (isDeleting) {
      charIndex--;
      typewriterEl.textContent = currentPhrase.slice(0, charIndex);
    } else {
      charIndex++;
      typewriterEl.textContent = currentPhrase.slice(0, charIndex);
    }

    let delay = isDeleting ? 80 : 150;
    if (!isDeleting && charIndex === currentPhrase.length) {
      delay = 2000;
      isDeleting = true;
    } else if (isDeleting && charIndex === 0) {
      isDeleting = false;
      phraseIndex = (phraseIndex + 1) % phrases.length;
      delay = 500;
    }

    setTimeout(type, delay);
  }

  type();
}
