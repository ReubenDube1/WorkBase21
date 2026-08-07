/* ==========================================================================
   WorkBase21 Admin — Insert Article Link
   Adds a small picker above the job description editors so staff can
   link to a published Career Resources article (e.g. the Z83 guide)
   without needing to look up or copy/paste its URL.
   ========================================================================== */
(function () {
  'use strict';

  var ARTICLES_URL = '/admin/jobs/job/article-links.json';
  var lastFocusedEditorName = null;
  var articlesCache = null;

  function fetchArticles(callback) {
    if (articlesCache) {
      callback(articlesCache);
      return;
    }
    fetch(ARTICLES_URL, { credentials: 'same-origin' })
      .then(function (res) { return res.ok ? res.json() : []; })
      .then(function (data) {
        articlesCache = data || [];
        callback(articlesCache);
      })
      .catch(function () { callback([]); });
  }

  function buildPicker(articles) {
    var wrap = document.createElement('div');
    wrap.className = 'article-link-picker';
    wrap.style.cssText =
      'margin:0 0 10px;padding:10px 12px;background:#f8fafc;' +
      'border:1px solid #e2e8f0;border-radius:6px;display:flex;' +
      'gap:8px;align-items:center;flex-wrap:wrap;';

    var label = document.createElement('span');
    label.textContent = 'Insert Article Link:';
    label.style.cssText = 'font-size:12px;font-weight:600;color:#334155;';
    wrap.appendChild(label);

    if (!articles.length) {
      var none = document.createElement('span');
      none.textContent = 'No published articles yet — publish one under Trending Topics first.';
      none.style.cssText = 'font-size:12px;color:#64748b;';
      wrap.appendChild(none);
      return wrap;
    }

    var select = document.createElement('select');
    select.style.cssText = 'flex:1;min-width:200px;max-width:400px;';
    articles.forEach(function (a) {
      var opt = document.createElement('option');
      opt.value = a.url;
      opt.textContent = a.title;
      opt.dataset.title = a.title;
      select.appendChild(opt);
    });
    wrap.appendChild(select);

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = 'Insert Link';
    btn.className = 'button';
    btn.style.cssText = 'font-size:12px;padding:5px 12px;cursor:pointer;';
    btn.addEventListener('click', function () {
      insertLink(select.value, select.options[select.selectedIndex].dataset.title);
    });
    wrap.appendChild(btn);

    var hint = document.createElement('span');
    hint.textContent = 'Click inside a description box first, then Insert.';
    hint.style.cssText = 'font-size:11px;color:#94a3b8;width:100%;';
    wrap.appendChild(hint);

    return wrap;
  }

  function insertLink(url, title) {
    if (typeof CKEDITOR === 'undefined') return;

    var editor = null;
    if (lastFocusedEditorName && CKEDITOR.instances[lastFocusedEditorName]) {
      editor = CKEDITOR.instances[lastFocusedEditorName];
    } else if (CKEDITOR.instances['id_description']) {
      // Default to Description Part 1 if nothing's been focused yet.
      editor = CKEDITOR.instances['id_description'];
    } else {
      var names = Object.keys(CKEDITOR.instances);
      if (names.length) editor = CKEDITOR.instances[names[0]];
    }

    if (!editor) {
      alert("Couldn't find a description box to insert into — click inside one first.");
      return;
    }

    var html = '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + title + '</a>';
    editor.insertHtml(html);
    editor.focus();
  }

  function trackFocus() {
    if (typeof CKEDITOR === 'undefined') return;
    CKEDITOR.on('instanceReady', function (ev) {
      ev.editor.on('focus', function () {
        lastFocusedEditorName = ev.editor.name;
      });
    });
  }

  function mountPicker() {
    var firstField = document.getElementById('cke_id_description');
    if (!firstField) return; // Not on the Job change/add page, or field not rendered yet.

    fetchArticles(function (articles) {
      var picker = buildPicker(articles);
      firstField.parentNode.insertBefore(picker, firstField);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    trackFocus();
    // CKEditor fields can render slightly after DOMContentLoaded in the
    // admin, so give it a moment before looking for the mount point.
    setTimeout(mountPicker, 400);
  });
})();
