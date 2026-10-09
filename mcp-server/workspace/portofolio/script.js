(() => {
  const nav = document.querySelector('.nav');
  const toggle = document.querySelector('#navToggle');
  const links = document.querySelector('#navLinks');

  const closeMenu = () => {
    links?.classList.remove('is-open');
    toggle?.setAttribute('aria-expanded', 'false');
  };

  toggle?.addEventListener('click', () => {
    const isOpen = links.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(isOpen));
  });

  links?.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', closeMenu);
  });

  const updateNav = () => {
    nav?.classList.toggle('is-scrolled', window.scrollY > 20);
  };
  window.addEventListener('scroll', updateNav, { passive: true });
  updateNav();

  const reveals = document.querySelectorAll('[data-reveal]');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    reveals.forEach((item) => observer.observe(item));
  } else {
    reveals.forEach((item) => item.classList.add('is-visible'));
  }

  document.querySelectorAll('[data-count]').forEach((element) => {
    const target = Number(element.dataset.count);
    const duration = 1400;
    const start = performance.now();

    const animate = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = Math.round(target * eased).toLocaleString('id-ID');
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  });

const year = document.getElementById('year');
if (year) {
  year.textContent = new Date().getFullYear();
}

})();