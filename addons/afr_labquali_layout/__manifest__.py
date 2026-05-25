{
    "name": "LabQuali Document Layout",
    "version": "16.0.1.0.0",
    "category": "Technical",
    "license": "LGPL-3",
    "author": "AFR Sistemas",
    "summary": (
        "Registers LabQuali brand layout in document-layout wizard. "
        "Header double-divider, orange side stripe (first page), "
        "confidential stamp, Inter typography."
    ),
    "depends": ["web", "base"],
    "data": [
        "views/external_layout_labquali.xml",
        "data/report_layout.xml",
        "data/paperformat.xml",
        "views/res_company_views.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
