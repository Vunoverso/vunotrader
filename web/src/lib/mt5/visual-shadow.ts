import { createAdminClient } from "@/lib/supabase/admin";

export const MT5_VISUAL_BUCKET =
  process.env.NEXT_PUBLIC_MT5_VISUAL_BUCKET ??
  process.env.MT5_VISUAL_BUCKET ??
  "mt5-visual-captures";

export async function signVisualStoragePaths(
  paths: Array<string | null | undefined>,
  expiresInSeconds = 1800
): Promise<Record<string, string | null>> {
  const uniquePaths = Array.from(new Set(paths.filter((path): path is string => Boolean(path))));
  if (uniquePaths.length === 0) {
    return {};
  }

  const admin = createAdminClient();
  const entries = await Promise.all(
    uniquePaths.map(async (path) => {
      const { data, error } = await admin.storage
        .from(MT5_VISUAL_BUCKET)
        .createSignedUrl(path, expiresInSeconds);

      return [path, error ? null : data.signedUrl] as const;
    })
  );

  return Object.fromEntries(entries);
}