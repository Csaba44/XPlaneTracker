# Translation Plan: Hungarian/Lovári to English

This plan outlines the systematic translation of the XPlaneTracker project to English, removing all Hungarian and Lovári slang as requested.

## 1. Python Desktop Client (XPlaneTracker)

### `main.py`
- [x] **Discord Webhook Title:**
  - Old: `f"{self.user_name} muro phral megérkezett, shavale!"`
  - New: `f"{self.user_name} has arrived!"`
- [x] **Discord Rich Presence Idle Details:**
  - Old: `"Repülőzzünk, shavale! 🍀"`
  - New: `"Ready for flight 🍀"`

## 2. Frontend (XPlaneTrackerFrontend)

### Components
- [x] `EditFlightModal.vue`:
  - "Járat Szerkesztése" -> "Edit Flight"
  - "Mégse" -> "Cancel"
  - "Mentés" -> "Save"
- [x] `FlightFilters.vue`:
  - "Keresés globálisan..." -> "Search globally or with tags (e.g. dep:LHBP callsign:RYR)..."
  - "Szűrő címke hozzáadása" -> "Add filter tag"
  - "Elérhető Címkék" -> "Available Tags"
  - "Keresés törlése" -> "Clear search"
  - "Találat:" -> "Results:"
  - "Összesen:" -> "Total:"
- [x] `FlightMap.vue`:
  - "Rétegek" -> "Layers"
  - "Sötét" -> "Dark"
  - "Műhold" -> "Satellite"
  - "Pályák" -> "Runways"
  - "Gurulóutak" -> "Taxiways"
  - "Állóhelyek" -> "Stands"
  - "Események" -> "Events"
- [x] `ProfileModal.vue`:
  - "Új jelszó" -> "New password"
  - "hagyd üresen a régihez" -> "leave empty to keep current"
  - "Mégse" -> "Cancel"
  - "Mentés" -> "Save"
- [x] `UserProfilePanel.vue`:
  - "Szia testvér!" -> "Welcome back!"
  - "Járatok" -> "Flights"
  - "Közösség" -> "Community"
  - "Barátok" -> "Friends"
  - "Eszközök" -> "Tools"
  - "Töltöm teso..." -> "Uploading..."
  - "Vigyázz rá testvérem, el ne lopják!" -> "Keep your account secure!"

### Views
- [x] `CommunityView.vue`:
  - "Vágólapra másolva." -> "Copied to clipboard."
  - "Profil sikeresen frissítve." -> "Profile updated successfully."
  - "Hiba a profil frissítésekor." -> "Error updating profile."
  - "SHAVALE" -> "COMMUNITY"
  - "Muro phralenge 🍀" -> "For the community 🍀"
  - "Még egy barátod sem repült..." -> "None of your friends have flown yet..."
  - "Nem találtam ilyet muro phral" -> "No results found"
- [x] `FlightView.vue`:
  - "Járat sikeresen frissítve." -> "Flight updated successfully."
  - "Hiba a járat frissítésekor." -> "Error updating flight."
  - "Biztosan törölni akarod ezt a járatot?" -> "Are you sure you want to delete this flight?"
  - "Járat sikeresen törölve." -> "Flight deleted successfully."
  - "Hiba történt a törlés során." -> "Error occurred during deletion."
  - "Keresem tesó, várj egy picit..." -> "Searching, please wait..."
- [x] `FriendsView.vue`:
  - "Hiba a barátok betöltésekor." -> "Error loading friends."
  - "Barátkérelem elküldve!" -> "Friend request sent!"
  - "Kérelem elfogadva!" -> "Request accepted!"
  - "Kérelem elutasítva." -> "Request declined."
  - "Biztosan törlöd ezt a testvért a listádról?" -> "Are you sure you want to remove this friend?"
  - "Testvér törölve." -> "Friend removed."
  - "BARÁTOK" -> "FRIENDS"
  - "Vissza a járatokhoz" -> "Back to flights"
  - "Kérelmek:" -> "Requests:"
  - "Barátnak jelölt" -> "Requested"
  - "Hozzáadva:" -> "Added:"
  - "Nincsenek barátaid." -> "You have no friends yet."
  - "Új Testvérek Keresése" -> "Search for Friends"
  - "Írd be a nevet vagy email címet a kereséshez." -> "Enter name or email to search."
  - "Keresés név vagy email alapján..." -> "Search by name or email..."
  - "Nem találtam ilyet tesó." -> "No results found."
  - "Barát" -> "Friend"
  - "Függőben" -> "Pending"
  - "Hozzáadás" -> "Add Friend"
- [x] `HomeView.vue`:
  - "Volanta gipsy verzió a széptestvéreknek" -> "CSABOLANTA - Flight Tracking Reimagined"
  - "Zha tar aba ando Pilótafülke muro phral" -> "Enter the Cockpit"
  - "Szeretem a pénzt" -> "Support the project"
  - "Báttya, 8 eurot fizetek havonta..." -> "We pay 8 euros monthly for the server. Support the project to keep it running!"
  - "Támogatás" -> "Support"
- [x] `LeaderboardView.vue`:
  - "Hiba a ranglista betöltésekor." -> "Error loading leaderboard."
  - "Az elmúlt 30 nap statisztikái" -> "Statistics for the last 30 days"
  - "Adatok betöltése..." -> "Loading data..."
  - "Nincs elég adat a leszállási ranglistához." -> "Not enough data for the landing leaderboard."
- [x] `LoginView.vue`:
  - "Hibás felhasználónév vagy jelszó! Jo hulye vagy." -> "Invalid username or password."
  - "Varjal teso mindjart..." -> "Please wait..."
  - "Zha tar aba muro phral, megyunk repulozni" -> "Log in and let's go flying"

## 3. Backend (XPlaneTrackerAPI)
- [x] Verified: Code already uses English for response messages.

## 4. Documentation
- [x] Update `CLAUDE.md` to reflect that the application is now in English and remove the Hungarian/Lovári note.

## Verification
- [ ] Run grep again for Hungarian characters and slang terms to ensure nothing was missed.
