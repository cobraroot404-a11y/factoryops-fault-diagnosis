FROM node:20-alpine AS build
WORKDIR /srv
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /srv/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
