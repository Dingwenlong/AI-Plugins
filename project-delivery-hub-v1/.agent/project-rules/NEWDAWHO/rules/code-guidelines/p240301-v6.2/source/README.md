# V6.2 Source Status

The original user-provided file has a `.docx` suffix but is an old Office OLE/DRM-style container. It is not a readable OpenXML DOCX and should not be loaded at runtime.

Before adding detailed V6.2 content, convert the guideline into readable Markdown or JSON, then split it into `catalog.json` and `rules/*.md` entries. Runtime selection must read the catalog first and load only selected rule files.
