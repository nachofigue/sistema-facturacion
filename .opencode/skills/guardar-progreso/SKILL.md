---
name: guardar-progreso
description: Guarda el progreso actual haciendo commit a la rama actual, merge a main, push y vuelve a la rama original
---

## Qué hace
Realiza el flujo completo de guardado de progreso en git:

1. Obtiene la rama actual con `git branch --show-current`
2. Ejecuta `git add .`
3. Crea un commit con `git commit -m "descripción del cambio"`
4. Cambia a la rama main con `git checkout main`
5. Mergea la rama anterior a main con `git merge <rama-anterior>`
6. Pushea con `git push`
7. Vuelve a la rama original con `git checkout <rama-anterior>`

## Cuándo usarla
Úsala cuando quieras guardar el progreso actual del trabajo en una rama, integrarlo a main, subirlo al remoto y volver a tu rama de trabajo.
