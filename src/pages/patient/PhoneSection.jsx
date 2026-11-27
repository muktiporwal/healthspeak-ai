// Mobile number: shows whether it is verified, and adds / changes it with an SMS code.
// The code goes to the NEW number; the current number keeps working until the code is confirmed.
import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { BadgeCheck, TriangleAlert } from "lucide-react";
import { Btn, Field } from "../../components/ui.jsx";
import { confirmPhoneCode, requestPhoneCode } from "../../services/auth.js";
import { translateError } from "../../i18n/index.js";
import DevSmsNotice from "../../components/DevSmsNotice.jsx";

export default function PhoneSection({ profile, onChanged, notify }) {
  const { t } = useTranslation();
  const [open, SetOpen] = useState(false);
  const [phone, SetPhone] = useState("");
  const [code, SetCode] = useState("");
  const [sentTo, SetSentTo] = useState(null);
  const [dev, SetDev] = useState(null);
  const [busy, SetBusy] = useState(false);

  const reset = () => {
    SetOpen(false);
    SetPhone("");
    SetCode("");
    SetSentTo(null);
    SetDev(null);
  };
  const start = (number) => {
    SetPhone(number || "");
    SetOpen(true);
  };
  const send = async () => {
    if (!phone.trim() || busy) return notify(t("forgot.needMobile"));
    SetBusy(true);
    try {
      const res = await requestPhoneCode(phone);
      SetSentTo(res.phone);
      SetDev(res.dev_code ? { code: res.dev_code } : null); // development server only
    } catch (err) {
      notify(translateError(err));
    } finally {
      SetBusy(false);
    }
  };
  const verify = async () => {
    if (!/^\d{6}$/.test(code.trim())) return notify(t("forgot.needCode"));
    if (busy) return;
    SetBusy(true);
    try {
      onChanged(await confirmPhoneCode(code));
      notify(t("profile.phoneUpdated"));
      reset();
    } catch (err) {
      notify(translateError(err));
    } finally {
      SetBusy(false);
    }
  };

  return (
    <section className="phone-section">
      <div className="phone-row">
        <div>
          <small>{t("auth.mobile")}</small>
          <b dir="ltr">{profile.phone || t("profile.noPhone")}</b>
        </div>
        {profile.phone &&
          (profile.phone_verified ? (
            <span className="status done" data-testid="phone-status">
              <BadgeCheck /> {t("profile.phoneVerified")}
            </span>
          ) : (
            <span className="status wait" data-testid="phone-status">
              <TriangleAlert /> {t("profile.phoneUnverified")}
            </span>
          ))}
      </div>
      {!open && (
        <div className="actions">
          {profile.phone && !profile.phone_verified && (
            <Btn type="button" kind="outline" onClick={() => start(profile.phone)}>
              {t("profile.verifyNumber")}
            </Btn>
          )}
          <Btn type="button" kind="outline" onClick={() => start("")}>
            {profile.phone ? t("profile.changePhone") : t("profile.addPhone")}
          </Btn>
        </div>
      )}
      {open && !sentTo && (
        <div className="phone-edit">
          <Field
            label={t("profile.newPhone")}
            placeholder={t("auth.mobilePh")}
            value={phone}
            onChange={(e) => SetPhone(e.target.value)}
            inputMode="tel"
            autoComplete="tel"
          />
          <p className="small-note">{t("profile.phoneCodeNote")}</p>
          <div className="actions">
            <Btn type="button" kind="outline" onClick={reset}>
              {t("common.close")}
            </Btn>
            <Btn type="button" onClick={send} disabled={busy}>
              {busy ? t("forgot.sending") : t("forgot.sendCode")}
            </Btn>
          </div>
        </div>
      )}
      {open && sentTo && (
        <div className="phone-edit">
          <p>{t("profile.codeSentTo", { phone: sentTo })}</p>
          {dev && <DevSmsNotice code={dev.code} />}
          <Field
            label={t("forgot.code")}
            value={code}
            onChange={(e) => SetCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
          />
          <div className="actions">
            <Btn type="button" kind="outline" onClick={reset}>
              {t("common.close")}
            </Btn>
            <Btn type="button" kind="outline" onClick={send} disabled={busy}>
              {t("forgot.resend")}
            </Btn>
            <Btn type="button" onClick={verify} disabled={busy}>
              {busy ? t("forgot.saving") : t("profile.verifyAndSave")}
            </Btn>
          </div>
        </div>
      )}
    </section>
  );
}
