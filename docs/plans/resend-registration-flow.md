# Resend Registration Flow Plan

## Overview
The goal is to transition from a manual user creation process (where administrators set passwords) to an invite-based flow using Resend. Administrators will invite users via email, and the system will email a secure registration link to the invited user.

## 1. Database Schema Updates
- **New Migration**: `create_user_invites_table`
  - `id` (primary key)
  - `email` (string, unique)
  - `name` (string, nullable)
  - `is_admin` (boolean, default false)
  - `token` (string, unique) - A secure random 32-character token.
  - `invited_by` (foreignId to `users.id`)
  - `created_at` & `updated_at` timestamps.

## 2. Backend API Changes (`XPlaneTrackerAPI`)
### 2.1 Dependencies
- No new packages strictly required; Laravel's HTTP Client (`Http::withToken()`) is sufficient to interact with the Resend API, avoiding additional composer dependencies.

### 2.2 Controller Updates
- **`AdminUserController@store`**:
  - **Validation**: Change to require `email`, optional `name`, and boolean `is_admin`. Remove the `password` requirement.
  - **Logic**:
    - Generate a secure token: `$token = Str::random(32);`
    - Store the invite in the `user_invites` table.
    - Send an email using Resend via the `Http` facade:
      - **Endpoint**: `POST https://api.resend.com/emails`
      - **Bearer Token**: `re_`
      - **From**: `Csabolanta Invites <onboarding@csabolanta.hu>`
      - **To**: `[$request->email]`
      - **Subject**: `Join Csabolanta!`
      - **HTML**: Include a styled message stating `{$request->user()->name} has invited you to join Csabolanta.` along with a primary button linking to `http://xtracker.local:5173/register?token={$token}` and a plaintext fallback link.
  - Return a 201 Created response.

### 2.3 New Endpoints
- **`GET /api/invites/{token}`**:
  - Validates the token exists in `user_invites`. Returns the invite details (e.g., `email`, `name`) to pre-fill the frontend registration form.
- **`POST /api/register`**:
  - **Validation**: Requires `token`, `name`, `password` (min 8, confirmed).
  - **Logic**:
    - Finds the invite by `token`.
    - Creates the final `User` record using the invite's `email`, `is_admin` status, and the user-provided `name` and `password`.
    - Deletes the invite record from `user_invites`.
    - Returns a 201 Created response so the frontend can redirect to the login page.

## 3. Frontend Changes (`XPlaneTrackerFrontend`)
### 3.1 Admin Panel (`AdminView.vue`)
- **Modification**: The "Add User" modal will be updated to only ask for an `email`, an optional `name`, and the `Grant Admin Privileges` checkbox. The `password` field will be removed entirely for new users. *(This step has been implemented as requested).*

### 3.2 Registration Page (`RegisterView.vue`)
- **Route**: Create a new route `/register`.
- **Logic**:
  - Read `?token=` from the URL query parameters.
  - On mount, fetch the invite details from `GET /api/invites/{token}` to optionally pre-fill the `name` field if the admin provided one.
- **Form UI**:
  - Inputs for `Name` (pre-filled if available, but editable).
  - Inputs for `Password` and `Confirm Password`.
  - Submit button to finalize registration via `POST /api/register`.
  - On success, redirect to `/login`.
