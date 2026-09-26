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
  }, { threshold: 0.05, rootMargin: '0px 0px -20px 0px' });

  fadeEls.forEach(function (el) {
    // Immediately show anything already visible in the viewport
    var rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight && rect.bottom > 0) {
      el.classList.add('in-view');
    } else {
      observer.observe(el);
    }
  });
} else {
  // Fallback: no IntersectionObserver support — just show everything
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

  /* ---------------------------------------------------------------------
     7. Voice search (Web Speech API) — lets job seekers speak instead
     of typing in either search box. Submits the form automatically
     once speech is recognised. Silently hides the mic button on
     browsers that don't support it (e.g. Firefox), so nothing breaks.
     --------------------------------------------------------------------- */
  var SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;

  document.querySelectorAll('[data-voice-search-btn]').forEach(function (micBtn) {
    if (!SpeechRecognitionCtor) {
      micBtn.style.display = 'none';
      return;
    }

    var form = micBtn.closest('form');
    var input = form ? form.querySelector('input[name="q"]') : null;
    if (!input) return;

    var recognition = new SpeechRecognitionCtor();
    recognition.lang = 'en-ZA';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    var listening = false;

    recognition.addEventListener('start', function () {
      listening = true;
      micBtn.classList.add('listening');
      micBtn.setAttribute('aria-label', 'Listening...');
      input.placeholder = 'Listening...';
    });

    function stopListening() {
      listening = false;
      micBtn.classList.remove('listening');
      micBtn.setAttribute('aria-label', 'Search by voice');
      input.placeholder = input.dataset.originalPlaceholder || input.placeholder;
    }

    recognition.addEventListener('end', stopListening);

    recognition.addEventListener('result', function (event) {
      var transcript = event.results[0][0].transcript;
      input.value = transcript;
      form.submit();
    });

    recognition.addEventListener('error', function () {
      stopListening();
    });

    micBtn.addEventListener('click', function () {
      if (listening) {
        recognition.stop();
        return;
      }
      if (!input.dataset.originalPlaceholder) {
        input.dataset.originalPlaceholder = input.placeholder;
      }
      try {
        recognition.start();
      } catch (err) {
        // start() throws if called while already active — ignore.
      }
    });
  });

});

/* ==========================================================================
   Form errors: take the user straight to the first problem
   ========================================================================== */
(function () {
  function focusField(group) {
    if (!group) return;
    var input = group.querySelector('input, select, textarea');
    group.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (input) { setTimeout(function () { input.focus({ preventScroll: true }); }, 350); }
  }
  var firstError = document.querySelector('.form-group.has-error');
  if (firstError) {
    focusField(firstError);
  } else {
    // Errors that aren't tied to one box (e.g. "wrong username or password")
    var summary = document.getElementById('form-error-summary');
    if (summary) summary.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  document.querySelectorAll('.form-error-jump').forEach(function (link) {
    link.addEventListener('click', function (e) {
      var target = document.getElementById(link.getAttribute('data-target'));
      if (!target) return;
      e.preventDefault();
      focusField(target.closest('.form-group'));
    });
  });
})();

