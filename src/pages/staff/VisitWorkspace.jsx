// One patient visit: details, status actions, doctor/department, care-team notes,
// confirmed intake and (staff only) appointment booking.
import React, { useEffect, useState } from "react";
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  LayoutDashboard,
  ShieldCheck,
  Stethoscope,
  X,
} from "lucide-react";
import { Brand, Btn, Info, QUEUE_STATUS, Status, timeOnly } from "../../components/ui.jsx";
import {
  addVisitNote,
  assignVisit,
  bookAppointment,
  getVisit,
  listDoctors,
  listSlots,
  setVisitStatus,
  todayLocal,
} from "../../services/visits.js";
import { listDepartments, LANGUAGE_NAMES, formatDate } from "../../services/intake.js";
import DoctorIntakeDetails from "../doctor/DoctorIntakeDetails.jsx";
import { PriorityChip } from "./IntakeInsights.jsx";

// Next steps offered as buttons (the server enforces the same rules).
const ACTIONS = {
  staff: {
    waiting: [["checked_in", "Mark as checked-in"], ["cancelled", "Cancel visit"], ["no_show", "Did not attend"]],
    checked_in: [["in_consultation", "Send in to doctor"], ["cancelled", "Cancel visit"], ["no_show", "Did not attend"]],
    in_consultation: [["completed", "Complete visit"]],
  },
  doctor: {
    checked_in: [["in_consultation", "Call patient in"]],
    in_consultation: [["completed", "Complete consultation"]],
  },
};

export default function VisitWorkspace({ entryId, role, go, notify, onBack }) {
  const [v, SetV] = useState(null);
  const [busy, SetBusy] = useState(false);
  const [note, SetNote] = useState("");
  const [doctors, SetDoctors] = useState([]);
  const [departments, SetDepartments] = useState([]);
  const [showOriginal, SetShowOriginal] = useState(false);
  // appointment booking (staff)
  const [bDoctor, SetBDoctor] = useState("");
  const [bDay, SetBDay] = useState(todayLocal());
  const [slots, SetSlots] = useState(null);
  const [bSlot, SetBSlot] = useState("");
  const [bReason, SetBReason] = useState("");
  const isStaff = role === "staff";

  useEffect(() => {
    getVisit(entryId).then(SetV).catch((err) => notify(err.message));
    if (isStaff) {
      listDoctors().then(SetDoctors).catch(() => SetDoctors([]));
      listDepartments().then(SetDepartments).catch(() => SetDepartments([]));
    }
  }, [entryId]);

  useEffect(() => {
    SetSlots(null);
    SetBSlot("");
    if (isStaff && bDoctor && bDay) {
      listSlots(bDoctor, bDay).then(SetSlots).catch((err) => notify(err.message));
    }
  }, [bDoctor, bDay]);

  const run = async (fn, okText) => {
    if (busy) return;
    SetBusy(true);
    try {
      const updated = await fn();
      if (updated && updated.id) SetV(updated);
      if (okText) notify(okText);
    } catch (err) {
      notify(err.message);
    } finally {
      SetBusy(false);
    }
  };

  if (!v) {
    return (
      <div className="workspace">
        <main>
          <p className="empty">Loading...</p>
        </main>
      </div>
    );
  }
  const actions = (ACTIONS[role] || {})[v.status] || [];
  const open = ["waiting", "checked_in", "in_consultation"].includes(v.status);

  return (
    <div className="workspace">
      <aside className="staff-sidebar compact">
        <Brand go={go} />
        <nav>
          <button onClick={onBack} aria-label="Back to overview">
            <LayoutDashboard />
          </button>
        </nav>
      </aside>
      <main>
        <header className="dash-head">
          <div>
            <span className="eyebrow">{isStaff ? "RECEPTION / PATIENT QUEUE" : "DOCTOR DASHBOARD / MY PATIENTS"}</span>
            <h2>Patient visit</h2>
            <p>
              {v.department.name} · token {v.token} · {formatDate(v.created_at)}
            </p>
          </div>
          <div className="workspace-links">
            <button className="link" onClick={onBack}>
              <ArrowLeft /> Back to overview
            </button>
          </div>
        </header>
        <div className="workspace-grid">
          <section className="workspace-card">
            <div className="patient-title">
              <div>
                <span className="eyebrow">PATIENT DETAILS / TOKEN {v.token}</span>
                <h1>{v.patient.full_name}</h1>
                <p>
                  {v.patient.age} yrs · {v.patient.gender.replace(/_/g, " ")} · prefers{" "}
                  {LANGUAGE_NAMES[v.patient.preferred_language]}
                </p>
              </div>
              <span>
                {v.priority && <PriorityChip priority={v.priority} />} <Status value={v.status} />
              </span>
            </div>
            <div className="workspace-details">
              <div>
                <span className="eyebrow">VISIT DETAILS</span>
                <Info label="Token number" value={v.token} />
                <Info label="Arrived in queue" value={timeOnly(v.created_at)} />
                {v.position !== null && <Info label="Patients ahead" value={String(v.position)} />}
                {v.called_at && <Info label="Called in" value={timeOnly(v.called_at)} />}
              </div>
              <div>
                <span className="eyebrow">DEPARTMENT AND DOCTOR</span>
                {isStaff && open ? (
                  <>
                    <label className="field">
                      <span>Department</span>
                      <select
                        value={v.department.id}
                        disabled={busy}
                        onChange={(e) =>
                          run(() => assignVisit(v.id, { department_id: e.target.value }),
                            "Moved to another department (new token issued).")
                        }
                      >
                        {departments.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>Assigned doctor</span>
                      <select
                        value={v.doctor ? v.doctor.id : ""}
                        disabled={busy}
                        onChange={(e) =>
                          run(() => assignVisit(v.id, { doctor_user_id: e.target.value || null }),
                            e.target.value ? "Doctor assigned and notified." : "Doctor unassigned.")
                        }
                      >
                        <option value="">Not assigned</option>
                        {doctors.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.full_name}
                            {d.departments.length ? ` (${d.departments.join(", ")})` : ""}
                          </option>
                        ))}
                      </select>
                    </label>
                  </>
                ) : (
                  <>
                    <h3>{v.doctor ? v.doctor.name : "Doctor not assigned"}</h3>
                    <p>{v.department.name}</p>
                  </>
                )}
              </div>
            </div>
            <div className="workspace-section">
              <span className="eyebrow">CONFIRMED INTAKE</span>
              {v.intake ? (
                <>
                  <p className="intake-done">
                    <CheckCircle2 /> Reviewed by staff · {v.intake.confirmed_department || "—"}
                  </p>
                  <p style={{ whiteSpace: "pre-wrap" }}>{v.intake.final_text}</p>
                  <button className="link" onClick={() => SetShowOriginal(!showOriginal)}>
                    {showOriginal ? "Hide" : "Show"} patient's original words (
                    {LANGUAGE_NAMES[v.intake.original_language]})
                  </button>
                  {showOriginal && (
                    <p dir="auto" style={{ whiteSpace: "pre-wrap" }}>
                      {v.intake.original_text}
                    </p>
                  )}
                </>
              ) : (
                <p>No intake linked to this visit (walk-in).</p>
              )}
            </div>
            {role === "doctor" && v.intake_id && <DoctorIntakeDetails intakeId={v.intake_id} notify={notify} />}
            <div className="workspace-section">
              <span className="eyebrow">CARE-TEAM NOTES</span>
              {v.notes.map((n) => (
                <p key={n.id}>
                  <b>{n.author || "Staff"}</b> · <small>{formatDate(n.created_at)}</small>
                  <br />
                  {n.text}
                </p>
              ))}
              <textarea
                value={note}
                onChange={(e) => SetNote(e.target.value)}
                placeholder="Add an internal note for the care team..."
              />
              <Btn
                kind="outline"
                disabled={busy || !note.trim()}
                onClick={() =>
                  run(async () => {
                    const r = await addVisitNote(v.id, note);
                    SetNote("");
                    return r;
                  }, "Note saved.")
                }
              >
                Save note
              </Btn>
            </div>
          </section>
          <aside>
            <div className="side-card">
              <span className="eyebrow">NEXT STEP</span>
              {!actions.length && <p>{open ? "Waiting for front-desk check-in." : "This visit is closed."}</p>}
              {actions.map(([status, label]) => (
                <button
                  key={status}
                  disabled={busy}
                  onClick={() =>
                    run(() => setVisitStatus(v.id, status), `${QUEUE_STATUS[status].label}.`)
                  }
                >
                  {status === "completed" ? <Check /> : status === "in_consultation" ? <Stethoscope /> : status === "checked_in" ? <CheckCircle2 /> : <X />}{" "}
                  {label}
                </button>
              ))}
            </div>
            {isStaff && (
              <div className="side-card">
                <span className="eyebrow">BOOK AN APPOINTMENT</span>
                <label className="field">
                  <span>Doctor</span>
                  <select value={bDoctor} onChange={(e) => SetBDoctor(e.target.value)}>
                    <option value="">Choose a doctor...</option>
                    {doctors.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.full_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>Date</span>
                  <input type="date" value={bDay} min={todayLocal()} onChange={(e) => SetBDay(e.target.value)} />
                </label>
                {bDoctor && (
                  <label className="field">
                    <span>Time</span>
                    <select value={bSlot} onChange={(e) => SetBSlot(e.target.value)}>
                      <option value="">
                        {slots === null ? "Loading..." : slots.length ? "Choose a time..." : "No free times this day"}
                      </option>
                      {(slots || []).map((s) => (
                        <option key={s.starts_at} value={s.starts_at}>
                          {timeOnly(s.starts_at)} · {s.department}
                          {s.room ? ` · ${s.room}` : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <input
                  className="reason"
                  placeholder="Reason (optional)"
                  value={bReason}
                  maxLength={300}
                  onChange={(e) => SetBReason(e.target.value)}
                />
                <button
                  disabled={busy || !bSlot}
                  onClick={() =>
                    run(async () => {
                      await bookAppointment(v.patient.id, bDoctor, bSlot, bReason);
                      SetBSlot("");
                      SetBReason("");
                      SetSlots(await listSlots(bDoctor, bDay));
                    }, "Appointment booked. The patient has been notified.")
                  }
                >
                  <Check /> Book appointment
                </button>
              </div>
            )}
            <div className="side-card">
              <span className="eyebrow">REMINDER</span>
              <p>
                Intake information was reviewed by staff, but clinical decisions
                remain with the treating doctor.
              </p>
              <p className="notice">
                <ShieldCheck /> HealthSpeak AI does not diagnose or prescribe.
              </p>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
