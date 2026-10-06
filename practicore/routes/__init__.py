from .admin import admin_bp
from .auth import auth_bp
from .employer import employer_bp
from .media import media_bp
from .student import student_bp

# media_bp carries no role guard: it streams stored images (the avatar route
# checks ownership itself, the logo route is public company branding).
ALL_BLUEPRINTS = [auth_bp, student_bp, employer_bp, admin_bp, media_bp]
