BusinessHub Logo Pack

FILES
- static/images/businesshub-logo-horizontal.png : website header logo
- static/images/businesshub-logo.png : full logo artwork
- static/images/businesshub-mark.png : logo symbol
- static/images/businesshub-icon.png : square icon source
- static/images/favicon.ico and favicon-*.png : browser tab icon options
- static/pwa/icon-192.png and icon-512.png : PWA app icons

INSTALL
1. Copy the contents of this pack's static folder into the existing static folder in your Django project. Merge folders; do not delete your existing static files.
2. In a Django template, ensure {% load static %} is present, then use this for the header logo:
   <img src="{% static 'images/businesshub-logo-horizontal.png' %}" alt="BusinessHub" class="businesshub-logo">
3. Add/adjust CSS:
   .businesshub-logo { display:block; width:220px; max-width:100%; height:auto; object-fit:contain; }
4. In the base template <head>, use:
   <link rel="icon" href="{% static 'images/favicon.ico' %}" sizes="any">
   <link rel="icon" type="image/png" sizes="32x32" href="{% static 'images/favicon-32.png' %}">
5. In manifest.json, use icon paths appropriate to the manifest's current location. If it is served from /static/pwa/ and URLs are root-relative, the icon URLs may be /static/pwa/icon-192.png and /static/pwa/icon-512.png. Preserve existing manifest fields.

IMPORTANT
This pack contains the image assets only; it does not replace base.html or manifest.json, because those files contain your site's existing navigation and PWA settings. Merge the files into your project and back up existing templates before editing.
