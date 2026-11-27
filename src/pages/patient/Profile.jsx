// "My Profile": the patient's basic details. Changing them never alters past visit records.
import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import { Btn, Field, Info } from "../../components/ui.jsx";
import { GENDER_CODES, LANGUAGE_CODES, getMyProfile, updateMyProfile } from "../../services/auth.js";
import { translateError } from "../../i18n/index.js";
import PhoneSection from "./PhoneSection.jsx";
import { displayLanguageFor } from "../../i18n/languages.js";

export default function Profile({ onBack, onSaved, notify }) {
  const { t } = useTranslation();
  const [profile, SetProfile] = useState(null);
  const [form, SetForm] = useState(null);
  const [saving, SetSaving] = useState(false);

  useEffect(() => {
    getMyProfile()
      .then((p) => {
        SetProfile(p);
        SetForm({
          full_name: p.full_name,
          date_of_birth: p.date_of_birth,
          gender: p.gender,
          preferred_language: p.preferred_language,
        });
      })
      .catch((err) => notify(translateError(err)));
  }, []);

  const set = (k) => (e) => SetForm({ ...form, [k]: e.target.value });
  const dirty =
    profile && form && Object.keys(form).some((k) => form[k] !== profile[k]);

  const save = async (e) => {
    e.preventDefault();
    if (!dirty || saving) return;
    if (!form.full_name.trim()) return notify(t("profile.nameRequired"));
    SetSaving(true);
    try {
      // Send only what changed.
      const changes = {};
      Object.keys(form).forEach((k) => {
        if (form[k] !== profile[k]) changes[k] = form[k];
      });
      const updated = await updateMyProfile(changes);
      SetProfile(updated);
      SetForm({
        full_name: updated.full_name,
        date_of_birth: updated.date_of_birth,
        gender: updated.gender,
        preferred_language: updated.preferred_language,
      });
      onSaved(updated);
      notify(t("profile.saved"));
    } catch (err) {
      notify(translateError(err));
    } finally {
      SetSaving(false);
    }
  };

  return (
    <div className="summary">
      <header>
        <div>
          <h2>{t("profile.title")}</h2>
        </div>
        <Btn kind="outline" onClick={onBack}>
          <ArrowLeft /> {t("common.back")}
        </Btn>
      </header>
      <main>
        {!form ? (
          <p className="empty">{t("common.loading")}</p>
        ) : (
          <form className="structured profile-form" onSubmit={save}>
            <Field
              label={t("auth.fullName")}
              value={form.full_name}
              onChange={set("full_name")}
              maxLength={120}
              required
            />
            <div className="two">
              <Field
                label={t("auth.dob")}
                type="date"
                value={form.date_of_birth}
                onChange={set("date_of_birth")}
                max={new Date().toISOString().slice(0, 10)}
                required
              />
              <label className="field">
                <span>{t("auth.gender")}</span>
                <select value={form.gender} onChange={set("gender")}>
                  {Object.entries(GENDER_CODES).map(([label, code]) => (
                    <option key={code} value={code}>
                      {t(`gender.${label}`)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="field">
              <span>{t("auth.speakingLanguage")}</span>
              <select value={displayLanguageFor(form.preferred_language)} onChange={set("preferred_language")}>
                {Object.values(LANGUAGE_CODES).map((code) => (
                  <option key={code} value={code}>
                    {t(`lang.${code}`)}
                  </option>
                ))}
              </select>
            </label>
            <div className="summary-grid">
              <Info label={t("profile.email")} value={profile.email || "—"} />
            </div>
            <PhoneSection
              profile={profile}
              notify={notify}
              onChanged={(p) => {
                SetProfile(p);
                onSaved(p);
              }}
            />
            <p className="disclaimer">
              <ShieldCheck /> {t("profile.historyUnchanged")}
            </p>
            <div className="actions">
              <Btn type="submit" disabled={!dirty || saving}>
                {saving ? t("profile.saving") : t("profile.save")}
              </Btn>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}
