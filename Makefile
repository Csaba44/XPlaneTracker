# -------------------------
# CONFIG
# -------------------------
COMPOSE_DEV=docker-compose.dev.yml
COMPOSE_PROD=docker-compose.prod.yml

VERSION ?= latest

DOCKER_USER=csabi44

BACKEND_IMAGE=$(DOCKER_USER)/xtracker-backend
FRONTEND_IMAGE=$(DOCKER_USER)/xtracker-frontend
WEBSOCKET_IMAGE=$(DOCKER_USER)/xtracker-websocket

# -------------------------
# HELP
# -------------------------
.PHONY: help
help:
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "DEV:"
	@echo "  make dev-key        Generate Laravel APP_KEY (dev)"
	@echo "  make dev-up         Start dev stack (foreground)"
	@echo "  make dev-up-d       Start dev stack (detached)"
	@echo "  make dev-down       Stop dev stack"
	@echo "  make dev-down-v     Stop dev stack and REMOVE volumes (DB reset)"
	@echo ""
	@echo "MIGRATE (DEV):"
	@echo "  make migrate             Run migrations"
	@echo "  make migrate-seed        Run migrations + seed"
	@echo "  make migrate-fresh       Drop all tables and re-run migrations"
	@echo "  make migrate-fresh-seed  Drop all tables, re-run migrations + seed"
	@echo ""
	@echo "BUILD:"
	@echo "  make build                  Build prod images (:latest)"
	@echo "  make build VERSION=x.y.z    Build and tag images with version"
	@echo ""
	@echo "PUBLISH:"
	@echo "  make push                   Push images to Docker Hub"
	@echo "  make release VERSION=x.y.z  Build + push images"
	@echo ""
	@echo "PROD:"
	@echo "  make prod-up        Start prod stack (foreground)"
	@echo "  make prod-up-d      Start prod stack (detached)"
	@echo "  make prod-down      Stop prod stack"
	@echo "  make prod-down-v    Stop prod stack and REMOVE volumes (DB reset)"
	@echo "  make prod-db-seed   Seed production database (USE ONLY ONCE)"
	@echo "  make prod-pull      Pull latest images for prod stack"
	@echo ""
	@echo "UTILS:"
	@echo "  make logs           Tail prod logs"
	@echo "  make ps             Show running containers"
	@echo "  make prettier             Run prettier formatting on frontend and websocket codebase"
	@echo ""

# -------------------------
# DEV
# -------------------------
.PHONY: dev-key
dev-key:
	@echo "Generating Laravel APP_KEY (DEV)..."
	docker compose -f $(COMPOSE_DEV) run --rm artisan key:generate --show

.PHONY: dev-up
dev-up:
	docker compose -f $(COMPOSE_DEV) up --build

.PHONY: dev-up-d
dev-up-d:
	docker compose -f $(COMPOSE_DEV) up -d

.PHONY: dev-down
dev-down:
	docker compose -f $(COMPOSE_DEV) down

.PHONY: dev-down-v
dev-down-v:
	docker compose -f $(COMPOSE_DEV) down -v

# -------------------------
# MIGRATE (DEV)
# -------------------------
.PHONY: migrate
migrate:
	./artisan migrate

.PHONY: migrate-seed
migrate-seed:
	./artisan migrate --seed

.PHONY: migrate-fresh
migrate-fresh:
	./artisan migrate:fresh

.PHONY: migrate-fresh-seed
migrate-fresh-seed:
	./artisan migrate:fresh --seed

# -------------------------
# BUILD (PROD IMAGES)
# -------------------------
.PHONY: build
build:
	@echo "Building BACKEND image ($(VERSION))..."
	docker build -t $(BACKEND_IMAGE):$(VERSION) ./XPlaneTrackerAPI
	docker tag $(BACKEND_IMAGE):$(VERSION) $(BACKEND_IMAGE):latest

	@echo "Building FRONTEND + NGINX image ($(VERSION))..."
	docker build -t $(FRONTEND_IMAGE):$(VERSION) --target prod ./XPlaneTrackerFrontend
	docker tag $(FRONTEND_IMAGE):$(VERSION) $(FRONTEND_IMAGE):latest

	@echo ""
	@echo "Images built:"
	@echo "  $(BACKEND_IMAGE):$(VERSION)"
	@echo "  $(FRONTEND_IMAGE):$(VERSION)"
	@echo ""

# -------------------------
# PUSH (DOCKER HUB)
# -------------------------
.PHONY: push
push:
	@echo "Pushing BACKEND image..."
	docker push $(BACKEND_IMAGE):$(VERSION)
	docker push $(BACKEND_IMAGE):latest

	@echo "Pushing FRONTEND image..."
	docker push $(FRONTEND_IMAGE):$(VERSION)
	docker push $(FRONTEND_IMAGE):latest

	@echo "Images pushed to Docker Hub."

# -------------------------
# RELEASE (BUILD + PUSH)
# -------------------------
.PHONY: release
release: build push
	@echo ""
	@echo "Release completed:"
	@echo "  $(BACKEND_IMAGE):$(VERSION)"
	@echo "  $(FRONTEND_IMAGE):$(VERSION)"
	@echo ""

# -------------------------
# PROD
# -------------------------
.PHONY: prod-up
prod-up:
	docker compose -f $(COMPOSE_PROD) up

.PHONY: prod-up-d
prod-up-d:
	docker compose -f $(COMPOSE_PROD) up -d

.PHONY: prod-down
prod-down:
	docker compose -f $(COMPOSE_PROD) down

.PHONY: prod-down-v
prod-down-v:
	docker compose -f $(COMPOSE_PROD) down -v

.PHONY: prod-db-seed
prod-db-seed:
	docker compose -f $(COMPOSE_PROD) run --rm artisan db:seed

.PHONY: prod-pull
prod-pull:
	docker compose -f $(COMPOSE_PROD) pull

# -------------------------
# UTILS
# -------------------------
.PHONY: logs
logs:
	docker compose -f $(COMPOSE_PROD) logs -f

.PHONY: ps
ps:
	docker compose ps

# -------------------------
# CODE FORMAT
# -------------------------
.PHONY: prettier
prettier:
	@echo "Formatting frontend..."
	cd frontend && npx prettier --write "**/*.{vue,js,ts,json}"

	@echo "Formatting websocket..."
	cd websocket && npx prettier --write "**/*.{js,ts,json}"

	@echo "Done."