from .admin import admin_bp
from .auth import auth_bp
from .employer import employer_bp
from .student import student_bp

ALL_BLUEPRINTS = [auth_bp, student_bp, employer_bp, admin_bp]
