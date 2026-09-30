/* ==========================================================================
   WorkBase21 Admin — Insert Article Link
   Adds a small picker above the job description editors so staff can
   link to a published Blog article (e.g. the Z83 guide) without needing
   to look up or copy/paste its URL.

   Works with the TinyMCE editor (see static/js/admin-editor.js).
   - Inserts into the description box you last clicked in (Part 1 if none).
   - If you've selected some words first, those words become the link;
     otherwise the article's title is inserted as the link text.
   ========================================================================== */
(function () {
  'use strict';

  var ARTICLES_URL = '/admin/jobs/job/article-links.json';

  function fetchArticles(callback) {
    fetch(ARTICLES_URL, { credentials: 'same-origin' })
      .then(function (res) { return res.ok ? res.json() : []; })
      .then(function (data) { callback(data || []); })
      .catch(function () { callback([]); });
  }

  function buildPicker(articles) {
    var wrap = document.createElement('div');
    wrap.className = 'article-link-picker';
    wrap.style.cssText =
      'margin:0 0 10px;padding:10px 12px;background:#f8fafc;' +
      'border:1px solid #e2e8f0;border-radius:6px;display:flex;' +
      'gap:8px;align-items:center;flex-wrap:wrap;max-width:860px;';

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
    select.className = 'article-link-select';
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
    btn.className = 'button article-link-insert';
    btn.style.cssText = 'font-size:12px;padding:5px 12px;cursor:pointer;';
    btn.addEventListener('click', function () {
      insertLink(select.value, select.options[select.selectedIndex].dataset.title);
    });
    wrap.appendChild(btn);

    var hint = document.createElement('span');
    hint.textContent = 'Click inside a description box first (or select some words to turn them into the link), then Insert.';
    hint.style.cssText = 'font-size:11px;color:#94a3b8;width:100%;';
    wrap.appendChild(hint);

    return wrap;
  }

  function targetEditor() {
    if (typeof tinymce === 'undefined') return null;
    // activeEditor = the description box last clicked in.
    var ed = tinymce.activeEditor;
    if (ed && /^id_description\d*$/.test(ed.id)) return ed;
    return tinymce.get('id_description') || null;
  }

  function insertLink(url, title) {
    var editor = targetEditor();
    if (!editor) {
      alert("The description editor hasn't loaded yet — wait a moment and try again.");
      return;
    }
    editor.focus();
    if (!editor.selection.isCollapsed()) {
      // Turn the selected words into the link.
      editor.execCommand('mceInsertLink', false, { href: url, target: '_blank', rel: 'noopener noreferrer' });
    } else {
      var safeTitle = editor.dom.encode(title);
      editor.insertContent('<a href="' + editor.dom.encode(url) + '" target="_blank" rel="noopener noreferrer">' + safeTitle + '</a>&nbsp;');
    }
  }

  function mountPicker() {
    var field = document.getElementById('id_description');
    if (!field || document.querySelector('.article-link-picker')) return; // not the Job form, or already added
    fetchArticles(function (articles) {
      // The admin lays out each field's label and box side by side in a row
      // (.flex-container); put the picker just above that whole row so it
      // sits on its own line above the Description Part 1 editor.
      var row = field.closest('.flex-container') || field;
      row.parentNode.insertBefore(buildPicker(articles), row);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountPicker);
  else mountPicker();
})();
