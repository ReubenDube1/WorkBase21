"""Rich-text editor for the admin (TinyMCE 7.9.3, bundled in
static/vendor/tinymce — GPL-2.0-or-later, free). Replaces django-ckeditor
(CKEditor 4), which is no longer supported and has known security issues.

Only the ADMIN uses the editor. What visitors see is unchanged: the saved
HTML is displayed exactly as before.

Two presets, matching the old CKEditor toolbars:
  * 'default' - job descriptions: headings, bold/italic/underline, lists,
                links, clear formatting, view source
  * 'article' - blog articles: all of the above + quotes, images (upload
                and position left/centre/right)
"""
import json
import uuid

from django import forms
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
# Only real bitmap images. SVG is deliberately NOT allowed: SVG files can
# contain scripts.
ALLOWED_FORMATS = {'JPEG': 'jpg', 'PNG': 'png', 'GIF': 'gif', 'WEBP': 'webp'}

BASE_TOOLBAR = 'undo redo | blocks | bold italic underline | bullist numlist | link unlink | removeformat | code'
ARTICLE_TOOLBAR = ('undo redo | blocks | bold italic underline | bullist numlist blockquote | '
                   'link unlink | image alignleft aligncenter alignright | removeformat | code')

CONFIGS = {
    'default': {'toolbar': BASE_TOOLBAR, 'plugins': 'lists link autolink code autoresize', 'min_height': 300},
    'article': {'toolbar': ARTICLE_TOOLBAR, 'plugins': 'lists link autolink code autoresize image', 'min_height': 350},
}


class RichTextEditor(forms.Textarea):
    """A normal <textarea> that the admin turns into a TinyMCE editor.
    If JavaScript fails for any reason, the plain textarea (with the HTML
    in it) still works, so content can never be lost."""

    def __init__(self, config='default', attrs=None):
        self.config_name = config
        attrs = {'class': 'wb21-rich-editor', **(attrs or {})}
        super().__init__(attrs=attrs)

    class Media:
        js = ('vendor/tinymce/tinymce.min.js', 'js/admin-editor.js')

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        config = dict(CONFIGS[self.config_name])
        # Loaded by path (not through the hashed-filename lookup), because
        # TinyMCE loads its plugins and skins relative to this folder.
        config['base_url'] = settings.STATIC_URL.rstrip('/') + '/vendor/tinymce'
        if 'image' in config['plugins']:
            config['upload_url'] = reverse('admin_editor_upload_image')
        context['widget']['attrs']['data-editor-config'] = json.dumps(config)
        return context


@staff_member_required
@require_POST
def upload_image(request):
    """Image upload for the article editor. Admins only; checks the file
    really is a JPG/PNG/GIF/WebP image (not just named like one) and is
    under 5 MB; saves it under media/uploads/ with a random name."""
    from PIL import Image

    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file received.'}, status=400)
    if f.size > MAX_IMAGE_BYTES:
        return JsonResponse({'error': 'That image is larger than 5 MB. Please use a smaller one.'}, status=400)
    try:
        with Image.open(f) as img:
            fmt = img.format
            img.verify()
    except Exception:
        return JsonResponse({'error': "That file isn't a picture we can use (JPG, PNG, GIF or WebP)."}, status=400)
    if fmt not in ALLOWED_FORMATS:
        return JsonResponse({'error': "Only JPG, PNG, GIF or WebP pictures can be uploaded."}, status=400)

    f.seek(0)
    name = f"uploads/{timezone.now():%Y/%m/%d}/{uuid.uuid4().hex}.{ALLOWED_FORMATS[fmt]}"
    saved = default_storage.save(name, f)
    return JsonResponse({'location': default_storage.url(saved)})
