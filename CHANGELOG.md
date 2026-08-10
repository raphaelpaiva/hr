## v0.3.0 (2026-08-10)

### Feat

- **takes**: play each take recording inline to verify capture
- **settings**: name USB devices to label downloaded wavs
- **takes**: click-to-rename takes and name ZIPs after them
- **session**: auto-name sessions with date/time when blank
- **ui**: make main screen the new-session recording screen

## v0.2.0 (2026-08-08)

### Feat

- **storage**: collapse recordings into sessions root with migration
- **dashboard**: unify quick record into anonymous sessions
- **sessions**: persist sessions to disk
- **scripts**: accept --host and --port parameters
- **ui**: responsive header and mobile card layouts

## v0.1.0 (2026-08-02)

### Feat

- **ui**: dark design system, session takes, tests, and Python 3.9 support
- Introduces Sound Systems and error handling
- Makes hr a standalone package
- **UI**: Only shows plughw devices for convenience.
- Add header with system health informantion
- interface revamp
- Adds history listing.
- add shutdown endpoint and button for system shutdown
- add development script for setting up virtual environment and running FastAPI
- add installation script and service configuration
- enhance UI and functionality for recording management with improved layout and state indicators
- implement recording functionality with device management and history tracking
- Choose audio device

### Fix

- History wont throw error when recordings directory doesnt exists.
- Alsa should be the default system.
- brain fart.
- show dates correctly
- show full name of sound devices
- virtualenv is not available as a command in the pi3
- ensure virtualenv installation is included in the setup script
- update service configuration for user and working directory

### Refactor

- separate javascript from page.
- Refactor and reorganize project structure with new modules for recording, sound devices, and system information
