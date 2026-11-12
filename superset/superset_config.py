import os
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://superset:{os.environ['POSTGRES_PASSWORD']}@db:5432/superset"
)
ENABLE_PROXY_FIX = True
WTF_CSRF_ENABLED = True
WTF_CSRF_EXEMPT_LIST = []
FEATURE_FLAGS = {"DASHBOARD_NATIVE_FILTERS": True, "DASHBOARD_CROSS_FILTERS": True, "ALERT_REPORTS": False}
ROW_LIMIT = 50000
SQLLAB_TIMEOUT = 120
SUPERSET_WEBSERVER_TIMEOUT = 120
TALISMAN_ENABLED = False

# ---------------- Marka / görünüm (Grup 6) ----------------
APP_NAME = "Wallmart · DC Planning"
APP_ICON = "/static/assets/images/custom/logo.svg"
APP_ICON_WIDTH = 190
LOGO_TARGET_PATH = "/superset/dashboard/dc-planning/"
LOGO_TOOLTIP = "Bölgesel Dağıtım Merkezi Planlama Dashboard'u"
FAVICONS = [{"href": "/static/assets/images/custom/favicon.svg"}]
THEME_OVERRIDES = {
    "colors": {
        "primary": {"base": "#1F4E79", "dark1": "#173C5E", "dark2": "#102B43", "light1": "#3A6EA5", "light2": "#7FA6CF",
                    "light3": "#B8D0E8", "light4": "#DCE8F4", "light5": "#F0F5FA"},
        "secondary": {"base": "#2E86AB"},
    },
    "typography": {"families": {"sansSerif": "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"}},
}
BABEL_DEFAULT_LOCALE = "tr"
LANGUAGES = {"tr": {"flag": "tr", "name": "Türkçe"}, "en": {"flag": "us", "name": "English"}}
EXTRA_CATEGORICAL_COLOR_SCHEMES = [{
    "id": "grup6", "label": "Grup 6", "isDefault": True,
    "colors": ["#1F4E79", "#F18F01", "#2E86AB", "#C73E1D", "#6A994E", "#8E7DBE", "#E9C46A", "#577590", "#F4A261", "#264653"],
}]
EXTRA_SEQUENTIAL_COLOR_SCHEMES = [{
    "id": "grup6_seq", "label": "Grup 6 (sıralı)", "isDiverging": False,
    "colors": ["#F0F5FA", "#B8D0E8", "#7FA6CF", "#3A6EA5", "#1F4E79", "#102B43"],
}]
FEATURE_FLAGS.update({"DASHBOARD_RBAC": True, "TAGGING_SYSTEM": True, "ENABLE_TEMPLATE_PROCESSING": True})
CONTENT_SECURITY_POLICY_WARNING = False
