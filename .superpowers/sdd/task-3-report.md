# Task 3 Report — Footer override + website.page record

**Status:** DONE

## Files created

- `addons/afr_labquali_website/views/website_layout_override.xml`
- `addons/afr_labquali_website/data/website_data.xml`

## Deviations from brief

### 1. `xpath expr="."` → `expr="//div[@id='footer']"`

The brief specified `<xpath expr="." position="replace">` to replace the entire `website.footer_custom` template root. This causes a hard `ParseError` on install:

```
Element '<xpath expr="//footer//span[hasclass('o_footer_copyright_name')]">'
cannot be located in parent view
```

**Root cause:** `website.footer_custom` is an extension of `website.layout`. Using `expr="."` with `position="replace"` replaces the entire combined layout arch (header, wrapwrap, footer, copyright div) with just our footer `<div>`. The sibling view `website.footer_copyright_company_name` (view 801) still inherits `website.layout` and looks for `//footer//span[hasclass('o_footer_copyright_name')]` in the combined arch — which no longer exists after the replace. Odoo fails validation.

**Fix:** Changed to `<xpath expr="//div[@id='footer']" position="replace">` which replaces only the `#footer` div, leaving the outer `<footer id="bottom">` and the `o_footer_copyright` sibling div (with its span) intact.

Additionally added a second xpath to hide the default Odoo copyright bar (which would otherwise appear below our custom footer's own copyright line):

```xml
<xpath expr="//div[hasclass('o_footer_copyright')]" position="attributes">
    <attribute name="class" add="d-none" separator=" "/>
</xpath>
```

### 2. `website_form` removed from depends

`website_form` is absent from this Odoo image (not in addons path, not in DB module list). The install failed with:

```
UserError: You try to install module 'afr_labquali_website' that depends on module 'website_form'.
But the latter module is not available in your system.
```

Removed from `__manifest__.py` depends. The homepage uses `/contactus` links (standard website module) — no form snippets are used.

## Install result

```
INFO odoo-labquali odoo.modules.loading: loading afr_labquali_website/views/labquali_homepage.xml
INFO odoo-labquali odoo.modules.loading: loading afr_labquali_website/views/website_layout_override.xml
INFO odoo-labquali odoo.modules.loading: loading afr_labquali_website/data/website_data.xml
INFO odoo-labquali odoo.modules.loading: Module afr_labquali_website loaded in 0.51s, 60 queries
```

No Python errors, no ParseError, no UserError. Only warnings from unrelated modules (engc_os field `ondelete`, steril_supervisorio_dashboard missing license key).
