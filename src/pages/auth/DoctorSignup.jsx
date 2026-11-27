// Doctor registration. This only SUBMITS an application: the account starts as "Pending verification"
// and has no access to patient information until an administrator approves it. The details typed here are
// claims, not proof; the administrator checks the registration number with the named council.
import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { ArrowLeft } from "lucide-react";
import { Btn, Field } from "../../components/ui.jsx";
import { registerDoctor } from "../../services/doctors.js";
import { translateError } from "../../i18n/index.js";

const EMPTY = {
  full_name: "",
  email: "",
  phone: "",
  password: "",
  qualification: "",
  specialization: "",
  registration_number: "",
  registration_authority: "",
  hospital_name: "",
  years_experience: "",
};

export default function DoctorSignup({ go, notify, onRegistered }) {
  const { t, i18n } = useTranslation();
  const [f, SetF] = useState(EMPTY);
  const [agreed, SetAgreed] = useState(false);
  const [busy, SetBusy] = useState(false);
  const set = (k) => (e) => SetF((cur) => ({ ...cur, [k]: e.target.value }));
  const L = (key, fallback) => t(key, { defaultValue: fallback });

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    if (Object.values(f).some((v) => !String(v).trim()) || f.password.length < 8)
      return notify(L("doctorReg.completeAll", "Please fill in every field (password: at least 8 characters)."));
    if (!agreed) return notify(L("doctorReg.agreeFirst", "Please confirm the declaration first."));
    SetBusy(true);
    try {
      const user = await registerDoctor({
        ...f,
        years_experience: Number(f.years_experience),
        ui_language: i18n.language,
      });
      SetF(EMPTY);
      onRegistered(user);
    } catch (err) {
      notify(translateError(err));
    } finally {
      SetBusy(false);
    }
  };

  return (
    <form className="auth-form signup" onSubmit={submit} data-testid="doctor-signup">
      <button type="button" className="back" onClick={() => go("login")}>
        <ArrowLeft /> {L("doctorReg.back", "Back to login")}
      </button>
      <span className="eyebrow">{L("doctorReg.eyebrow", "DOCTOR REGISTRATION")}</span>
      <h2>{L("doctorReg.title", "Register as a doctor")}</h2>
      <p>
        {L(
          "doctorReg.intro",
          "Your account will be created as Pending Verification. You will not see any patient information until an administrator has checked your registration and approved your account.",
        )}
      </p>
      <Field label={L("doctorReg.fullName", "Full name")} value={f.full_name} onChange={set("full_name")} maxLength={120} required />
      <div className="two">
        <Field label={L("doctorReg.email", "Email")} type="email" value={f.email} onChange={set("email")} autoComplete="email" required />
        <Field label={L("doctorReg.phone", "Mobile number")} value={f.phone} onChange={set("phone")} inputMode="tel" autoComplete="tel" required />
      </div>
      <div className="two">
        <Field label={L("doctorReg.qualification", "Medical qualification")} placeholder="MBBS, MD (Medicine)" value={f.qualification} onChange={set("qualification")} maxLength={120} required />
        <Field label={L("doctorReg.specialization", "Specialization")} placeholder="General Medicine" value={f.specialization} onChange={set("specialization")} maxLength={120} required />
      </div>
      <div className="two">
        <Field label={L("doctorReg.regNumber", "Medical registration number")} value={f.registration_number} onChange={set("registration_number")} maxLength={64} required />
        <Field label={L("doctorReg.authority", "State medical council / registration authority")} value={f.registration_authority} onChange={set("registration_authority")} maxLength={120} required />
      </div>
      <div className="two">
        <Field label={L("doctorReg.hospital", "Hospital or clinic")} value={f.hospital_name} onChange={set("hospital_name")} maxLength={160} required />
        <Field label={L("doctorReg.years", "Years of experience")} type="number" min="0" max="70" value={f.years_experience} onChange={set("years_experience")} required />
      </div>
      <label className="field">
        <span>{L("auth.createPassword", "Create a password")}</span>
        <input type="password" value={f.password} onChange={set("password")} minLength="8" autoComplete="new-password" required />
      </label>
      <label className="check">
        <input type="checkbox" checked={agreed} onChange={(e) => SetAgreed(e.target.checked)} required />{" "}
        {L(
          "doctorReg.declaration",
          "I confirm these details are true. I understand that they will be checked and that I cannot use the doctor dashboard until an administrator approves my account.",
        )}
      </label>
      <Btn type="submit" disabled={busy}>
        {busy ? L("doctorReg.submitting", "Submitting...") : L("doctorReg.submit", "Submit for verification")}
      </Btn>
    </form>
  );
}
