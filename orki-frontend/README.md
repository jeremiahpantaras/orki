# Orki Frontend

Next.js App Router frontend for Orki, built with TypeScript and Tailwind CSS.

## Stack

- Next.js (App Router)
- TypeScript (strict)
- Tailwind CSS v4

## Run Locally

1. Copy env values:

```bash
cp .env.example .env.local
```

2. Install dependencies:

```bash
npm install
```

3. Run dev server:

```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000)

## Scripts

- `npm run dev` - start development server
- `npm run build` - build production bundle
- `npm run start` - run production server
- `npm run lint` - run ESLint checks
- `npm run typecheck` - run TypeScript checks

## Project Structure

```text
src/
  app/
    (auth)/
      login/page.tsx
      register/page.tsx
    (main)/
      layout.tsx
      dashboard/page.tsx
      analytics/page.tsx
      exams/page.tsx
      flashcards/page.tsx
      profile/page.tsx
    globals.css
    layout.tsx
    page.tsx
  entities/
    analytics/types.ts
    dashboard/types.ts
    exams/types.ts
    flashcards/types.ts
  features/
    navigation/nav-items.ts
  shared/
    api/http.ts
    api/study.ts
    config/env.ts
    config/routes.ts
    types/api.ts
  widgets/
    app-shell/app-shell.tsx
```

## API Integration

- Backend base URL is read from `NEXT_PUBLIC_API_URL`.
- API helpers are centralized in `src/shared/api`.
- Domain-facing data types live in `src/entities`.

## Firebase Setup (Auth + Firestore)

This project is now wired to Firebase using:

- `src/shared/firebase/client.ts` for app initialization
- `src/shared/firebase/auth.ts` for Google sign-in helpers
- `src/app/(auth)/login/page.tsx` for Google login action

### Required `.env.local` values

Copy from `.env.example` and fill:

- `NEXT_PUBLIC_FIREBASE_API_KEY`
- `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`
- `NEXT_PUBLIC_FIREBASE_PROJECT_ID`
- `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET`
- `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID`
- `NEXT_PUBLIC_FIREBASE_APP_ID`

### Step-by-step (your intervention points)

1. Open [Firebase Console](https://console.firebase.google.com/), select your project.
2. Go to **Project settings** -> **General** -> **Your apps**.
3. If no web app exists, create one (`</>` icon) and register it.
4. Copy the web config values into `orki-frontend/.env.local`.
5. In **Authentication** -> **Sign-in method**, confirm **Google** is enabled.
6. In **Authentication** -> **Settings** -> **Authorized domains**, ensure `localhost` is present.
7. In **Firestore Database**, verify DB is created in Native mode.
8. In **Firestore Database** -> **Rules**, for development allow authenticated reads/writes (or your preferred policy).
9. Restart frontend dev server after changing `.env.local`.

### Verify integration

1. Run `npm run dev`.
2. Open `/login`.
3. Click **Continue with Google**.
4. Complete Google popup sign-in.
5. If popup succeeds, Firebase Auth is linked correctly.
