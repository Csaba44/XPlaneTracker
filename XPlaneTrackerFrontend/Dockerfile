########################
# BASE STAGE
########################
FROM node:25.3-alpine AS base

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

########################
# BUILD STAGE
########################
FROM base AS build
RUN npm run build

########################
# DEV STAGE
########################
FROM base AS dev
EXPOSE 5173
CMD ["npm", "run", "dev"]

########################
# PROD STAGE (nginx)
########################
FROM nginx:alpine AS prod

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
