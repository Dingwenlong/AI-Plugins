# Config Rules

Runtime use: load only for appsettings, external endpoints, third-party service settings, or environment-specific configuration.

- Follow existing `appsettings.{Environment}.json` and section naming conventions.
- Do not invent a new config file name unless handoff or repository convention requires it.
- Keep endpoint, credential, and environment-sensitive values out of business code.
- For large third-party settings, require handoff or repository evidence before splitting files.
- Block when a required endpoint, key, or environment section is missing.
