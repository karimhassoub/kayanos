# ==========================================
# Stage 1: Build the Vue/Vite Frontend
# ==========================================
FROM node:18-alpine AS frontend-builder
WORKDIR /app

# Copy the entire app so relative paths in vite.config.ts work
COPY . .

# Build the frontend which will output to kayanos/public/frontend
WORKDIR /app/frontend
RUN npm install
RUN npm run build


# ==========================================
# Stage 2: Backend (Frappe Worker)
# ==========================================
FROM frappe/frappe-worker:version-16 AS backend

USER root
# Install git and any other OS dependencies if needed
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

USER frappe

# Copy the frontend build output and the python app code
COPY --from=frontend-builder --chown=frappe:frappe /app /home/frappe/frappe-bench/apps/kayanos

# Install the app into the bench
RUN bench get-app kayanos /home/frappe/frappe-bench/apps/kayanos


# ==========================================
# Stage 3: Frontend (Frappe Nginx)
# ==========================================
FROM frappe/frappe-nginx:version-16 AS frontend

USER root

# Copy apps.txt to let frappe know about the installed apps
COPY --from=backend --chown=frappe:frappe /home/frappe/frappe-bench/sites/apps.txt /var/www/html/sites/apps.txt

# Copy the app's public assets (which includes the built vite frontend)
# to the nginx html directory
COPY --from=backend --chown=frappe:frappe /home/frappe/frappe-bench/apps/kayanos/kayanos/public /var/www/html/assets/kayanos

USER frappe
