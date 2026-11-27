// Read-only intake details for the doctor a visit is assigned to: priority, symptoms, how each field was
// found, and the patient's earlier visits. Doctors cannot edit anything here; clinical decisions stay theirs.
import React, { useEffect, useState } from "react";
import { getDoctorIntake, getDoctorIntakeHistory } from "../../services/doctors.js";
import {
  EvidenceChip,
  FieldEvidencePanel,
  HistoryPanel,
  PriorityChip,
  StatusChip,
} from "../staff/IntakeInsights.jsx";

export default function DoctorIntakeDetails({ intakeId, notify }) {
  const [intake, SetIntake] = useState(null);
  useEffect(() => {
    let alive = true;
    SetIntake(null);
    getDoctorIntake(intakeId)
      .then((i) => alive && SetIntake(i))
      .catch((err) => alive && notify(err.message));
    return () => {
      alive = false;
    };
  }, [intakeId]);

  if (!intake) return <p className="empty">Loading intake details...</p>;
  const symptoms = (intake.symptoms || []).filter((s) => s.review_status !== "rejected");
  return (
    <div data-testid="doctor-intake">
      <div className="workspace-section">
        <span className="eyebrow">PRIORITY</span>
        <p>
          <PriorityChip priority={intake.priority} source={intake.priority_source} />{" "}
          <small>{intake.priority_source === "staff" ? "Set by a staff member" : "Set by the emergency rules"}</small>
        </p>
        {intake.priority_reason && <small>Reason: {intake.priority_reason}</small>}
      </div>
      <div className="workspace-section symptoms">
        <span className="eyebrow">SYMPTOMS · AI-EXTRACTED UNTIL STAFF CONFIRM</span>
        {!symptoms.length && <p>No symptoms were extracted. Please read the patient's words.</p>}
        {symptoms.map((s) => (
          <div key={s.id} className="symptom-row">
            <div className="symptom-head">
              <b>{s.effective_term}</b>
              <StatusChip value={s.effective_status} />
              <EvidenceChip evidence={s.evidence} />
            </div>
            {s.evidence_text && (
              <small>
                Patient's words: <q>{s.evidence_text}</q>
              </small>
            )}
          </div>
        ))}
      </div>
      <FieldEvidencePanel fields={intake.field_evidence} />
      <HistoryPanel intakeId={intakeId} fetchHistory={getDoctorIntakeHistory} />
    </div>
  );
}
