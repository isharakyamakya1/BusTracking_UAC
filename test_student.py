from app import app

client = app.test_client()

print("Testing student dashboard...")

rv = client.get("/student", follow_redirects=False)
assert rv.status_code == 302, f"Expected redirect for anonymous user, got {rv.status_code}"
assert rv.headers.get("Location", "").endswith("/login"), rv.headers.get("Location")

login = client.post(
    "/login",
    data={"email": "POLY163/2022", "password": "uac2026"},
    follow_redirects=False,
)
assert login.status_code == 302, f"Expected successful login redirect, got {login.status_code}"
assert login.headers.get("Location", "").endswith("/student"), login.headers.get("Location")

dashboard = client.get("/student")
assert dashboard.status_code == 200, f"Expected student dashboard, got {dashboard.status_code}"
assert b"Tableau de Bord Etudiant" in dashboard.data
assert b"Suivre le bus" in dashboard.data

print("Student dashboard smoke test passed.")
