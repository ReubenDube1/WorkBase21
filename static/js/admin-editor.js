/* Turns admin text boxes marked .wb21-rich-editor into TinyMCE editors.
   Settings are chosen so content saved by the old editor (CKEditor 4)
   is kept exactly: links/image addresses are not rewritten, underline
   stays <u>, and images keep their left/right positioning. */
(function () {
  if (typeof tinymce === 'undefined') return;   // plain textarea still works

  function csrfToken() {
    var el = document.querySelector('input[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
  }

  function uploadHandler(uploadUrl) {
    return function (blobInfo) {
      return new Promise(function (resolve, reject) {
        var data = new FormData();
        data.append('file', blobInfo.blob(), blobInfo.filename());
        fetch(uploadUrl, {
          method: 'POST', body: data, credentials: 'same-origin',
          headers: { 'X-CSRFToken': csrfToken() }
        }).then(function (res) {
          return res.json().then(function (json) {
            if (res.ok && json.location) resolve(json.location);
            else reject({ message: json.error || 'Upload failed.', remove: true });
          });
        }).catch(function () {
          reject({ message: 'Upload failed — check your connection and try again.', remove: true });
        });
      });
    };
  }

  function init(textarea) {
    var cfg = JSON.parse(textarea.getAttribute('data-editor-config'));
    var options = {
      target: textarea,
      license_key: 'gpl',              // TinyMCE 7 is free under GPL v2+
      base_url: cfg.base_url,
      suffix: '.min',
      promotion: false,
      branding: false,
      menubar: false,
      plugins: cfg.plugins,
      toolbar: cfg.toolbar,
      toolbar_mode: 'wrap',
      min_height: cfg.min_height,
      autoresize_bottom_margin: 20,
      block_formats: 'Paragraph=p; Heading 2=h2; Heading 3=h3; Heading 4=h4',
      formats: { underline: { inline: 'u', exact: true } },
      // Keep addresses exactly as saved (e.g. /media/uploads/...).
      relative_urls: false,
      remove_script_host: true,
      convert_urls: true,
      entity_encoding: 'raw',
      link_default_target: '',
      content_style:
        'body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.6;margin:12px}' +
        'img{max-width:100%;height:auto}',
    };
    if (cfg.upload_url) {
      options.images_upload_handler = uploadHandler(cfg.upload_url);
      options.automatic_uploads = true;
      options.images_file_types = 'jpeg,jpg,png,gif,webp';
      options.image_description = true;   // "alt" text for accessibility/SEO
      options.image_dimensions = true;
      options.file_picker_types = 'image';
    }
    tinymce.init(options);
  }

  function start() {
    document.querySelectorAll('textarea.wb21-rich-editor').forEach(init);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
