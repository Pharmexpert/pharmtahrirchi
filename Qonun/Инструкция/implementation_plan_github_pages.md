# [Implementation Plan: Next.js GitHub Pages Integration] (Monorepo)

The goal is to automate the deployment of the Next.js frontend to GitHub Pages using GitHub Actions, while accounting for the project's monorepo structure where the frontend resides in the `frontend/` directory.

## User Review Required

> [!IMPORTANT]
> **Static Export Only**: GitHub Pages only hosts static files. Your Next.js app must be configured for **Static Export** (`output: 'export'`). Server-side features (API routes, SSR) will not work on GitHub Pages.
> **Backend Communication**: Since the backend (FastAPI) is NOT hosted on GitHub Pages, the deployed frontend will attempt to connect to `http://localhost:8000` by default. You will need to host your backend on a platform like **Render**, **Railway**, or **PythonAnywhere** for the live site to be fully functional.

## Proposed Changes

### Frontend: Configuration for Static Export

#### [MODIFY] [next.config.js](file:///c:/Users/Администратор/Desktop/2/frontend/next.config.js)
- Set `output: 'export'` to enable static HTML/CSS/JS generation.
- Add `images: { unoptimized: true }` (required for static exports on Pages).

### GitHub Actions: CI/CD Workflow

#### [NEW] [.github/workflows/nextjs.yml](file:///c:/Users/Администратор/Desktop/2/.github/workflows/nextjs.yml)
- Adapt your provided YAML to work with the `frontend/` subdirectory.
- **Key Adjustments**:
  - `working-directory: ./frontend` for all build and install steps.
  - Deployment path: `./frontend/out`.

## Open Questions

- Do you have a public URL for your FastAPI backend yet? If so, I can configure the CI/CD to inject the `NEXT_PUBLIC_API_URL` during the build process.

## Verification Plan

### Manual Verification
- After we push the changes to GitHub, you will see a new run in the **Actions** tab of your repository. 
- Once the "Deploy" job finishes, your site will be live at `https://pharmexpert.github.io/pharmtahrirchi/`.
- Check the console for any "Mixed Content" or "CORS" errors if the backend is not yet hosted over HTTPS.
