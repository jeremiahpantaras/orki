"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import type { SessionUser } from "@/shared/types/session";
import { getSession, loginWithBackend } from "@/shared/api/auth";

interface AuthContextValue {
  user: SessionUser | null;
  loading: boolean;
  /** Update the in-memory user after a login or profile patch. */
  setUser: (user: SessionUser | null) => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  setUser: () => {},
});

export function useAuthContext(): AuthContextValue {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);

  const setUser = useCallback((u: SessionUser | null) => setUserState(u), []);

  useEffect(() => {
    // Subscribe to Firebase Auth state.  Fires immediately on mount (from
    // IndexedDB persistence) and again after every sign-in / sign-out.
    // On every page load — including after a deploy — this restores the
    // auth state without touching any backend database.
    let unsubscribe: (() => void) | undefined;

    import("@/shared/firebase/client").then(({ auth }) => {
      import("firebase/auth").then(({ onAuthStateChanged }) => {
        unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
          if (!firebaseUser) {
            setUserState(null);
            setLoading(false);
            return;
          }

          try {
            // Try to load the existing Firestore profile
            const data = await getSession();
            setUserState(data.user);
          } catch {
            // New user or profile missing — create it via login endpoint
            try {
              const data = await loginWithBackend();
              setUserState(data.user);
            } catch {
              setUserState(null);
            }
          } finally {
            setLoading(false);
          }
        });
      });
    });

    return () => unsubscribe?.();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

