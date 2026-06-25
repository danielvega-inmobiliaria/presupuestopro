# Guía de deploy — PresupuestoPRO en Hetzner VPS

## 1. Contratar el servidor

1. Ir a https://www.hetzner.com/cloud
2. Crear cuenta / iniciar sesión
3. Click **"Add Server"**:
   - Location: Nuremberg o Helsinki (lo más cercano a vos)
   - Image: **Ubuntu 22.04**
   - Type: **CX11** (~€3.29/mes, 1 vCPU, 2 GB RAM, 20 GB SSD)
   - SSH Key: pegá tu clave pública (ver paso 2)
   - Name: `presupuestopro`
4. Click **Create & Buy now** → te muestra la **IP del servidor**

---

## 2. Generar clave SSH (en tu PC, solo una vez)

```bash
ssh-keygen -t ed25519 -C "presupuestopro"
# Presioná Enter a todo (sin passphrase está bien)
cat ~/.ssh/id_ed25519.pub
# Copiá todo el output y pegalo en Hetzner al crear el servidor
```

---

## 3. Conectarse al servidor

```bash
ssh root@TU_IP_AQUI
```

La primera vez te pregunta si confiar en el host → escribí `yes`.

---

## 4. Configuración inicial del servidor

```bash
# Actualizar sistema
apt update && apt upgrade -y

# Instalar dependencias
apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# Crear usuario no-root (opcional pero recomendado)
adduser presup
usermod -aG sudo presup
```

---

## 5. Subir el código

**Opción A — desde tu PC con scp:**
```bash
# Desde tu PC (no desde el servidor)
scp -r "D:\ESCRITORIO\CLAUDE\APP_PRESUPUESTOPRO" root@TU_IP:/var/www/presupuestopro
```

**Opción B — clonar desde GitHub:**
```bash
# En el servidor
mkdir /var/www/presupuestopro
# (subí el código a GitHub primero)
git clone https://github.com/TU_USUARIO/presupuestopro.git /var/www/presupuestopro
```

---

## 6. Instalar dependencias Python

```bash
cd /var/www/presupuestopro

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar paquetes
pip install -r requirements.txt
pip install gunicorn
```

---

## 7. Inicializar la base de datos

```bash
cd /var/www/presupuestopro
source venv/bin/activate

python3 -c "
from app import create_app
from database import init_db
app = create_app()
with app.app_context():
    init_db()
print('Base de datos creada OK')
"
```

Esto crea `presupuestopro.db` con el admin y los datos semilla.

---

## 8. Crear archivo de variables de entorno

```bash
nano /var/www/presupuestopro/.env
```

Contenido del archivo:
```
SECRET_KEY=cambia_esto_por_algo_largo_y_random_ej_xk29mz7q
```

Para generar una clave segura:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 9. Configurar Gunicorn como servicio

```bash
nano /etc/systemd/system/presupuestopro.service
```

Contenido:
```ini
[Unit]
Description=PresupuestoPRO Flask App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/presupuestopro
Environment="PATH=/var/www/presupuestopro/venv/bin"
EnvironmentFile=/var/www/presupuestopro/.env
ExecStart=/var/www/presupuestopro/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8000 \
    "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar el servicio:
```bash
chown -R www-data:www-data /var/www/presupuestopro
systemctl daemon-reload
systemctl enable presupuestopro
systemctl start presupuestopro
systemctl status presupuestopro   # debe decir "active (running)"
```

---

## 10. Configurar Nginx como proxy

```bash
nano /etc/nginx/sites-available/presupuestopro
```

Contenido (reemplazá `tudominio.com`):
```nginx
server {
    listen 80;
    server_name tudominio.com www.tudominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/presupuestopro/static/;
        expires 7d;
    }
}
```

Activar y probar:
```bash
ln -s /etc/nginx/sites-available/presupuestopro /etc/nginx/sites-enabled/
nginx -t                    # debe decir "syntax is ok"
systemctl restart nginx
```

---

## 11. Configurar dominio

En el panel de tu registrador de dominio (NIC.ar, GoDaddy, etc.):
- Crear un registro **A** apuntando a la IP de Hetzner
- Nombre: `@` (o `www`)
- Valor: `TU_IP`
- TTL: 3600

Esperá ~10 minutos a que se propague.

---

## 12. Activar HTTPS con Let's Encrypt (gratis)

```bash
certbot --nginx -d tudominio.com -d www.tudominio.com
# Seguí las instrucciones → ingresá email, aceptá términos
# Elegí opción 2: redirigir todo a HTTPS
```

Certbot renueva el certificado automáticamente. Verificá:
```bash
systemctl status certbot.timer
```

---

## 13. Verificación final

Abrí `https://tudominio.com` en el navegador.

- Login: `admin@presupuestopro.com` / `admin1234`
- **Cambiá la contraseña del admin inmediatamente** desde el panel.

---

## 14. Comandos útiles post-deploy

```bash
# Ver logs de la app
journalctl -u presupuestopro -f

# Reiniciar la app (tras actualizar código)
systemctl restart presupuestopro

# Actualizar código (si usás Git)
cd /var/www/presupuestopro
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart presupuestopro

# Backup de la base de datos
cp /var/www/presupuestopro/presupuestopro.db /root/backup_$(date +%Y%m%d).db
```

---

## Resumen de costos

| Concepto | Costo |
|----------|-------|
| Hetzner CX11 | ~€3.29/mes |
| Dominio (.com) | ~$10/año |
| SSL (Let's Encrypt) | Gratis |
| **Total** | **~€4/mes** |
