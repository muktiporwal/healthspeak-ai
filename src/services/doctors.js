// Doctor verification status, the administrator's approvals, and the doctor's read-only intake view.
// The app has no doctor sign-up screen: doctor accounts are created by an administrator.
// The server decides every permission; nothing here grants access.
import { api } from "./api.js";

export const getMyVerification = () => api("/doctors/me/verification");

// ----- administrator -----
export const listDoctorApplications = (status = "") =>
  api(`/admin/doctors?limit=100${status ? `&status=${encodeURIComponent(status)}` : ""}`);
export const approveDoctor = (userId, note) =>
  api(`/admin/doctors/${userId}/approve`, { method: "POST", body: { note: note || null } });
export const rejectDoctor = (userId, note) =>
  api(`/admin/doctors/${userId}/reject`, { method: "POST", body: { note } });

// ----- verified doctor: only intakes of visits assigned to them -----
export const getDoctorIntake = (intakeId) => api(`/doctor/intakes/${intakeId}`);
export const getDoctorIntakeHistory = (intakeId, { limit = 5, offset = 0 } = {}) =>
  api(`/doctor/intakes/${intakeId}/history?limit=${limit}&offset=${offset}`);
