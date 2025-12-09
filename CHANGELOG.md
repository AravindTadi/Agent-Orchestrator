# Changelog - UI/UX Enhancements

## [Unreleased]

### Added
- **Global Profile Menu**: Added a consistent profile dropdown menu across all pages (`orchestrator.html`, `index.html`, `analytics.html`, `integrations.html`, `chat.html`).
  - Includes links to Settings, Region, API Keys, and Logout.
  - Includes a theme toggle switch.
- **Light Mode Default**: Changed the default theme to 'light' for a more professional look.
- **SVGs**: Replaced all emojis with professional SVG icons across the application.

### Changed
- **Theme Toggle**: Moved the theme toggle from the top navbar to the profile dropdown menu.
- **Navbar**: Standardized the top navbar across all pages.
- **Typography**: Updated font to 'IBM Plex Sans' for a cleaner, more modern aesthetic.
- **Colors**: Refined the color palette in `style.css` for better contrast and visual appeal in both light and dark modes.
- **Login Page**: Removed emojis and updated icons to SVGs.

### Fixed
- **Inline Scripts**: Cleaned up inline scripts in `integrations.html` and `analytics.html` to reduce code duplication and rely on `script.js`.
- **Icon Consistency**: Ensured consistent icon usage for file types and UI elements.
