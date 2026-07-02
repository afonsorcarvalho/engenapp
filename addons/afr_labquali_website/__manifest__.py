# addons/afr_labquali_website/__manifest__.py
{
    "name": "LabQuali Website",
    "version": "16.0.1.1.3",
    "category": "Website",
    "license": "LGPL-3",
    "author": "AFR Sistemas",
    "summary": "Landing page institucional LabQuali — qualificação e calibração de equipamentos",
    "depends": ["website", "afr_labquali_layout"],
    "data": [
        "security/ir.model.access.csv",
        "views/labquali_homepage.xml",
        "views/labquali_backend_views.xml",
        "views/website_layout_override.xml",
        "data/labquali_images_data.xml",
    ],
    "post_init_hook": "post_init_hook",
    "assets": {
        "web.assets_frontend": [
            "afr_labquali_website/static/src/lib/gsap.min.js",
            "afr_labquali_website/static/src/lib/ScrollTrigger.min.js",
            "afr_labquali_website/static/src/scss/labquali_website.scss",
            "afr_labquali_website/static/src/js/labquali_animations.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
