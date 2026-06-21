@ECHO OFF
REM ============================================================================
REM  hugo.start.cmd
REM ----------------------------------------------------------------------------
REM  Reference sheet for starting the Hugo development server locally.
REM
REM  This file is for REFERENCE ONLY. It is not wired into the build or deploy
REM  pipeline and runs nothing on its own. Copy the command you need from the
REM  list below and run it from this directory (the Hugo site root).
REM
REM  Site root (folder containing hugo.toml): this directory
REM  Local preview URL once running:          http://localhost:1313/
REM
REM  Copyright (c) TACE Data Management Inc.
REM ============================================================================

REM --- Command reference ------------------------------------------------------
REM  hugo server                      Build, serve at :1313, live-reload on save
REM  hugo server -D                   Include draft content
REM  hugo server -D -F                Include drafts AND future-dated posts
REM  hugo server --port 8080          Serve on a different port
REM  hugo server --bind 0.0.0.0       Expose to other devices on the LAN
REM  hugo server --navigateToChanged  Auto-jump the browser to the edited page
REM  hugo server --disableFastRender  Force full rebuilds (fixes stale renders)
REM ----------------------------------------------------------------------------
