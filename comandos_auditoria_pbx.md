# Comandos de Auditoría y Seguridad PBX (Issabel/Asterisk)

Esta es tu "chuleta" (cheatsheet) para demostrar cómo auditaste el servidor y detuviste el ataque. Guárdala en un bloc de notas.

## 1. Conexión al Servidor
```bash
ssh root@190.145.227.29
# Te pedirá la contraseña del servidor PBX
```

---

## 2. Buscar intentos de Hackeo (Fuerza Bruta) en tiempo real
Para ver quién está intentando adivinar las contraseñas de las extensiones, leemos el log principal de Asterisk filtrando por "Wrong password".

**Comando:**
```bash
grep "Wrong password" /var/log/asterisk/full | tail -n 20
```

**Respuesta esperada:**
Verás líneas indicando qué IP intentó entrar y falló.
> `[2026-09-06 19:12:23] NOTICE[49087] chan_sip.c: Registration from '<sip:3619@190.145.227.29>' failed for '45.61.184.74:54724' - Wrong password`

**Explicación para Néstor:** "Revisé el log de Asterisk (`/var/log/asterisk/full`) y me di cuenta de que teníamos miles de peticiones por segundo desde IPs extranjeras intentando registrar extensiones con claves incorrectas."

---

## 3. Ver las llamadas fraudulentas que lograron sacar
Si el hacker logró entrar, el PBX guardará la grabación de la llamada en la carpeta de monitoreo. Para ver las llamadas de un día específico (ej. 6 de septiembre de 2026), buscamos los archivos de audio de salida (`out-*.wav`).

**Comando:**
```bash
ls -l /var/spool/asterisk/monitor/2026/09/06/ | grep "out-" | wc -l
```

**Respuesta esperada:**
Un número entero, por ejemplo:
> `3780`

**Explicación para Néstor:** "Fui al directorio de spooling del PBX y conté cuántos archivos de grabación de salida (outbound) se generaron. El sábado sacaron más de 1.500 llamadas y hoy iban por las 3.700."

---

## 4. Bloquear una IP atacante en el Firewall (La Solución Inmediata)
Una vez identificas la IP del atacante (ej. `190.60.123.171`), le bloqueas la entrada de red directamente desde el sistema operativo (Linux) usando `iptables`.

**Comando:**
```bash
iptables -I INPUT -s 190.60.123.171 -j DROP
```

**Respuesta esperada:**
Ninguna (si el comando es exitoso, no arroja texto, simplemente aplica la regla de inmediato).

**Explicación para Néstor:** "Al ver el ataque crítico, tomé acción de contención inmediata. Inyecté una regla DROP en la cadena INPUT de iptables para aislar la IP origen del atacante, cerrándole el paso a nivel de sistema operativo para que ni siquiera llegara al puerto 5060 de Asterisk."

---

## 5. Verificar que el atacante quedó bloqueado
Para comprobar que el bloqueo está activo y ver si la IP sigue intentando atacar (los paquetes se van sumando en la columna de bloqueados).

**Comando:**
```bash
iptables -L INPUT -n -v | grep DROP
```

**Respuesta esperada:**
Verás la lista de IPs bloqueadas y cuántos paquetes han sido rechazados.
> `145K  8700K DROP  all  --  *  *  190.60.123.171   0.0.0.0/0`

**Explicación para Néstor:** "Confirmé la mitigación revisando la tabla de ruteo; el firewall de Linux estaba dropeando cientos de miles de paquetes de esa IP, confirmando que cortamos el ataque de raíz."
