// Doctor home: only the patients and appointments assigned to this doctor.
import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import LanguageSwitcher from "../../components/LanguageSwitcher.jsx";
import { CalendarDays, CheckCircle2, Clock3, LogOut, Users } from "lucide-react";
import { Brand, Stat, initials, pad2, timeOnly } from "../../components/ui.jsx";
import QueuePanel from "../staff/QueuePanel.jsx";
import { doctorDashboard, listAppointments } from "../../services/visits.js";

const UPCOMING_DAYS = 14;
const dateShort = (iso) =>
  iso ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" }) : "";

export default function DoctorHome({ go, notify, userName, onLogout, onOpen, onLanguage }) {
  const { t } = useTranslation();
  const [dash, SetDash] = useState(null);
  const [appts, SetAppts] = useState(null);
  useEffect(() => {
    doctorDashboard().then(SetDash).catch((err) => notify(err.message));
    // Today and the next 13 days, so a booking for tomorrow is visible today.
    listAppointments({ days: UPCOMING_DAYS }).then(SetAppts).catch(() => SetAppts([]));
  }, []);
  const q = dash ? dash.my_queue : null;
  return (
    <div className="staff-layout">
      <aside className="staff-sidebar">
        <Brand go={go} />
        <LanguageSwitcher onChange={onLanguage} className="language" />
        <div className="staff-user">
          <div className="avatar">{initials(userName)}</div>
          <div>
            <b>{userName}</b>
            <small>{t("doctor.role")}</small>
          </div>
          <button onClick={onLogout} title={t("common.logout")} aria-label={t("common.logout")}>
            <LogOut />
          </button>
        </div>
      </aside>
      <main className="staff-main">
        <header className="dash-head">
          <div>
            <span className="eyebrow">{t("doctor.eyebrow")}</span>
            <h2>{t("doctor.hello", { name: userName })}</h2>
            <p>{t("doctor.assignedToday")}</p>
          </div>
        </header>
        <div className="stats">
          <Stat icon={<Users />} label={t("doctor.waiting")} value={q ? pad2(q.waiting + q.checked_in) : "--"} />
          <Stat icon={<Clock3 />} label={t("doctor.withYou")} value={q ? pad2(q.in_consultation) : "--"} />
          <Stat icon={<CheckCircle2 />} label={t("doctor.completed")} value={q ? pad2(q.completed) : "--"} />
          <Stat icon={<CalendarDays />} label={t("doctor.appointments")} value={dash ? pad2(dash.my_appointments_today) : "--"} />
        </div>
        <QueuePanel
          eyebrow={t("doctor.myPatients")}
          title={t("doctor.assignedTitle")}
          emptyText={t("doctor.noneAssigned")}
          onOpen={onOpen}
          notify={notify}
          urgentFirst
        />
        <section className="queue">
          <div className="section-title">
            <div>
              <span className="eyebrow">{t("doctor.apptEyebrow")}</span>
              <h3>{t("doctor.apptTitle")}</h3>
            </div>
          </div>
          {appts === null && <p className="empty">{t("common.loading")}</p>}
          {appts && !appts.length && <p className="empty">{t("doctor.noAppts")}</p>}
          {(appts || []).map((a) => (
            <p key={a.id}>
              <b>{dateShort(a.starts_at)}, {timeOnly(a.starts_at)}</b> · {a.patient.name} · {a.department}
              {a.room ? ` · ${a.room}` : ""} · {a.status}
            </p>
          ))}
        </section>
      </main>
    </div>
  );
}
