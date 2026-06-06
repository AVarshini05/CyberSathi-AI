# Step 1: Build stage
FROM node:20-alpine AS builder

WORKDIR /frontend

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# Step 2: Serve stage
FROM nginx:alpine

COPY --from=builder /frontend/dist /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
