// Administrator: review doctor applications. Approve only after checking the registration number with the
// named council; rejecting needs a reason that the doctor sees. Every decision is audited by the server.
import React, { useEffect, useState } from "react";
import { Check, X } from "lucide-react";
import { Btn } from "../../components/ui.jsx";
import { approveDoctor, listDoctorApplications, rejectDoctor } from "../../services/doctors.js";
import { formatDate } from "../../services/intake.js";

const TONE = { pending: "wait", approved: "done", rejected: "empty" };

export default function DoctorApprovals({ notify }) {
  const [status, SetStatus] = useState("pending");
  const [data, SetData] = useState(null);
  const [reasons, SetReasons] = useState({});
  const [busy, SetBusy] = useState("");

  const load = () =>
    listDoctorApplications(status).then(SetData).catch((err) => {
      SetData({ items: [], total: 0 });
      notify(err.message);
    });
  useEffect(() => {
    SetData(null);
    load();
  }, [status]);

  const decide = async (id, approve) => {
    const note = (reasons[id] || "").trim();
    if (!approve && note.length < 3) return notify("Write a short reason before rejecting.");
    SetBusy(id);
    try {
      await (approve ? approveDoctor(id, note) : rejectDoctor(id, note));
      notify(approve ? "Doctor approved. They now have doctor access." : "Application rejected.");
      await load();
    } catch (err) {
      notify(err.message);
    } finally {
      SetBusy("");
    }
  };

  return (
    <section className="queue" data-testid="doctor-approvals">
      <div className="section-title">
        <div>
          <span className="eyebrow">DOCTOR VERIFICATION</span>
          <h3>Doctor applications</h3>
        </div>
        <select value={status} onChange={(e) => SetStatus(e.target.value)} aria-label="Filter by status">
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="">All</option>
        </select>
      </div>
      <small>
        The details below were typed by the applicant and are not proof. Check the registration number with the named
        council before approving.
      </small>
      {data === null && <p className="empty">Loading...</p>}
      {data && !data.items.length && <p className="empty">No applications in this list.</p>}
      {(data ? data.items : []).map(({ user, profile }) => (
        <div className="workspace-section" key={user.id} data-testid="doctor-application">
          <div className="symptom-head">
            <b>{user.full_name}</b>
            <span className={"status " + TONE[profile.verification_status]}>{profile.verification_status}</span>
            <small>Applied {formatDate(profile.created_at)}</small>
          </div>
          <p>
            {profile.qualification} · {profile.specialization} · {profile.years_experience} yrs experience
            <br />
            Registration <b>{profile.registration_number}</b> ({profile.registration_authority})
            <br />
            {profile.hospital_name} · {user.email} · {user.phone}
          </p>
          {profile.verification_status === "pending" ? (
            <div className="actions">
              <input
                className="reason"
                placeholder="Reason (required to reject, optional note to approve)"
                maxLength={500}
                value={reasons[user.id] || ""}
                onChange={(e) => SetReasons((r) => ({ ...r, [user.id]: e.target.value }))}
              />
              <Btn disabled={busy === user.id} onClick={() => decide(user.id, true)}>
                <Check /> Approve
              </Btn>
              <Btn kind="outline" disabled={busy === user.id} onClick={() => decide(user.id, false)}>
                <X /> Reject
              </Btn>
            </div>
          ) : (
            profile.review_note && <small>Note: {profile.review_note}</small>
          )}
        </div>
      ))}
    </section>
  );
}
