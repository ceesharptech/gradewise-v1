"""
notifications.py  —  Gmail SMTP email alerts
"""
import smtplib, threading
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from datetime             import datetime


# ─────────────────────────────────────────────────────────────
# SEND HELPER  (runs in a background thread so it never
#               blocks the HTTP response)
# ─────────────────────────────────────────────────────────────
def _send(cfg: dict, subject: str, html: str, plain: str) -> tuple[bool, str]:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = cfg["sender_email"]
        msg["To"]      = cfg["recipient_email"]
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        with smtplib.SMTP(cfg["smtp_server"], int(cfg["smtp_port"])) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["sender_email"], cfg["sender_password"])
            server.sendmail(cfg["sender_email"], cfg["recipient_email"], msg.as_string())
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)


def _async_send(cfg, subject, html, plain, callback=None):
    def run():
        ok, msg = _send(cfg, subject, html, plain)
        if callback:
            callback(ok, msg)
    threading.Thread(target=run, daemon=True).start()


# ─────────────────────────────────────────────────────────────
# TEST EMAIL
# ─────────────────────────────────────────────────────────────
def send_test_email(cfg: dict) -> tuple[bool, str]:
    subject = "[SPPS] Test Email — Configuration Verified"
    plain   = "This is a test email from the Student Performance Prediction System."
    html    = """
    <div style="font-family:'Segoe UI',sans-serif;max-width:560px;margin:0 auto;
                padding:32px 24px;color:#0f172a">
      <div style="background:#2563eb;border-radius:10px;padding:24px;
                  text-align:center;margin-bottom:24px">
        <h2 style="color:#fff;margin:0;font-size:18px">SPPS — Test Email</h2>
      </div>
      <p style="font-size:14px;line-height:1.6">
        Your email notification settings are configured correctly.
        You will receive alerts when at-risk students exceed your configured threshold.
      </p>
      <p style="font-size:12px;color:#94a3b8;margin-top:24px">
        Sent by the Student Performance Prediction System
      </p>
    </div>"""
    return _send(cfg, subject, html, plain)


# ─────────────────────────────────────────────────────────────
# AT-RISK ALERT
# ─────────────────────────────────────────────────────────────
def send_at_risk_alert(cfg: dict, lecturer_name: str,
                       at_risk_students: list, total_students: int,
                       source: str = "upload"):
    threshold  = cfg.get("threshold", 10)
    at_risk_n  = len(at_risk_students)

    if not cfg.get("notifications_enabled") or at_risk_n <= threshold:
        return

    subject = f"[SPPS Alert] {at_risk_n} At-Risk Student{'s' if at_risk_n != 1 else ''} Identified"

    # ── Plain text ──────────────────────────────────────
    lines = [
        f"Dear {lecturer_name},",
        "",
        f"A {'bulk upload' if source == 'upload' else 'prediction'} was processed on "
        f"{datetime.now().strftime('%d %B %Y at %H:%M')}.",
        f"{at_risk_n} student{'s have' if at_risk_n != 1 else ' has'} been flagged as at-risk "
        f"(threshold: >{threshold}).",
        "",
        "AT-RISK STUDENTS:",
    ]
    for i, s in enumerate(at_risk_students, 1):
        factors = ", ".join(s.get("risk_factors", [])) or "Multiple factors"
        lines.append(
            f"  {i}. {s['name']} ({s['student_id']}) — "
            f"Score: {s['final_score']:.2f} | Grade: {s['grade_category']} | {factors}"
        )
    lines += ["", f"Total: {at_risk_n} of {total_students} students",
              "", "— SPPS Automated Alert"]
    plain = "\n".join(lines)

    # ── HTML ────────────────────────────────────────────
    rows_html = "".join(f"""
        <tr style="border-bottom:1px solid #e2e8f0">
          <td style="padding:10px 12px;font-weight:500">{s['name']}</td>
          <td style="padding:10px 12px;color:#64748b">{s['student_id']}</td>
          <td style="padding:10px 12px;font-weight:700;color:#dc2626">{s['final_score']:.2f}</td>
          <td style="padding:10px 12px">
            <span style="background:#fee2e2;color:#dc2626;padding:2px 8px;
                         border-radius:999px;font-size:12px;font-weight:600">
              {s['grade_category']}
            </span>
          </td>
          <td style="padding:10px 12px;font-size:12px;color:#64748b">
            {", ".join(s.get("risk_factors", [])) or "—"}
          </td>
        </tr>""" for s in at_risk_students)

    html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:640px;margin:0 auto;
                padding:32px 24px;color:#0f172a">

      <div style="background:#1e3a5f;border-radius:10px;padding:24px 28px;margin-bottom:24px">
        <h2 style="color:#fff;margin:0 0 4px;font-size:18px">SPPS — At-Risk Student Alert</h2>
        <p style="color:#93c5fd;margin:0;font-size:13px">
          {datetime.now().strftime('%d %B %Y, %H:%M')}
        </p>
      </div>

      <p style="font-size:14px;line-height:1.6;margin-bottom:6px">
        Dear <strong>{lecturer_name}</strong>,
      </p>
      <p style="font-size:14px;line-height:1.6;color:#475569">
        A <strong>{'bulk upload' if source == 'upload' else 'prediction'}</strong> was processed
        and <strong style="color:#dc2626">{at_risk_n} student{'s' if at_risk_n != 1 else ''}</strong>
        {'have' if at_risk_n != 1 else 'has'} been identified as at-risk
        (threshold: &gt;{threshold} students).
      </p>

      <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;
                  padding:12px 16px;margin:20px 0;display:flex;align-items:center;gap:10px">
        <span style="font-size:20px">⚠</span>
        <span style="font-size:14px;font-weight:600;color:#dc2626">
          {at_risk_n} of {total_students} students require attention
        </span>
      </div>

      <table style="width:100%;border-collapse:collapse;font-size:13px;margin-top:16px">
        <thead>
          <tr style="background:#f8fafc;text-align:left">
            <th style="padding:10px 12px;font-weight:600;color:#64748b;
                       border-bottom:2px solid #e2e8f0">Name</th>
            <th style="padding:10px 12px;font-weight:600;color:#64748b;
                       border-bottom:2px solid #e2e8f0">ID</th>
            <th style="padding:10px 12px;font-weight:600;color:#64748b;
                       border-bottom:2px solid #e2e8f0">Score</th>
            <th style="padding:10px 12px;font-weight:600;color:#64748b;
                       border-bottom:2px solid #e2e8f0">Grade</th>
            <th style="padding:10px 12px;font-weight:600;color:#64748b;
                       border-bottom:2px solid #e2e8f0">Risk Factors</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>

      <p style="font-size:12px;color:#94a3b8;margin-top:32px;padding-top:16px;
                border-top:1px solid #e2e8f0">
        This is an automated alert from the Student Performance Prediction System.
        Log in to your dashboard to view full details and download reports.
      </p>
    </div>"""

    _async_send(cfg, subject, html, plain)