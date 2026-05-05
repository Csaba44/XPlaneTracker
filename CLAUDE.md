# Project Overview

Csabolanta (XPlaneTracker) is a full-stack flight tracking platform for X-Plane and MSFS. It consists of a web dashboard for flight telemetry analysis and community features (friend systems, leaderboards), powered by a Laravel backend and a Vue 3 frontend, along with a standalone Python desktop client that connects to the simulators and streams telemetry data to the API.

## Repository & File Structure

The project is divided into distinct domains:

- `@/XPlaneTracker/`: The Python-based desktop client application (GUI, telemetry extraction).
- `@/XPlaneTrackerAPI/`: The Laravel PHP backend.
- `@/XPlaneTrackerFrontend/`: The Vue 3 SPA frontend.
- `@/docker/`: Nginx and PHP configuration files for development and production.
- `@/jetphotos-worker/`: **[IGNORE]** Do not inspect or modify this directory unless explicitly instructed to do so.

## Tech Stack

- **Desktop Client:** Python 3 utilizing `customtkinter` for the GUI. It interfaces with MSFS via `SimConnect` and X-Plane via UDP (`XPlaneConnectX`). It handles Discord Rich Presence (`pypresence`) and packages flight data into compressed JSON `.gz` payloads. Compiled via `PyInstaller`.
- **Frontend:** Vue 3 (Composition API & `<script setup>`), Pinia (State), Vue Router, Tailwind CSS (custom dark theme), Leaflet.js (Mapping), and Apache ECharts (`vue-echarts`).
- **Backend:** Laravel (PHP) using Eloquent ORM and Sanctum for token/cookie-based auth.

## Environment & Docker Architecture

The web stack utilizes a comprehensive multi-container Docker setup tailored for both development (`docker-compose.dev.yml`) and production (`docker-compose.prod.yml`).

- **Services:** Isolates concerns into `mysql`, `backend` (PHP-FPM), `nginx`, `frontend` (Vite dev server), and a dedicated `artisan` container for safe CLI execution.
- **Nginx & PHP Tuning:** Custom configurations handle routing, WebSocket proxying, and Cloudflare Origin Certificates.

## Development Workflow (Make & Artisan)

The web application leverages a `Makefile` to streamline Docker orchestration.

- **Key Make Commands:** `make dev-up` (start dev stack), `make dev-down` (stop dev stack), `make migrate` (run database migrations).
- **The Artisan Wrapper:** Laravel's Artisan CLI is wrapped in a local bash script (`./artisan`) that automatically forwards commands into the isolated `xtracker_artisan` Docker container.

## Python Client Development (venv & PyInstaller)

- **Virtual Environment:** All Python development must be executed within the local virtual environment located at `/XPlaneTracker/.venv`. To activate it, use the command: `source .venv/bin/activate`.
- **Providers Architecture:** Simulator connections extend from `BaseProvider` (`base_provider.py`). `MSFSProvider` utilizes the `SimConnect` library, while `XPlaneProvider` monitors UDP datarefs through `XPlaneConnectX.py`.
- **Build Process:** The application is compiled into a standalone executable using PyInstaller via the provided `CSABOLANTA.spec` file, which explicitly handles hidden imports and library assets (like `customtkinter`).

## CI/CD Workflow (GitHub Actions)

- **Automated Releases:** The repository uses a GitHub Actions workflow (`Build and Release EXE`) to automate the building and releasing of the Python desktop client[cite: 19].
- **Triggers:** The workflow is triggered automatically whenever a new version tag (e.g., `v*`) is pushed to the repository[cite: 19].
- **Build Environment:** It runs on a `windows-latest` environment using Python 3.11[cite: 19].
- **Secrets Injection:** Required secrets, such as the Discord Webhook URL and Client ID, are automatically injected into the `.env` file during the build process[cite: 19].
- **Compilation & Publishing:** The workflow installs all necessary dependencies, compiles the application using PyInstaller in `--onedir` mode[cite: 19], zips the output directory[cite: 19], and publishes the archive as a GitHub Release[cite: 19].

---

## AI Development Guidelines (Instructions for Claude)

- **Code Generation Constraints:**
  - **DO NOT WRITE COMMENTS.** Only write comments in the code in extremely exceptional cases where the logic is impossibly complex without it. Keep the code clean and self-documenting.
- **Backend & CLI Conventions:**
  - Always use the local wrapper for artisan commands. **Never** use `php artisan <command>`. You must use `./artisan <command>` (e.g., `./artisan make:controller FlightController`).
  - Follow standard Laravel controller patterns. Ensure all API endpoints are protected by appropriate middleware or authorization checks.
  - Heavily utilize Laravel's `Cache` facade to minimize external API rate-limiting.
- **Frontend Conventions:**
  - Strictly adhere to the Vue 3 Composition API using `<script setup>`.
  - Maintain the current separation of concerns: use composables for complex logic and mathematics outside of the UI components.
  - Whenever you are asked to create or modify a Vue component, you **MUST** read the .claude/skills/design file first. Strictly apply the Tailwind classes, color variables, and typography rules defined there.

* **Python Conventions:**
  - Assume execution from within the `.venv`. Do not modify the `CSABOLANTA.spec` file unless adding new explicit data dependencies or hidden imports.
  - Maintain the `BaseProvider` abstract class structure when dealing with simulator telemetry.
  - **Dependency Management:** If you add new Python dependencies, you **MUST** add them to the `pip install` step in `release.yml` to guarantee a successful build. If PyInstaller struggles to find them, you must also add them as hidden imports in `CSABOLANTA.spec` to prevent runtime errors.

- **UI Text & Language (Critical):**
  - All user-facing text, notifications, and error messages must be written in English.
  - The application has been fully translated from Hungarian/Lovári slang to professional English.
  - Maintain this English-only standard for all new features and text.

## Flight Telemetry Data Schema

You can find an example of the flight data structure located at: `.claude/example-flight/flight_UAE76J_20260502_083528.json`

**Note:** In the actual application, these flight logs are always compressed and stored as `.json.gz` files. The provided example is uncompressed and has its telemetry data points severely truncated for ease of use and readability.

The JSON schema consists of three main sections:

- **`metadata`**: An object containing the flight's core details (`callsign`, `flight_number`, `airline`, `aircraft_registration`, `aircraft_type`, `route`, `simulator`, and `start_time`). It also includes a `columns` array that strictly defines the order of the telemetry values in the `path` section.
- **`path`**: A large array of arrays. Each inner array represents a single telemetry snapshot in time, mapped directly to the `columns` definition (e.g., `[timestamp, lat, lon, alt, speed]`).
- **`landings`**: An array of objects tracking touchdown events. Each object contains the `timestamp`, vertical speed (`fpm`), `g_force`, `lat`, `lon`, plus optional `pitch`, `roll`, `ias`, `gs`, `airport_icao`, `airport_name`, `runway_ident`, `touchdown_offset_m`, `rollout_m`.
- **`events`**: An array of state-machine events emitted by `flight_state.py`. Each entry has `ts` (Unix seconds) and `type`, plus type-specific extras. Types: `engine_start` / `engine_shutdown` (`engine`), `liftoff` (`pitch`, `max_pitch_10s`, `roll`, `ias`, `gs`, `alt`), `touchdown`, `bounce` (`gs`, `ias`), `gear_up` / `gear_down` (`alt`, `ias`), `flaps_set` (`index`), `stall` (`alt`, `ias`, `pitch`), `touch_and_go` (`gs`), `phase_change` (`phase`).
- **`phases`**: An array of flight-phase segments. Each entry has `type` (one of `taxi_out`, `climb`, `cruise`, `descent`, `approach`, `taxi_in`), `start`, `end`, and optional `peak_alt`.

**Maintenance Rule for Claude:** Whenever you implement new data points, alter the telemetry schema, or add new core features to the application, you **MUST** update this `CLAUDE.md` document to ensure the project context remains perfectly fresh and accurate for future sessions.

## Core Directive: Write Plans to Files

Whenever the user asks you to create a plan, design a feature, or outline steps for a task, **do not just output the plan in the terminal or chat interface**.

Instead, you must write the plan to a Markdown file within the `@docs/plans` folder. This allows the user to read, review, and track progress without having to scroll through terminal logs, and creates a permanent history of project plans.

# Further AI instructions

Populate and maintain CLAUDE.md with all relevant project-wide context so you can resume work efficiently without me repeating context each session. Include:

- Project summary & active features
- Tech stack
- Code style & naming conventions
- Known bugs and next TODOs
- Test scenarios we haven’t completed yet (if any) Keep it under 5k tokens total.

If it becomes impossible to keep all relevant info under 5k tokens, split less critical sections into separate files under the docs/ directory. For example, if there are details about a future system version (e.g., MK2), create a separate markdown file like docs/mk2_notes.md instead of bloating CLAUDE.md.
