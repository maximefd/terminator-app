"use client";

import { useEffect } from "react";
import { initMonitoring } from "@/lib/monitoring";

/** Active le suivi des erreurs du navigateur si le build a reçu un DSN Sentry (voir lib/monitoring.ts). */
export function MonitoringInit() {
  useEffect(() => {
    initMonitoring(process.env.NEXT_PUBLIC_SENTRY_DSN);
  }, []);
  return null;
}
