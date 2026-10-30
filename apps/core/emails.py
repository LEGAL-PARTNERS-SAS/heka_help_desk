"""
apps/core/emails.py — plantilla HTML compartida ("Marfil Minimal
premium", ver memoria project_correos_heka_rediseno) para TODOS los
correos de este proyecto Django, y el envío real por Django con el
logo embebido.

Antes cada app armaba su propio correo (tickets en HTML con el diseño
nuevo, el código de MFA en texto plano sin ningún diseño) — esto saca
el shell y el envío a un solo lugar para que agregar un correo nuevo en
cualquier app de este proyecto (users, tickets, el que sea) no implique
copiar la plantilla de nuevo.
"""
import html as _html
import logging
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

LOGO_PATH = str(settings.BASE_DIR / 'static' / 'img' / 'logo_heka.png')

TEMAS = {
    'azul':  {'accent': '1c6ea8', 'accent2': '298ece', 'tint': 'e8f3fb'},
    'verde': {'accent': '2e8b57', 'accent2': '3aa06a', 'tint': 'e9f6ee'},
    'rojo':  {'accent': 'd1495b', 'accent2': 'a73a49', 'tint': 'fbeaec'},
}


def render_shell(eyebrow: str, titulo: str, intro_html: str, detalle: list = None,
                  cta_label: str = None, cta_url: str = None, app_nombre: str = 'Heka',
                  accent: str = '1c6ea8', accent2: str = '298ece', tint: str = 'e8f3fb') -> str:
    """Tarjeta blanca de 620px, logo real de HEKA, franja de acento en
    degradado, botón en contorno. titulo/eyebrow se escapan porque suelen
    traer texto libre (título de ticket, nombre de usuario). intro_html NO
    se escapa a propósito, el llamador decide si necesita <strong>, etc. y
    escapa lo variable él mismo antes de armar ese fragmento."""
    titulo_seguro  = _html.escape(titulo)
    eyebrow_seguro = _html.escape(eyebrow)
    detalle = detalle or []

    campos_html = ''
    for i, (k, v) in enumerate(detalle):
        divisor = '' if i == 0 else '<div style="height:1px;background:rgba(0,0,0,.06);margin:14px 0;"></div>'
        campos_html += (
            divisor
            + f'<p style="margin:0 0 4px;font-size:10.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#{accent};">{_html.escape(str(k))}</p>'
            + f'<p style="margin:0;font-size:15px;font-weight:700;color:#161a1f;">{_html.escape(str(v))}</p>'
        )
    detalle_html = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#{tint};border-radius:14px;margin:0 0 28px;">
  <tr><td style="padding:24px 26px;">{campos_html}</td></tr>
</table>""" if detalle else ''

    cta_html = f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:4px 0 8px;">
    <a href="{cta_url}" class="cta-btn" style="display:inline-block;background:transparent;color:#{accent};
       border:2px solid #{accent};text-decoration:none;font-size:14.5px;font-weight:700;letter-spacing:.02em;
       padding:14px 44px;border-radius:999px;">{_html.escape(cta_label)}</a>
    </td></tr></table>""" if (cta_label and cta_url) else ''

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titulo_seguro}</title>
<style>.cta-btn:hover{{background:#{accent} !important;color:#ffffff !important;box-shadow:0 14px 28px rgba(0,0,0,.16);}}</style>
</head>
<body style="margin:0;padding:0;background:linear-gradient(180deg,#f7fafc,#eef2f5);font-family:Arial,Helvetica,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(180deg,#f7fafc,#eef2f5);padding:44px 16px;">
<tr><td align="center">
<table role="presentation" width="620" cellpadding="0" cellspacing="0" style="width:620px;max-width:100%;background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 26px 60px rgba(20,78,120,.14),0 2px 10px rgba(15,23,32,.05);">
  <tr><td style="height:3px;line-height:3px;font-size:0;background:linear-gradient(90deg,#{accent2},#{accent} 60%,#0f2438);">&nbsp;</td></tr>
  <tr>
    <td style="padding:40px 48px 8px;text-align:center;">
      <img src="cid:hekalogo" width="60" alt="HEKA" style="display:block;margin:0 auto;border:0;">
      <div style="font-family:Arial,Helvetica,sans-serif;font-size:10.5px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#{accent};margin-top:14px;">{_html.escape(app_nombre)}</div>
      <div style="width:120px;height:1px;background:linear-gradient(90deg,rgba(0,0,0,0),rgba(0,0,0,.14),rgba(0,0,0,0));margin:20px auto 0;"></div>
    </td>
  </tr>
  <tr>
    <td style="padding:24px 48px 44px;">
      <p style="margin:0 0 8px;font-size:11px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#{accent};">{eyebrow_seguro}</p>
      <h1 style="margin:0 0 16px;font-family:Georgia,'Times New Roman',serif;font-size:26px;font-weight:700;color:#161a1f;letter-spacing:-0.01em;">{titulo_seguro}</h1>
      <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#4a5257;">{intro_html}</p>
      {detalle_html}
      {cta_html}
    </td>
  </tr>
  <tr>
    <td style="background:#{tint};padding:26px 48px 28px;text-align:center;">
      <div style="width:64px;height:1px;background:linear-gradient(90deg,rgba(0,0,0,0),rgba(0,0,0,.14),rgba(0,0,0,0));margin:0 auto 16px;"></div>
      <p style="margin:0;font-size:11px;color:#8b959c;">HEKA {_html.escape(app_nombre)} &middot; Este es un correo automático, no respondas a esta dirección.</p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body></html>"""


def send_html_mail(to, subject: str, html_body: str, plain_fallback: str = '') -> bool:
    """to: string o lista de correos. Nunca lanza: devuelve False y deja
    log si algo falla, un correo que no sale no debe tumbar el flujo que
    lo dispara (login, notificación de ticket, etc.)."""
    to_list = [to] if isinstance(to, str) else list(to)
    if not to_list:
        return False
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_fallback or ' ',
            from_email=settings.EMAIL_HOST_USER,
            to=to_list,
        )
        msg.mixed_subtype = 'related'
        msg.attach_alternative(html_body, 'text/html')
        try:
            with open(LOGO_PATH, 'rb') as f:
                img = MIMEImage(f.read())
            img.add_header('Content-ID', '<hekalogo>')
            img.add_header('Content-Disposition', 'inline', filename='logo_heka.png')
            msg.attach(img)
        except OSError as e:
            logger.warning('No se pudo adjuntar el logo al correo: %s', e)
        msg.send(fail_silently=False)
        logger.info('[EMAIL] Enviado a %d destinatario(s) — %s', len(to_list), subject)
        return True
    except Exception as e:
        logger.error('[EMAIL ERROR] %s', e)
        return False
