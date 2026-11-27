// Staff intake review add-ons: per-symptom review and the patient's earlier encounters.
// Everything here is shown only to authorised staff; data stays in component state.
import React, { useEffect, useState } from "react";
import { Check, X } from "lucide-react";
import { Btn } from "../../components/ui.jsx";
import { addSymptom, getIntakeHistory, reviewSymptom, setIntakePriority } from "../../services/intake.js";

export const SYMPTOM_STATUS = {
  current: { label: "Current", tone: "blue" },
  uncertain: { label: "Patient unsure", tone: "wait" },
  negated: { label: "Denied", tone: "done" },
  historical: { label: "Past (not current)", tone: "wait" },
  third_party: { label: "Another person", tone: "wait" },
};

const REVIEW_LABEL = {
  unreviewed: "AI-extracted · not confirmed",
  confirmed: "Confirmed by staff",
  corrected: "Corrected by staff",
  rejected: "Rejected by staff",
};

const day = (iso) => {
  try {
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return "";
  }
};

const detailText = (attrs) => {
  const out = [];
  for (const key of ["severity", "duration", "frequency", "timing"]) {
    if (attrs && attrs[key] && attrs[key].text) {
      out.push(`${key}: "${attrs[key].text}"${attrs[key].shared ? " (whole sentence)" : ""}`);
    }
  }
  if (attrs && attrs.triggers && attrs.triggers.length) {
    out.push(`trigger: "${attrs.triggers.map((t) => t.text).join('", "')}"`);
  }
  return out;
};

// ---------- priority (Urgent / Normal) ----------

export function PriorityChip({ priority, source }) {
  const urgent = priority === "urgent";
  return (
    <span
      className={"status priority " + (urgent ? "urgent" : "normal")}
      data-testid="priority-chip"
      title={source === "staff" ? "Set by a staff member" : "Set by the emergency rules"}
    >
      {urgent ? "Urgent" : "Normal"}
    </span>
  );
}

// Review screen: the saved priority, why, and a staff-only way to change it (a reason is required).
export function PriorityPanel({ intake, notify, onChanged }) {
  const [open, SetOpen] = useState(false);
  const [value, SetValue] = useState(intake.priority === "urgent" ? "normal" : "urgent");
  const [reason, SetReason] = useState("");
  const [busy, SetBusy] = useState(false);
  const urgent = intake.priority === "urgent";
  const save = async () => {
    SetBusy(true);
    try {
      onChanged(await setIntakePriority(intake.id, value, reason.trim()));
      SetOpen(false);
      SetReason("");
    } catch (err) {
      notify(err.message);
    } finally {
      SetBusy(false);
    }
  };
  return (
    <div className={"workspace-section priority-panel" + (urgent ? " urgent" : "")} data-testid="priority-panel">
      <span className="eyebrow">PRIORITY</span>
      <div className="symptom-head">
        <PriorityChip priority={intake.priority} source={intake.priority_source} />
        <small>
          {intake.priority_source === "staff"
            ? "Set by staff"
            : urgent
              ? "Set by the emergency rules (an emergency symptom or attention rule was found)"
              : "No emergency symptom was found by the rules"}
        </small>
      </div>
      {intake.priority_reason && <small>Reason: {intake.priority_reason}</small>}
      {urgent && intake.priority_source !== "staff" && (
        <small>The system only ever raises this flag. Only a staff member can lower it, with a reason.</small>
      )}
      {intake.review_status !== "confirmed" && !open && (
        <div className="actions">
          <Btn kind="outline" onClick={() => SetOpen(true)}>
            Change priority
          </Btn>
        </div>
      )}
      {open && (
        <div className="actions">
          <select value={value} onChange={(e) => SetValue(e.target.value)} aria-label="New priority">
            <option value="urgent">Urgent</option>
            <option value="normal">Normal</option>
          </select>
          <input
            className="reason"
            value={reason}
            maxLength={500}
            placeholder="Reason for the change (required)"
            aria-label="Reason for the priority change"
            onChange={(e) => SetReason(e.target.value)}
          />
          <Btn disabled={busy || reason.trim().length < 3 || value === intake.priority} onClick={save}>
            Save priority
          </Btn>
          <Btn kind="outline" onClick={() => SetOpen(false)}>
            Cancel
          </Btn>
        </div>
      )}
    </div>
  );
}

// ---------- evidence ("confidence") ----------

const EVIDENCE_TONE = { exact: "done", possible: "wait", staff: "blue", missing: "empty", rejected: "empty" };

export function EvidenceChip({ evidence }) {
  if (!evidence) return null;
  return (
    <span
      className={"status evidence " + EVIDENCE_TONE[evidence.level]}
      data-testid="evidence-chip"
      data-level={evidence.level}
    >
      {evidence.label}
    </span>
  );
}

const FIELD_NAME = {
  symptoms: "Symptoms",
  duration: "Duration",
  severity: "Severity",
  medicines: "Medicines",
  allergies: "Allergies",
  department: "Department",
};

// One row per extracted field: how it was found, so staff can see what needs attention first.
export function FieldEvidencePanel({ fields }) {
  if (!fields || !fields.length) return null;
  return (
    <div className="workspace-section field-evidence" data-testid="field-evidence">
      <span className="eyebrow">HOW EACH FIELD WAS FOUND</span>
      {fields.map((f) => (
        <div className="field-row" key={f.field} data-field={f.field}>
          <b>{FIELD_NAME[f.field] || f.field}</b>
          <span className={"status evidence " + EVIDENCE_TONE[f.level]} data-level={f.level}>
            {f.label}
          </span>
          <small>{f.detail}</small>
          {f.notes.map((n) => (
            <small key={n}>{n}</small>
          ))}
        </div>
      ))}
      <small>These labels show how a field was found. They are not a clinical certainty or a probability.</small>
    </div>
  );
}

export function StatusChip({ value }) {
  const s = SYMPTOM_STATUS[value] || { label: value, tone: "wait" };
  return <span className={"status " + s.tone}>{s.label}</span>;
}

// ---------- symptoms of THIS encounter ----------

export function SymptomsPanel({ intake, notify }) {
  const [items, SetItems] = useState(intake.symptoms || []);
  const [busyId, SetBusyId] = useState("");
  const [editing, SetEditing] = useState("");
  const [editTerm, SetEditTerm] = useState("");
  const [editStatus, SetEditStatus] = useState("");
  const [addTerm, SetAddTerm] = useState("");
  const [addStatus, SetAddStatus] = useState("current");
  const locked = intake.review_status === "confirmed";

  const replace = (updated) => SetItems((cur) => cur.map((s) => (s.id === updated.id ? updated : s)));

  const act = async (symptom, payload) => {
    SetBusyId(symptom.id);
    try {
      replace(await reviewSymptom(intake.id, symptom.id, payload));
      SetEditing("");
    } catch (err) {
      notify(err.message);
    } finally {
      SetBusyId("");
    }
  };

  const add = async () => {
    if (!addTerm.trim()) return;
    SetBusyId("add");
    try {
      const created = await addSymptom(intake.id, { term: addTerm.trim(), status: addStatus });
      SetItems((cur) => [...cur, created]);
      SetAddTerm("");
    } catch (err) {
      notify(err.message);
    } finally {
      SetBusyId("");
    }
  };

  return (
    <div className="workspace-section symptoms">
      <span className="eyebrow">SYMPTOMS · AI-EXTRACTED UNTIL STAFF CONFIRM</span>
      {!items.length && (
        <p>
          No symptoms were extracted for this intake. Read the patient's original words; if the
          summary above is from an older version, use "Re-create summary".
        </p>
      )}
      {items.map((s) => {
        const rejected = s.review_status === "rejected";
        return (
          <div key={s.id} className={"symptom-row" + (rejected ? " rejected" : "")}>
            <div className="symptom-head">
              <b>{s.effective_term}</b>
              <StatusChip value={s.effective_status} />
              <EvidenceChip evidence={s.evidence} />
              <small>{REVIEW_LABEL[s.review_status]}</small>
            </div>
            {s.evidence_text && (
              <small>
                Patient's words: <q>{s.evidence_text}</q>
              </small>
            )}
            {s.effective_term !== s.term && <small>AI read this as: {s.term}</small>}
            {s.evidence && s.evidence.notes.map((n) => (
              <small key={n}>{n}</small>
            ))}
            {s.effective_status !== s.status && <small>AI read the status as: {SYMPTOM_STATUS[s.status]?.label}</small>}
            {detailText(s.attributes).map((d) => (
              <small key={d}>{d}</small>
            ))}
            {s.review_note && <small>Staff note: {s.review_note}</small>}
            {!locked && editing !== s.id && (
              <div className="actions">
                <Btn kind="outline" disabled={Boolean(busyId)} onClick={() => act(s, { action: "confirm" })}>
                  <Check /> Confirm
                </Btn>
                <Btn kind="outline" disabled={Boolean(busyId)} onClick={() => act(s, { action: "reject" })}>
                  <X /> Not a symptom
                </Btn>
                <Btn
                  kind="outline"
                  disabled={Boolean(busyId)}
                  onClick={() => {
                    SetEditing(s.id);
                    SetEditTerm(s.effective_term);
                    SetEditStatus(s.effective_status);
                  }}
                >
                  Correct
                </Btn>
              </div>
            )}
            {!locked && editing === s.id && (
              <div className="actions">
                <input
                  className="reason"
                  value={editTerm}
                  maxLength={60}
                  onChange={(e) => SetEditTerm(e.target.value)}
                  aria-label="Symptom name"
                />
                <select value={editStatus} onChange={(e) => SetEditStatus(e.target.value)} aria-label="Status">
                  {Object.entries(SYMPTOM_STATUS).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v.label}
                    </option>
                  ))}
                </select>
                <Btn
                  disabled={Boolean(busyId) || !editTerm.trim()}
                  onClick={() => act(s, { action: "correct", term: editTerm.trim(), status: editStatus })}
                >
                  Save correction
                </Btn>
                <Btn kind="outline" onClick={() => SetEditing("")}>
                  Cancel
                </Btn>
              </div>
            )}
          </div>
        );
      })}
      {!locked && (
        <div className="actions symptom-add">
          <input
            className="reason"
            value={addTerm}
            maxLength={60}
            placeholder="Add a symptom the system missed"
            aria-label="Add a symptom"
            onChange={(e) => SetAddTerm(e.target.value)}
          />
          <select value={addStatus} onChange={(e) => SetAddStatus(e.target.value)} aria-label="Status of added symptom">
            {Object.entries(SYMPTOM_STATUS).map(([k, v]) => (
              <option key={k} value={k}>
                {v.label}
              </option>
            ))}
          </select>
          <Btn kind="outline" disabled={Boolean(busyId) || !addTerm.trim()} onClick={add}>
            Add
          </Btn>
        </div>
      )}
      {locked && <small>This intake is confirmed, so its symptoms are final.</small>}
    </div>
  );
}

// ---------- earlier encounters of the same verified patient ----------

const PAGE = 5;

export function HistoryPanel({ intakeId, fetchHistory = getIntakeHistory }) {
  const [state, SetState] = useState({ phase: "loading", data: null, error: "" });
  const [more, SetMore] = useState(false);

  useEffect(() => {
    let alive = true;
    SetState({ phase: "loading", data: null, error: "" });
    fetchHistory(intakeId, { limit: PAGE, offset: 0 })
      .then((data) => alive && SetState({ phase: "ready", data, error: "" }))
      .catch((err) => {
        if (!alive) return;
        SetState({
          phase: err.status === 403 || err.status === 401 ? "forbidden" : "error",
          data: null,
          error: err.message,
        });
      });
    return () => {
      alive = false;
    };
  }, [intakeId]);

  const loadMore = async () => {
    SetMore(true);
    try {
      const next = await fetchHistory(intakeId, { limit: PAGE, offset: state.data.encounters.length });
      SetState((cur) => ({ ...cur, data: { ...cur.data, encounters: [...cur.data.encounters, ...next.encounters] } }));
    } catch (err) {
      SetState((cur) => ({ ...cur, error: err.message }));
    } finally {
      SetMore(false);
    }
  };

  const { phase, data, error } = state;
  return (
    <div className="workspace-section history">
      <span className="eyebrow">EARLIER VISITS OF THIS PATIENT</span>
      {phase === "loading" && <p>Loading earlier visits…</p>}
      {phase === "forbidden" && <p>You are not authorised to view this patient's history.</p>}
      {phase === "error" && <p className="demo-note">Could not load earlier visits. {error}</p>}
      {phase === "ready" && (
        <>
          <small>{data.notice}</small>
          {!data.encounters.length && <p>No earlier visits on record. This is the patient's first visit here.</p>}
          {data.recurring.length > 0 && (
            <p className="notice">
              <b>Also reported at an earlier visit:</b>{" "}
              {data.recurring
                .map((r) => `${r.term} (${r.previous.map((p) => day(p.encounter_date)).join(", ")})`)
                .join("; ")}
              . Ask whether it is the same problem; it is not assumed to be.
            </p>
          )}
          {data.encounters.map((e) => (
            <div key={e.intake_id} className="encounter">
              <div className="symptom-head">
                <b>{day(e.encounter_date)}</b>
                <span className={"status " + (e.review_status === "confirmed" ? "done" : "wait")}>
                  {e.review_status === "confirmed" ? "Confirmed by staff" : "Not confirmed"}
                </span>
                {e.confirmed_department && <small>Department: {e.confirmed_department}</small>}
              </div>
              <p dir="auto" style={{ whiteSpace: "pre-wrap" }}>
                {e.statement}
              </p>
              {e.symptoms.length > 0 && (
                <ul>
                  {e.symptoms.map((s, i) => (
                    <li key={i}>
                      {s.term} <StatusChip value={s.status} />{" "}
                      <small>
                        {s.source === "staff_confirmed" ? "confirmed by staff" : "AI-extracted, unconfirmed"}
                        {Object.keys(s.details).length > 0 &&
                          " · " + Object.entries(s.details).map(([k, v]) => `${k}: "${v}"`).join(", ")}
                      </small>
                    </li>
                  ))}
                </ul>
              )}
              {e.medication_mentions.length > 0 && (
                <small>
                  Medicine mentioned then (not verified, not assumed current): {e.medication_mentions.join(" / ")}
                </small>
              )}
              {e.allergy_mentions.length > 0 && (
                <small>
                  Allergy mentioned then (not verified — confirm with the patient): {e.allergy_mentions.join(" / ")}
                </small>
              )}
            </div>
          ))}
          {data.encounters.length < data.total && (
            <Btn kind="outline" disabled={more} onClick={loadMore}>
              Show older visits ({data.total - data.encounters.length} more)
            </Btn>
          )}
        </>
      )}
    </div>
  );
}
