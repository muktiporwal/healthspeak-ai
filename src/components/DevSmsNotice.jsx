// Development-only "phone notification" showing the one-time code the server would have texted.
// It is rendered ONLY when the API returned `dev_code`, and the API does that only in development with the
// console SMS provider (backend/app/services/sms_service.py: dev_echo_allowed). In production the API never
// sends the code to the browser, so this panel can never appear. No real SMS is sent here, and the panel says so.
import React from "react";
import { useTranslation } from "react-i18next";
import { MessageSquareText } from "lucide-react";

export default function DevSmsNotice({ code }) {
  const { t } = useTranslation();
  if (!code) return null;
  return (
    <div className="sms-demo" role="status" data-testid="dev-otp">
      <div className="sms-demo-top">
        <span className="sms-demo-app">
          <MessageSquareText aria-hidden="true" /> {t("forgot.devApp")}
        </span>
        <span className="sms-demo-badge">{t("forgot.devBadge")}</span>
      </div>
      <p className="sms-demo-msg">{t("forgot.devMessage")}</p>
      <code className="sms-demo-code" dir="ltr">
        {code}
      </code>
      <small className="sms-demo-note">{t("forgot.devNoSms")}</small>
    </div>
  );
}
