/**
 * Cloudflare Email Worker — PresupuestoPRO
 * Agregado 25/07/2026, paso 1 del CRM unificado (ver PROYECTO.md en
 * RETENCION_USUARIOS).
 *
 * Qué hace, en orden:
 *   1. Reenvía el mail a Gmail tal cual lo hacía la regla de Email Routing
 *      hasta ahora (contacto@presupuestopro.com.ar -> presupuestopro.app@gmail.com).
 *      Esto NO cambia — nada se pierde de lo que ya funciona.
 *   2. Parsea el mail (remitente, asunto, texto) con postal-mime.
 *   3. Manda ese contenido por POST a la app (routes/email_bot.py), para que
 *      la respuesta también aparezca en Admin > Email, cruzada con el
 *      usuario si el remitente coincide con un email de la base.
 *
 * Variables necesarias (Worker > Settings > Variables and Secrets):
 *   EMAIL_WEBHOOK_SECRET (secreto) → tiene que ser EXACTAMENTE el mismo
 *     valor que la variable de entorno EMAIL_WEBHOOK_SECRET en Railway.
 *   RAILWAY_APP_URL (variable normal, opcional) → si no se carga, usa el
 *     valor por default de abajo (la URL actual de producción).
 */
import PostalMime from 'postal-mime';

const GMAIL_DESTINO = 'presupuestopro.app@gmail.com';
const RAILWAY_URL_DEFAULT = 'https://web-production-0c9c1.up.railway.app';

export default {
  async email(message, env, ctx) {
    // 1) Reenviar a Gmail — igual que la regla de Email Routing anterior.
    try {
      await message.forward(GMAIL_DESTINO);
    } catch (err) {
      console.error('Error reenviando a Gmail:', err);
    }

    // 2) Parsear el mail.
    let parsed;
    try {
      const rawEmail = await new Response(message.raw).arrayBuffer();
      parsed = await PostalMime.parse(rawEmail);
    } catch (err) {
      console.error('Error parseando el mail:', err);
      return;
    }

    // 3) Mandar el contenido a la app.
    const railwayUrl = (env.RAILWAY_APP_URL || RAILWAY_URL_DEFAULT).replace(/\/$/, '');
    const payload = {
      from: message.from,
      subject: parsed.subject || '',
      text: parsed.text || parsed.html || '',
    };

    try {
      const resp = await fetch(`${railwayUrl}/webhook/email`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Webhook-Secret': env.EMAIL_WEBHOOK_SECRET || '',
        },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        console.error('El webhook de la app devolvió', resp.status, await resp.text());
      }
    } catch (err) {
      console.error('Error mandando el mail a la app:', err);
    }
  },
};
