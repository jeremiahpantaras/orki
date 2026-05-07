"use client";

import { GoogleAuthProvider, signInWithPopup, signOut } from "firebase/auth";

import { auth } from "@/shared/firebase/client";

const googleProvider = new GoogleAuthProvider();

export async function signInWithGoogle() {
  return signInWithPopup(auth, googleProvider);
}

export async function logout() {
  return signOut(auth);
}
