import os

# app.auth refuses to start without a strong JWT_SECRET. Fake value, for tests only.
# pytest loads conftest.py before the test modules, so this runs before the app is imported.
os.environ["JWT_SECRET"] = "test-only-secret-not-used-anywhere-else"
