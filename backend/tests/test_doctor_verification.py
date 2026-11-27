"""Doctor self-registration is PENDING until an administrator approves; role cannot be self-assigned."""

import pytest

from app.core.consent import CONSENT_VERSION
from app.core.enums import Role

CONSENT = {"version": CONSENT_VERSION, "granted": True, "language": "en"}
PASSWORD = "Doctor-Synthetic-1"

APPLICATION = {
    "full_name": "Dr. Synthetic Applicant", "email": "applicant@example.com", "phone": "9877700001",
    "password": PASSWORD, "qualification": "MBBS, MD (Medicine)", "specialization": "General Medicine",
    "registration_number": "SYN/12345", "registration_authority": "Synthetic State Medical Council",
    "hospital_name": "Synthetic City Hospital", "years_experience": 7,
}


def register(client, **over):
    return client.post("/api/doctors/register", json={**APPLICATION, **over})


def headers(r):
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin(auth_headers):
    return auth_headers(Role.ADMIN)


@pytest.fixture
def make_patient(client):
    def _make(phone="9877700090", name="Synthetic Patient"):
        r = client.post("/api/patients/register", json={
            "full_name": name, "phone": phone, "date_of_birth": "1988-08-08", "gender": "female",
            "password": "Visit-Synthetic-1", "consent": CONSENT})
        assert r.status_code == 201, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["patient"]["id"]
    return _make


# ---------- registration ----------

def test_registration_creates_pending_doctor(client):
    r = register(client)
    assert r.status_code == 201, r.text
    user = r.json()["user"]
    assert user["role"] == "doctor" and user["verification_status"] == "pending"
    assert "password" not in r.text


def test_registration_requires_all_professional_details(client):
    for field in ("qualification", "specialization", "registration_number", "registration_authority",
                  "hospital_name", "years_experience", "email", "phone", "full_name"):
        body = {k: v for k, v in APPLICATION.items() if k != field}
        assert client.post("/api/doctors/register", json=body).status_code == 422, field


def test_client_cannot_choose_a_role_or_status(client):
    assert register(client, role="admin").status_code == 422
    assert register(client, role="doctor", email="x@example.com").status_code == 422
    assert register(client, verification_status="approved").status_code == 422


def test_duplicate_account_or_registration_number_is_refused(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409  # same email
    other = register(client, email="other@example.com", phone="9877700002")  # same council number
    assert other.status_code == 409 and "registration number" in other.json()["detail"]
    ok = register(client, email="third@example.com", phone="9877700003", registration_number="SYN/99999")
    assert ok.status_code == 201


# ---------- a pending doctor has no doctor access ----------

def test_pending_doctor_cannot_use_any_doctor_or_patient_endpoint(client, make_patient, departments):
    h = headers(register(client))
    for url in ("/api/doctors", "/api/appointments", "/api/doctor-schedules", "/api/departments"):
        assert client.get(url, headers=h).status_code == 403, url
    assert client.get("/api/queue", headers=h).status_code == 403
    assert client.get("/api/dashboard/doctor", headers=h).status_code == 403
    assert client.get("/api/patients", headers=h).status_code == 403
    assert client.get("/api/intakes", headers=h).status_code == 403
    assert client.get("/api/patients/me", headers=h).status_code == 403
    _, pid = make_patient()
    assert client.get(f"/api/patients/{pid}", headers=h).status_code == 403
    assert client.get("/api/doctor/intakes/00000000-0000-0000-0000-000000000000", headers=h).status_code == 403


def test_pending_doctor_can_only_see_own_status_and_profile(client):
    h = headers(register(client))
    me = client.get("/api/users/me", headers=h).json()
    assert me["verification_status"] == "pending"
    st = client.get("/api/doctors/me/verification", headers=h).json()
    assert st["status"] == "pending" and st["profile"]["registration_number"] == "SYN/12345"


def test_pending_doctor_cannot_be_assigned_patients_or_listed(client, auth_headers, make_patient, departments):
    r = register(client)
    doctor_id = r.json()["user"]["id"]
    staff = auth_headers(Role.STAFF)
    _, pid = make_patient()
    listed = client.get("/api/doctors", headers=staff).json()
    assert all(d["id"] != doctor_id for d in listed)
    q = client.post("/api/queue", headers=staff, json={"patient_id": pid, "department_id": departments["cardiology"],
                                                        "doctor_user_id": doctor_id})
    assert q.status_code == 422


def test_non_doctors_cannot_call_doctor_status_or_admin_endpoints(client, auth_headers):
    assert client.get("/api/doctors/me/verification", headers=auth_headers(Role.PATIENT)).status_code == 403
    assert client.get("/api/doctors/me/verification", headers=auth_headers(Role.STAFF)).status_code == 403
    assert client.get("/api/admin/doctors").status_code == 401


# ---------- administrator decision ----------

def test_only_admin_can_review_applications(client, auth_headers):
    uid = register(client).json()["user"]["id"]
    for role in (Role.PATIENT, Role.STAFF, Role.DOCTOR):
        h = auth_headers(role)
        assert client.get("/api/admin/doctors", headers=h).status_code == 403
        assert client.post(f"/api/admin/doctors/{uid}/approve", headers=h).status_code == 403
        assert client.post(f"/api/admin/doctors/{uid}/reject", headers=h, json={"note": "no"}).status_code == 403
    pending = headers(client.post("/api/auth/login", json={"identifier": "applicant@example.com",
                                                           "password": PASSWORD}))
    assert client.post(f"/api/admin/doctors/{uid}/approve", headers=pending).status_code == 403  # cannot self-approve


def test_admin_sees_applications_and_approval_unlocks_access(client, admin):
    r = register(client)
    uid = r.json()["user"]["id"]
    h = headers(r)
    assert client.get("/api/queue", headers=h).status_code == 403

    pending = client.get("/api/admin/doctors", params={"status": "pending"}, headers=admin).json()
    assert pending["total"] == 1 and pending["items"][0]["profile"]["registration_number"] == "SYN/12345"
    assert "password" not in str(pending)

    done = client.post(f"/api/admin/doctors/{uid}/approve", headers=admin, json={})
    assert done.status_code == 200 and done.json()["profile"]["verification_status"] == "approved"

    # The SAME token now works: access is decided by the server on every request.
    assert client.get("/api/queue", headers=h).status_code == 200
    assert client.get("/api/users/me", headers=h).json()["verification_status"] == "approved"
    assert client.post(f"/api/admin/doctors/{uid}/approve", headers=admin).status_code == 409  # already decided


def test_rejection_needs_a_reason_and_keeps_access_closed(client, admin):
    r = register(client)
    uid = r.json()["user"]["id"]
    h = headers(r)
    assert client.post(f"/api/admin/doctors/{uid}/reject", headers=admin, json={}).status_code == 422
    done = client.post(f"/api/admin/doctors/{uid}/reject", headers=admin, json={"note": "Number not found at council"})
    assert done.status_code == 200 and done.json()["profile"]["verification_status"] == "rejected"
    assert client.get("/api/queue", headers=h).status_code == 403
    st = client.get("/api/doctors/me/verification", headers=h).json()
    assert st["status"] == "rejected" and st["profile"]["review_note"] == "Number not found at council"


def test_decisions_are_audited(client, admin, db):
    from sqlalchemy import select

    from app.database.models import AuditEvent
    uid = register(client).json()["user"]["id"]
    client.post(f"/api/admin/doctors/{uid}/approve", headers=admin, json={})
    actions = {a for (a,) in db.execute(select(AuditEvent.action))}
    assert {"doctor.registered", "doctor.approved"} <= actions


def test_unknown_application_is_404(client, admin):
    assert client.post("/api/admin/doctors/00000000-0000-0000-0000-000000000000/approve", headers=admin
                       ).status_code == 404


# ---------- nobody can promote themselves ----------

def test_patient_cannot_change_own_role(client, make_patient, db):
    h, _ = make_patient()
    assert client.patch("/api/users/me/preferences", headers=h, json={"role": "doctor"}).status_code == 422
    assert client.patch("/api/users/me/preferences", headers=h,
                        json={"ui_language": "en", "role": "doctor"}).status_code == 422
    assert client.patch("/api/patients/me", headers=h, json={"role": "doctor"}).status_code == 422
    assert client.post("/api/admin/users", headers=h, json={
        "full_name": "X", "email": "x@example.com", "password": PASSWORD, "role": "doctor"}).status_code == 403
    me = client.get("/api/users/me", headers=h).json()
    assert me["role"] == "patient"


def test_patient_registration_ignores_or_rejects_role_fields(client):
    r = client.post("/api/patients/register", json={
        "full_name": "Synthetic Sneaky", "phone": "9877700077", "date_of_birth": "1990-01-01", "gender": "male",
        "password": "Visit-Synthetic-1", "consent": CONSENT, "role": "doctor"})
    assert r.status_code == 422


# ---------- verified doctors read assigned intakes only ----------

def _confirmed_intake(client, patient_headers, staff, dept_id, text="Chest pain since this morning."):
    cid = client.post("/api/conversations", headers=patient_headers).json()["id"]
    client.post(f"/api/conversations/{cid}/messages", headers=patient_headers, json={"content": text})
    iid = client.post(f"/api/conversations/{cid}/submit", headers=patient_headers).json()["id"]
    assert client.post(f"/api/intakes/{iid}/confirm", headers=staff, json={"department_id": dept_id}).status_code == 200
    return iid


def test_doctor_reads_only_intakes_assigned_to_them(client, admin, auth_headers, make_user, login,
                                                    make_patient, departments):
    staff = auth_headers(Role.STAFF)
    mine = make_user(Role.DOCTOR, email="mine@example.com")
    other = make_user(Role.DOCTOR, email="other-doc@example.com")
    ph, pid = make_patient()
    iid = _confirmed_intake(client, ph, staff, departments["cardiology"])
    entry = client.get("/api/queue", headers=staff).json()[0]
    assert entry["priority"] in ("urgent", "normal")
    assert client.patch(f"/api/queue/{entry['id']}", headers=staff, json={"doctor_user_id": str(mine.id)}
                        ).status_code == 200

    me, them = login("mine@example.com"), login("other-doc@example.com")
    d = client.get(f"/api/doctor/intakes/{iid}", headers=me)
    assert d.status_code == 200
    body = d.json()
    assert body["priority"] in ("urgent", "normal") and "field_evidence" in body and "symptoms" in body
    assert client.get(f"/api/doctor/intakes/{iid}/history", headers=me).status_code == 200
    # another doctor, a patient and a pending doctor all get nothing
    assert client.get(f"/api/doctor/intakes/{iid}", headers=them).status_code == 404
    assert client.get(f"/api/doctor/intakes/{iid}", headers=ph).status_code == 403
    pending = headers(register(client))
    assert client.get(f"/api/doctor/intakes/{iid}", headers=pending).status_code == 403
    # doctors still cannot edit: the staff-only intake routes stay closed
    assert client.get(f"/api/intakes/{iid}", headers=me).status_code == 403
    assert client.patch(f"/api/intakes/{iid}/priority", headers=me,
                        json={"priority": "normal", "reason": "because"}).status_code == 403
