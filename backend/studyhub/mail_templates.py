"""The e-mails Nexus sends. Table layout with inline styles (works in Outlook, Gmail and phones), a plain-text twin for every
message, and every dynamic value escaped."""
from __future__ import annotations

from html import escape as e

BLUE, BLUE_DARK, PALE, INK, MUTED = "#1561AD", "#0F4A86", "#EAF6FD", "#0B1F3A", "#5A6F8E"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


def layout(preheader: str, heading: str, body: str, footer: str = "") -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">
<title>{e(heading)}</title></head>
<body style="margin:0;padding:0;background:{PALE};font-family:{FONT};color:{INK};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:{PALE};">{e(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PALE};padding:24px 12px;"><tr><td align="center">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #BAE2F7;">
    <tr><td style="background:{BLUE};padding:20px 28px;"><span style="font-size:22px;font-weight:800;letter-spacing:-0.3px;color:#ffffff;">Nexus</span>
      <span style="font-size:13px;color:#BAE2F7;margin-left:10px;">Learn &middot; Practice &middot; Progress</span></td></tr>
    <tr><td style="padding:32px 28px 8px 28px;"><h1 style="margin:0 0 12px 0;font-size:22px;line-height:1.3;color:{INK};">{e(heading)}</h1></td></tr>
    <tr><td style="padding:0 28px 28px 28px;font-size:15px;line-height:1.6;color:{INK};">{body}</td></tr>
    <tr><td style="background:#F4FAFE;border-top:1px solid #BAE2F7;padding:18px 28px;font-size:12px;line-height:1.6;color:{MUTED};">
      {footer}<p style="margin:0;">This is an automated message from Nexus. Please do not reply to it.</p></td></tr>
  </table>
</td></tr></table></body></html>"""


def _code_box(code: str) -> str:
    spaced = " ".join(code)
    return (f'<table role="presentation" align="center" cellpadding="0" cellspacing="0" style="margin:20px auto;"><tr>'
            f'<td style="background:{PALE};border:2px dashed {BLUE};border-radius:10px;padding:16px 28px;font-family:Consolas,Menlo,monospace;'
            f'font-size:34px;font-weight:700;letter-spacing:6px;color:{BLUE_DARK};text-align:center;">{e(spaced)}</td></tr></table>')


def _security(items: list[str]) -> str:
    lis = "".join(f'<li style="margin:0 0 6px 0;">{e(i)}</li>' for i in items)
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px;"><tr><td style="background:#FFF3D6;border-left:4px solid #B7791F;'
            f'border-radius:6px;padding:14px 16px;font-size:13px;line-height:1.55;color:#5B3A00;"><b>Keep your account safe</b>'
            f'<ul style="margin:8px 0 0 18px;padding:0;">{lis}</ul></td></tr></table>')


def _details(rows: list[tuple[str, str]]) -> str:
    trs = "".join(f'<tr><td style="padding:3px 12px 3px 0;color:{MUTED};font-size:13px;">{e(k)}</td><td style="padding:3px 0;font-size:13px;">{e(v)}</td></tr>' for k, v in rows)
    return f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:14px;">{trs}</table>'


def otp_email(purpose: str, code: str, minutes: int, when: str, ip_hint: str) -> tuple[str, str, str]:
    reset = purpose == "reset"
    subject = "Your Nexus password reset code" if reset else "Verify your email address for Nexus"
    intro = ("We received a request to reset the password of your Nexus account. Enter this code on the reset page to choose a new password."
             if reset else "Enter this code in Nexus to confirm that this email address is yours.")
    tips = ["Nexus will never ask you for this code by phone, chat or email.", "Do not share it with anyone, including anyone claiming to be from Nexus.",
            "If you did not make this request, ignore this email. Your password stays unchanged."]
    body = (f'<p style="margin:0 0 4px 0;">{e(intro)}</p>{_code_box(code)}'
            f'<p style="margin:0;text-align:center;color:{MUTED};font-size:13px;">The code expires in <b>{minutes} minutes</b> and works once.</p>'
            f'{_details([("Requested", when), ("From network", ip_hint)])}<div style="height:16px;"></div>{_security(tips)}')
    text = (f"{intro}\n\nYour code: {code}\n\nIt expires in {minutes} minutes and works once.\nRequested: {when} from {ip_hint}\n\n"
            + "\n".join(f"- {t}" for t in tips) + "\n\nNexus")
    return subject, text, layout(f"Your code is {code}. It expires in {minutes} minutes.", subject, body)


def password_changed_email(when: str, ip_hint: str) -> tuple[str, str, str]:
    subject = "Your Nexus password was changed"
    tips = ["Every device was signed out.", "If this was not you, reset your password again straight away and check your email account's security."]
    body = (f'<p style="margin:0;">The password of your Nexus account was just changed.</p>{_details([("When", when), ("From network", ip_hint)])}'
            f'<div style="height:16px;"></div>{_security(tips)}')
    text = f"The password of your Nexus account was just changed.\nWhen: {when} from {ip_hint}\n\n" + "\n".join(f"- {t}" for t in tips) + "\n\nNexus"
    return subject, text, layout("Your password was changed.", subject, body)


def _stat(label: str, value: str) -> str:
    return (f'<td align="center" style="padding:12px 6px;background:{PALE};border-radius:8px;"><div style="font-size:24px;font-weight:800;color:{BLUE_DARK};">{e(value)}</div>'
            f'<div style="font-size:12px;color:{MUTED};">{e(label)}</div></td>')


def digest_email(name: str, d: dict, url: str) -> tuple[str, str, str]:
    subject = "Your Nexus week: " + (f"{d['answers']} answers, {d['streak']}-day streak" if d["answers"] else "a quick summary")
    stats = ('<table role="presentation" width="100%" cellpadding="0" cellspacing="6"><tr>'
             + _stat("quiz answers", str(d["answers"])) + _stat("correct", f"{d['accuracy']}%" if d["answers"] else "–")
             + _stat("questions asked", str(d["asked"])) + _stat("day streak", str(d["streak"])) + "</tr></table>")
    subjects = "".join(
        f'<tr><td style="padding:6px 0;border-bottom:1px solid #E3EEF8;">{e(s["name"])}</td><td align="right" style="padding:6px 0;border-bottom:1px solid #E3EEF8;font-weight:700;">'
        f'{"–" if s["confidence"] is None else str(round(s["confidence"] * 100)) + "%"}</td></tr>' for s in d["subjects"])
    weak = "".join(f'<li style="margin:0 0 4px 0;">{e(w["name"])} <span style="color:{MUTED};">({e(w["subject"])}, {round(w["confidence"] * 100)}% confidence)</span></li>' for w in d["weak"])
    due = f'<p style="margin:14px 0 0 0;">You have <b>{d["due_cards"]}</b> flashcard{"s" if d["due_cards"] != 1 else ""} due for review.</p>' if d["due_cards"] else ""
    body = (f'<p style="margin:0 0 14px 0;">Hi {e(name)}, here is how your week went.</p>{stats}'
            + (f'<h2 style="font-size:16px;margin:22px 0 6px 0;">Confidence by subject</h2><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:14px;">{subjects}</table>' if subjects else "")
            + (f'<h2 style="font-size:16px;margin:22px 0 6px 0;">Worth another look</h2><ul style="margin:0 0 0 18px;padding:0;font-size:14px;">{weak}</ul>' if weak else "")
            + due
            + f'<p style="margin:24px 0 0 0;"><a href="{e(url)}/dashboard" style="display:inline-block;background:{BLUE};color:#ffffff;text-decoration:none;font-weight:700;padding:12px 22px;border-radius:8px;">Open Nexus</a></p>')
    footer = f'<p style="margin:0 0 8px 0;">You get this summary because you turned on the weekly email. Turn it off any time in Account &rarr; Email.</p>'
    text = (f"Hi {name}, here is how your week went.\n\nQuiz answers: {d['answers']}" + (f" ({d['accuracy']}% correct)" if d["answers"] else "")
            + f"\nQuestions asked: {d['asked']}\nDay streak: {d['streak']}\n"
            + ("\nConfidence by subject:\n" + "\n".join(f"- {s['name']}: {'-' if s['confidence'] is None else str(round(s['confidence'] * 100)) + '%'}" for s in d["subjects"]) + "\n" if d["subjects"] else "")
            + ("\nWorth another look:\n" + "\n".join(f"- {w['name']} ({w['subject']})" for w in d["weak"]) + "\n" if d["weak"] else "")
            + (f"\nFlashcards due: {d['due_cards']}\n" if d["due_cards"] else "") + f"\nOpen Nexus: {url}/dashboard\nTurn this email off in Account > Email.\n")
    return subject, text, layout("Your weekly Nexus summary.", "Your week in Nexus", body, footer)
