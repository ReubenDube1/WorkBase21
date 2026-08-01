/* ==========================================================================
   WorkBase21 — main.js
   Vanilla JavaScript only. No jQuery, no frameworks.
   ========================================================================== */
document.addEventListener('DOMContentLoaded', function () {

  /* ---------------------------------------------------------------------
     1. Navbar shadow while scrolling
     --------------------------------------------------------------------- */
  var header = document.getElementById('site-header');
  function updateHeaderShadow() {
    if (!header) return;
    if (window.scrollY > 8) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  }
  updateHeaderShadow();
  window.addEventListener('scroll', updateHeaderShadow, { passive: true });

  /* ---------------------------------------------------------------------
     2. Mobile hamburger menu
     --------------------------------------------------------------------- */
  var hamburger = document.getElementById('hamburger');
  var mainNav = document.getElementById('main-nav');

  if (hamburger && mainNav) {
    hamburger.addEventListener('click', function () {
      var isOpen = mainNav.classList.toggle('open');
      hamburger.classList.toggle('open', isOpen);
      hamburger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    // Close the mobile menu when a link inside it is tapped.
    mainNav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        mainNav.classList.remove('open');
        hamburger.classList.remove('open');
        hamburger.setAttribute('aria-expanded', 'false');
      });
    });

    // Close menu on outside click.
    document.addEventListener('click', function (event) {
      var clickedInsideNav = mainNav.contains(event.target) || hamburger.contains(event.target);
      if (!clickedInsideNav) {
        mainNav.classList.remove('open');
        hamburger.classList.remove('open');
        hamburger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ---------------------------------------------------------------------
     3. Back-to-top button
     --------------------------------------------------------------------- */
  var backToTop = document.getElementById('back-to-top');
  if (backToTop) {
    function toggleBackToTop() {
      if (window.scrollY > 480) {
        backToTop.classList.add('visible');
      } else {
        backToTop.classList.remove('visible');
      }
    }
    toggleBackToTop();
    window.addEventListener('scroll', toggleBackToTop, { passive: true });

    backToTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* ---------------------------------------------------------------------
     4. Smooth scrolling for in-page anchor links (e.g. #section-id)
     --------------------------------------------------------------------- */
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      var targetId = this.getAttribute('href');
      if (targetId.length > 1) {
        var target = document.querySelector(targetId);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  });

  /* ---------------------------------------------------------------------
     5. Fade-in animation while scrolling (job cards, content blocks)
     --------------------------------------------------------------------- */
  var fadeEls = document.querySelectorAll('.fade-in');
  if ('IntersectionObserver' in window && fadeEls.length) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });

    fadeEls.forEach(function (el) { observer.observe(el); });
  } else {
    // Fallback: no IntersectionObserver support — just show everything.
    fadeEls.forEach(function (el) { el.classList.add('in-view'); });
  }

  /* ---------------------------------------------------------------------
     6. Search box micro-animation (focus pulse)
     --------------------------------------------------------------------- */
  document.querySelectorAll('.nav-search, .hero-search').forEach(function (box) {
    var input = box.querySelector('input');
    if (!input) return;
    input.addEventListener('focus', function () {
      box.style.transform = 'scale(1.01)';
    });
    input.addEventListener('blur', function () {
      box.style.transform = 'scale(1)';
    });
  });

});
