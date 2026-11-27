// Forgot password: a one-time code is sent by SMS to the patient's mobile number.
import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Btn, Field, ModalBox } from "../../components/ui.jsx";
import { confirmPasswordReset, requestPasswordReset } from "../../services/auth.js";
import { translateError } from "../../i18n/index.js";
import DevSmsNotice from "../../components/DevSmsNotice.jsx";

export default function ForgotPassword({ initialIdentifier = "", close, onDone, notify }) {
  const { t } = useTranslation();
  const [step, SetStep] = useState(1);
  const [identifier, SetIdentifier] = useState(initialIdentifier);
  const [code, SetCode] = useState("");
  const [pw, SetPw] = useState("");
  const [pw2, SetPw2] = useState("");
  const [busy, SetBusy] = useState(false);
  const [dev, SetDev] = useState(null); // development-only: the code, because no real SMS is sent

  const send = async () => {
    if (!identifier.trim()) return notify(t("forgot.needMobile"));
    if (busy) return;
    SetBusy(true);
    try {
      const res = await requestPasswordReset(identifier);
      // Only present on a development server (APP_ENV=development, console SMS): never in production.
      SetDev(res && res.dev_code ? { code: res.dev_code, notice: res.dev_notice } : null);
      SetStep(2); // same screen whether or not the account exists
    } catch (err) {
      notify(translateError(err));
    } finally {
      SetBusy(false);
    }
  };

  const reset = async () => {
    if (!/^\d{6}$/.test(code.trim())) return notify(t("forgot.needCode"));
    if (pw.length < 8) return notify(t("forgot.pwShort"));
    if (pw !== pw2) return notify(t("forgot.pwMismatch"));
    if (busy) return;
    SetBusy(true);
    try {
      await confirmPasswordReset(identifier, code, pw);
      notify(t("forgot.done"));
      onDone(identifier);
    } catch (err) {
      notify(translateError(err));
    } finally {
      SetBusy(false);
    }
  };

  return (
    <ModalBox title={t("auth.forgotTitle")} close={close}>
      {step === 1 ? (
        <>
          <p>{t("forgot.intro")}</p>
          <Field
            label={t("auth.mobile")}
            placeholder={t("auth.mobilePh")}
            value={identifier}
            onChange={(e) => SetIdentifier(e.target.value)}
            autoComplete="tel"
          />
          <Btn onClick={send} disabled={busy}>
            {busy ? t("forgot.sending") : t("forgot.sendCode")}
          </Btn>
          <p className="small-note">{t("forgot.staffNote")}</p>
        </>
      ) : (
        <>
          <p>{t("forgot.sent")}</p>
          {dev && <DevSmsNotice code={dev.code} />}
          <Field
            label={t("forgot.code")}
            value={code}
            onChange={(e) => SetCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
          />
          <Field
            label={t("forgot.newPassword")}
            type="password"
            value={pw}
            onChange={(e) => SetPw(e.target.value)}
            autoComplete="new-password"
          />
          <Field
            label={t("forgot.confirmPassword")}
            type="password"
            value={pw2}
            onChange={(e) => SetPw2(e.target.value)}
            autoComplete="new-password"
          />
          <Btn onClick={reset} disabled={busy}>
            {busy ? t("forgot.saving") : t("forgot.reset")}
          </Btn>
          <Btn kind="outline" onClick={send} disabled={busy}>
            {t("forgot.resend")}
          </Btn>
        </>
      )}
    </ModalBox>
  );
}
