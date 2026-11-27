// Shown to a doctor whose account is not (yet) approved. It contains NO patient information and the server
// refuses every doctor endpoint for this account, so this page is only an explanation.
import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Clock3, LogOut, RefreshCw, ShieldAlert } from "lucide-react";
import { Brand, Btn, Info } from "../../components/ui.jsx";
import { getMyVerification } from "../../services/doctors.js";

export default function PendingVerification({ go, notify, user, onLogout, onRecheck }) {
  const { t } = useTranslation();
  const L = (key, fallback) => t(key, { defaultValue: fallback });
  const [v, SetV] = useState(null);
  const [busy, SetBusy] = useState(false);

  const load = () => getMyVerification().then(SetV).catch((err) => notify(err.message));
  useEffect(() => {
    load();
  }, []);

  const recheck = async () => {
    SetBusy(true);
    try {
      await onRecheck(); // reloads the account; moves to the doctor dashboard if it was approved
      await load();
    } finally {
      SetBusy(false);
    }
  };

  const rejected = (v ? v.status : user.verification_status) === "rejected";
  const p = v && v.profile;
  return (
    <div className="pending-page" data-testid="pending-verification">
      <header className="pending-top">
        <Brand go={go} />
        <button className="link" onClick={onLogout}>
          <LogOut /> {t("common.logout")}
        </button>
      </header>
      <main className="pending-card">
        <span className={"pending-icon " + (rejected ? "rejected" : "")}>{rejected ? <ShieldAlert /> : <Clock3 />}</span>
        <span className="eyebrow">
          {rejected ? L("pending.rejectedEyebrow", "VERIFICATION NOT APPROVED") : L("pending.eyebrow", "PENDING VERIFICATION")}
        </span>
        <h2>
          {rejected
            ? L("pending.rejectedTitle", "Your doctor account was not approved")
            : L("pending.title", "Your account is waiting for verification")}
        </h2>
        <p>
          {rejected
            ? L("pending.rejectedText", "An administrator reviewed your details and did not approve this account. You cannot see patient information.")
            : L("pending.text", "Thank you for registering, {{name}}. An administrator will check your registration details. Until then you cannot see any patient information.", { name: user.full_name })}
        </p>
        {rejected && p && p.review_note && (
          <p className="notice" data-testid="review-note">
            {L("pending.reason", "Reason given")}: {p.review_note}
          </p>
        )}
        {p && (
          <div className="summary-grid">
            <Info label={L("doctorReg.qualification", "Medical qualification")} value={p.qualification} />
            <Info label={L("doctorReg.specialization", "Specialization")} value={p.specialization} />
            <Info label={L("doctorReg.regNumber", "Medical registration number")} value={p.registration_number} />
            <Info label={L("doctorReg.authority", "State medical council / registration authority")} value={p.registration_authority} />
            <Info label={L("doctorReg.hospital", "Hospital or clinic")} value={p.hospital_name} />
          </div>
        )}
        <div className="actions">
          <Btn kind="outline" onClick={recheck} disabled={busy}>
            <RefreshCw /> {L("pending.check", "Check again")}
          </Btn>
        </div>
        <small>{L("pending.note", "Approval is decided only by an administrator. Submitting these details does not give any access.")}</small>
      </main>
    </div>
  );
}
