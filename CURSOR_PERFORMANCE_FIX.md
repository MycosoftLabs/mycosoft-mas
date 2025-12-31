# Cursor Performance & Stability Fixes

## Issues Identified

Cursor was crashing due to:

1. **TypeScript processing too many files**: The `tsconfig.json` was using a broad `**/*.ts` pattern that attempted to process thousands of files from Python directories, logs, data files, Docker volumes, and other non-TypeScript code.

2. **File watcher overload**: Cursor was watching all files in the workspace, including frequently changing large directories (logs, data, node_modules, build artifacts, Python virtual environments, etc.), causing excessive CPU and memory usage.

3. **No memory limits**: TypeScript language server had no memory constraints, allowing it to consume unlimited resources.

4. **Inefficient file processing**: No exclusions for large directories that don't contain TypeScript code.

## Fixes Applied

### 1. Optimized `tsconfig.json`

**Changes:**
- Changed include patterns from `**/*.ts` and `**/*.tsx` to specific directory patterns:
  - `app/**/*.ts` and `app/**/*.tsx` (Next.js app directory)
  - `components/**/*.ts` and `components/**/*.tsx` (React components)
  - `lib/**/*.ts` and `lib/**/*.tsx` (library code)
  - `middleware.ts` (Next.js middleware)
  - `.next/types/**/*.ts` (Next.js generated types)
  
- Added comprehensive exclude list for non-TypeScript directories:
  - Build artifacts (`.next`, `dist`, `build`, `out`, `coverage`)
  - Python code (`mycosoft_mas`, `orchestrator-myca`, `venv*`, `__pycache__`)
  - Logs and data (`logs`, `data`, `*.log`)
  - Infrastructure (`docker`, `grafana`, `prometheus`, `redis`, `n8n`, `infra`)
  - Other projects (`unifi-dashboard`, `WEBSITE`)
  - System files (`migrations`, `models`, `contracts`, `services`, `agents`, `scripts`, `tests`, `docs`, `plugins`, `secrets`, `speech`, `static`)

- Added `maxNodeModuleJsDepth: 1` to limit module resolution depth

### 2. Enhanced `.cursor/settings.json`

**Added optimizations:**
- File watcher exclusions for all large/dynamic directories
- TypeScript server memory limit: `4096 MB`
- TypeScript watch options to exclude directories from file watching
- Disabled auto-imports and file move imports (reduces CPU usage)
- Increased editor tokenization limit for large files
- Increased max memory for large files to 4096 MB

### 3. Enhanced `.vscode/settings.json`

Applied the same optimizations for consistency across editors.

## Expected Improvements

1. **Reduced memory usage**: TypeScript will only process relevant TypeScript files (estimated 90%+ reduction in files processed)

2. **Faster startup**: Cursor will start faster as it won't index thousands of unnecessary files

3. **Reduced CPU usage**: File watchers will ignore directories that change frequently but aren't relevant

4. **Stability**: Memory limits prevent the TypeScript server from consuming all available RAM

5. **Better performance**: More targeted file processing means faster IntelliSense and code navigation

## Next Steps

1. **Restart Cursor completely** (close all windows and restart the application)

2. **Clear TypeScript cache** (optional, if issues persist):
   - Delete `.next` directory if it exists
   - Restart Cursor

3. **Monitor performance**: The editor should now be stable and responsive

## Configuration Files Modified

- `tsconfig.json` - TypeScript compiler configuration
- `.cursor/settings.json` - Cursor-specific settings
- `.vscode/settings.json` - VSCode/Cursor workspace settings

All changes are backwards compatible and won't affect your code - they only reduce what Cursor processes internally.

