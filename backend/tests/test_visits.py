"""Queue tokens, status rules, doctor access, schedules, appointments, notifications, dashboards."""

from datetime import date, datetime, timedelta

import pytest

from app.core.clock import hospital_tz, local_today
from app.core.consent import CONSENT_VERSION
from app.core.enums import Role

CONSENT = {"version": CONSENT_VERSION, "granted": True, "language": "en"}


@pytest.fixture
def staff(auth_headers):
    return auth_headers(Role.STAFF)


@pytest.fixture
def make_patient(client):
    def _make(phone, name):
        r = client.post("/api/patients/register", json={
            "full_name": name, "phone": phone, "date_of_birth": "1988-08-08", "gender": "female",
            "password": "Visit-Synthetic-1", "consent": CONSENT})
        assert r.status_code == 201, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["patient"]["id"]
    return _make


@pytest.fixture
def doctor(make_user, login):
    def _make(email):
        u = make_user(Role.DOCTOR, email=email, full_name=f"Dr. {email.split('@')[0].title()}")
        return login(email), str(u.id)
    return _make


def queue(client, staff, pid, dept, **kw):
    return client.post("/api/queue", headers=staff, json={"patient_id": pid, "department_id": dept, **kw})


def _submit_and_confirm(client, ph, staff, dept_id, text="Knee pain for a week."):
    cid = client.post("/api/conversations", headers=ph).json()["id"]
    client.post(f"/api/conversations/{cid}/messages", headers=ph, json={"content": text})
    iid = client.post(f"/api/conversations/{cid}/submit", headers=ph).json()["id"]
    r = client.post(f"/api/intakes/{iid}/confirm", headers=staff, json={"department_id": dept_id})
    assert r.status_code == 200, r.text
    return iid


# ---------- queue ----------

def test_confirming_intake_creates_token_and_notifies_patient(client, make_patient, staff, departments):
    ph, pid = make_patient("9844400001", "Synthetic Queue One")
    iid = _submit_and_confirm(client, ph, staff, departments["orthopaedics"])
    entries = client.get("/api/queue", headers=staff).json()
    assert len(entries) == 1
    e = entries[0]
    assert e["token"] == "ORT-001" and e["status"] == "waiting" and e["intake_id"] == iid
    assert e["intake_review_status"] == "confirmed" and e["position"] == 0
    visits = client.get("/api/patients/me/visits", headers=ph).json()
    assert visits[0]["token"] == "ORT-001" and visits[0]["department"] == "Orthopaedics"
    titles = [n["title"] for n in client.get("/api/notifications", headers=ph).json()["items"]]
    assert "Your visit token" in titles and "Your concern was reviewed" in titles


def test_tokens_count_per_department_and_one_active_visit_per_patient(client, make_patient, staff, departments):
    p = [make_patient(f"98444000{i}", f"Synthetic Token {i}")[1] for i in range(10, 14)]
    assert queue(client, staff, p[0], departments["cardiology"]).json()["token"] == "CAR-001"
    assert queue(client, staff, p[1], departments["cardiology"]).json()["token"] == "CAR-002"
    assert queue(client, staff, p[2], departments["general_medicine"]).json()["token"] == "GM-001"
    dup = queue(client, staff, p[0], departments["ent"])
    assert dup.status_code == 409 and "CAR-001" in dup.json()["detail"]
    second = client.get("/api/queue", headers=staff).json()
    assert [e["position"] for e in second if e["department"]["name"] == "Cardiology"] == [0, 1]


def test_status_flow_and_invalid_transitions(client, make_patient, staff, departments):
    ph, pid = make_patient("9844400020", "Synthetic Flow")
    eid = queue(client, staff, pid, departments["ent"]).json()["id"]
    step = lambda s: client.post(f"/api/queue/{eid}/status", headers=staff, json={"status": s})  # noqa: E731
    assert step("completed").status_code == 409  # cannot skip ahead
    assert step("checked_in").json()["checked_in_at"]
    called = step("in_consultation").json()
    assert called["called_at"] and called["position"] is None
    assert any(n["kind"] == "queue.called" for n in client.get("/api/notifications", headers=ph).json()["items"])
    assert step("completed").json()["status"] == "completed"
    assert step("waiting").status_code == 409  # going backwards is not allowed
    assert step("teleported").status_code == 422  # not a status at all
    assert step("cancelled").status_code == 409  # closed visit


def test_doctor_sees_only_assigned_and_limited_actions(client, make_patient, staff, departments, doctor):
    dh, did = doctor("house@example.com")
    oh, _ = doctor("other@example.com")
    _, p1 = make_patient("9844400030", "Synthetic Assigned")
    _, p2 = make_patient("9844400031", "Synthetic Unassigned")
    mine = queue(client, staff, p1, departments["neurology"], doctor_user_id=did).json()["id"]
    theirs = queue(client, staff, p2, departments["neurology"]).json()["id"]

    assert [e["id"] for e in client.get("/api/queue", headers=dh).json()] == [mine]
    assert client.get(f"/api/queue/{theirs}", headers=dh).status_code == 404
    assert client.get(f"/api/queue/{mine}", headers=oh).status_code == 404
    # Doctors cannot check patients in (front-desk task) ...
    assert client.post(f"/api/queue/{mine}/status", headers=dh, json={"status": "checked_in"}).status_code == 409
    client.post(f"/api/queue/{mine}/status", headers=staff, json={"status": "checked_in"})
    # ... but can call in and complete their own patient.
    assert client.post(f"/api/queue/{mine}/status", headers=dh, json={"status": "in_consultation"}).status_code == 200
    assert client.post(f"/api/queue/{mine}/notes", headers=dh, json={"text": "Seen; follow up."}).status_code == 201
    detail = client.post(f"/api/queue/{mine}/status", headers=dh, json={"status": "completed"}).json()
    assert detail["status"] == "completed" and detail["notes"][0]["author"] == "Dr. House"
    # Doctors cannot reassign or add to the queue.
    assert client.patch(f"/api/queue/{theirs}", headers=dh, json={"doctor_user_id": did}).status_code == 403
    assert queue(client, dh, p2, departments["ent"]).status_code == 403


def test_assign_doctor_notifies_and_department_change_gets_new_token(client, make_patient, staff, departments, doctor):
    dh, did = doctor("assign@example.com")
    _, pid = make_patient("9844400040", "Synthetic Assign")
    eid = queue(client, staff, pid, departments["general_medicine"]).json()["id"]
    r = client.patch(f"/api/queue/{eid}", headers=staff, json={"doctor_user_id": did})
    assert r.json()["doctor"]["id"] == did
    assert client.get("/api/notifications", headers=dh).json()["unread"] == 1
    moved = client.patch(f"/api/queue/{eid}", headers=staff, json={"department_id": departments["cardiology"]}).json()
    assert moved["token"] == "CAR-001" and moved["doctor"]["id"] == did
    unassigned = client.patch(f"/api/queue/{eid}", headers=staff, json={"doctor_user_id": None}).json()
    assert unassigned["doctor"] is None
    patient_as_doctor = client.patch(f"/api/queue/{eid}", headers=staff,
                                     json={"doctor_user_id": "00000000-0000-0000-0000-000000000000"})
    assert patient_as_doctor.status_code == 422


@pytest.mark.parametrize("role", [Role.PATIENT, Role.ADMIN])
def test_queue_closed_to_patients_and_admins(client, auth_headers, role):
    assert client.get("/api/queue", headers=auth_headers(role)).status_code == 403


# ---------- notifications ----------

def test_notifications_are_private_and_markable(client, make_patient, staff, departments):
    ph, pid = make_patient("9844400050", "Synthetic Notify")
    queue(client, staff, pid, departments["ent"])
    body = client.get("/api/notifications", headers=ph).json()
    nid = body["items"][0]["id"]
    assert body["unread"] == 1
    assert client.post(f"/api/notifications/{nid}/read", headers=staff).status_code == 404  # not theirs
    assert client.post(f"/api/notifications/{nid}/read", headers=ph).status_code == 204
    assert client.get("/api/notifications", headers=ph).json()["unread"] == 0
    assert client.post("/api/notifications/read-all", headers=ph).status_code == 204


# ---------- schedules & appointments ----------

def _next(weekday: int) -> date:
    d = local_today() + timedelta(days=1)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d


@pytest.fixture
def schedule(client, staff, departments, doctor):
    dh, did = doctor("sched@example.com")
    r = client.post("/api/doctor-schedules", headers=staff, json={
        "doctor_user_id": did, "department_id": departments["dermatology"], "weekday": 2,
        "start_time": "09:00", "end_time": "10:00", "slot_minutes": 20, "room": "Room 12"})
    assert r.status_code == 201, r.text
    return dh, did, r.json()


def test_slots_follow_schedule_in_local_time(client, staff, schedule):
    _, did, _ = schedule
    day = _next(2)
    slots = client.get("/api/appointments/slots", headers=staff, params={"doctor_user_id": did, "day": day}).json()
    local = [datetime.fromisoformat(s["starts_at"]).astimezone(hospital_tz()).strftime("%H:%M") for s in slots]
    assert local == ["09:00", "09:20", "09:40"]
    assert {s["room"] for s in slots} == {"Room 12"}
    other_day = client.get("/api/appointments/slots", headers=staff,
                           params={"doctor_user_id": did, "day": _next(3)}).json()
    assert other_day == []


def test_booking_double_booking_cancel_and_rebook(client, staff, schedule, make_patient):
    dh, did, _ = schedule
    ph, pid = make_patient("9844400060", "Synthetic Booking")
    _, pid2 = make_patient("9844400061", "Synthetic Booking Two")
    slot = client.get("/api/appointments/slots", headers=staff,
                      params={"doctor_user_id": did, "day": _next(2)}).json()[0]["starts_at"]
    r = client.post("/api/appointments", headers=staff, json={"patient_id": pid, "doctor_user_id": did,
                                                                "starts_at": slot, "reason": "Rash follow-up"})
    assert r.status_code == 201, r.text
    appt = r.json()
    assert appt["department"] == "Dermatology" and appt["room"] == "Room 12"
    clash = client.post("/api/appointments", headers=staff, json={"patient_id": pid2, "doctor_user_id": did,
                                                                    "starts_at": slot})
    assert clash.status_code == 409
    odd_time = datetime.fromisoformat(slot) + timedelta(minutes=7)
    assert client.post("/api/appointments", headers=staff, json={
        "patient_id": pid2, "doctor_user_id": did, "starts_at": odd_time.isoformat()}).status_code == 409
    assert client.post("/api/appointments", headers=staff, json={
        "patient_id": pid2, "doctor_user_id": did, "starts_at": slot[:19]}).status_code == 422  # no time zone

    mine = client.get("/api/patients/me/appointments", headers=ph).json()
    assert len(mine) == 1 and mine[0]["status"] == "booked"
    assert any(n["kind"] == "appointment.booked" for n in client.get("/api/notifications", headers=ph).json()["items"])

    # Doctors may complete/no-show their own appointments but not cancel them.
    assert client.post(f"/api/appointments/{appt['id']}/status", headers=dh,
                       json={"status": "cancelled"}).status_code == 409
    cancel = client.post(f"/api/appointments/{appt['id']}/status", headers=staff,
                         json={"status": "cancelled", "reason": "Patient request"})
    assert cancel.json()["status"] == "cancelled"
    assert client.post("/api/appointments", headers=staff, json={"patient_id": pid2, "doctor_user_id": did,
                                                                   "starts_at": slot}).status_code == 201


def test_doctor_sees_upcoming_appointments_with_days_option(client, staff, schedule, make_patient, doctor):
    dh, did, _ = schedule
    oh, _ = doctor("upcoming-other@example.com")
    _, pid = make_patient("9844400062", "Synthetic Upcoming")
    day = _next(2)
    slot = client.get("/api/appointments/slots", headers=staff,
                      params={"doctor_user_id": did, "day": day}).json()[0]["starts_at"]
    assert client.post("/api/appointments", headers=staff, json={
        "patient_id": pid, "doctor_user_id": did, "starts_at": slot}).status_code == 201
    needed = (day - local_today()).days + 1  # smallest window (today = day 1) that reaches the booking
    assert client.get("/api/appointments", headers=dh).json() == []  # default is still today only
    assert client.get("/api/appointments", headers=dh, params={"days": needed - 1}).json() == []
    seen = client.get("/api/appointments", headers=dh, params={"days": needed}).json()
    assert len(seen) == 1 and seen[0]["patient"]["name"] == "Synthetic Upcoming"
    assert client.get("/api/appointments", headers=oh, params={"days": 31}).json() == []  # not another doctor's
    assert client.get("/api/appointments", headers=dh, params={"days": 0}).status_code == 422
    assert client.get("/api/appointments", headers=dh, params={"days": 32}).status_code == 422


def test_doctor_sees_own_schedule_and_appointments_only(client, staff, schedule, doctor, auth_headers):
    dh, did, _ = schedule
    oh, _ = doctor("nosched@example.com")
    assert len(client.get("/api/doctor-schedules", headers=dh).json()) == 1
    assert client.get("/api/doctor-schedules", headers=oh).json() == []
    assert client.get("/api/appointments", headers=oh, params={"doctor_user_id": did}).json() == []
    assert client.get("/api/doctor-schedules", headers=auth_headers(Role.PATIENT)).status_code == 403
    assert client.post("/api/doctor-schedules", headers=dh, json={}).status_code == 403


@pytest.mark.parametrize("bad", [
    {"weekday": 7}, {"start_time": "10:00", "end_time": "09:00"}, {"slot_minutes": 2},
])
def test_invalid_schedule_rejected(client, staff, departments, doctor, bad):
    _, did = doctor("badsched@example.com")
    body = {"doctor_user_id": did, "department_id": departments["ent"], "weekday": 1,
            "start_time": "09:00", "end_time": "12:00", "slot_minutes": 15, **bad}
    assert client.post("/api/doctor-schedules", headers=staff, json=body).status_code == 422


def test_schedule_needs_a_real_doctor(client, staff, departments, make_user):
    nurse = make_user(Role.STAFF, email="nurse2@example.com")
    r = client.post("/api/doctor-schedules", headers=staff, json={
        "doctor_user_id": str(nurse.id), "department_id": departments["ent"], "weekday": 1,
        "start_time": "09:00", "end_time": "12:00"})
    assert r.status_code == 422


# ---------- dashboards ----------

def test_dashboards_counts_and_no_identifiers(client, make_patient, staff, departments, doctor, auth_headers):
    dh, did = doctor("dash@example.com")
    ph, pid = make_patient("9844400070", "Synthetic Dashboard Person")
    iid = _submit_and_confirm(client, ph, staff, departments["ent"], "Sore throat and chest pain.")
    _, pid2 = make_patient("9844400071", "Synthetic Waiting Person")
    queue(client, staff, pid2, departments["ent"], doctor_user_id=did)

    s = client.get("/api/dashboard/staff", headers=staff).json()
    assert s["queue"]["waiting"] == 2 and s["intakes_pending_review"] == 0
    d = client.get("/api/dashboard/doctor", headers=dh).json()
    assert d["my_queue"]["waiting"] == 1
    a = client.get("/api/dashboard/admin", headers=auth_headers(Role.ADMIN)).json()
    assert a["confirmed_last_30_days_by_department"] == {"ENT (Ear, Nose and Throat)": 1}
    assert a["intakes_last_30_days_by_language"] == {"en": 1}
    blob = str(a) + str(s) + str(d)
    assert "Synthetic" not in blob and iid not in blob and pid not in blob


@pytest.mark.parametrize("path,allowed", [
    ("/api/dashboard/staff", Role.STAFF), ("/api/dashboard/doctor", Role.DOCTOR), ("/api/dashboard/admin", Role.ADMIN),
])
def test_dashboard_permissions(client, auth_headers, path, allowed):
    for role in Role:
        code = client.get(path, headers=auth_headers(role)).status_code
        assert code == (200 if role == allowed else 403), (path, role)
