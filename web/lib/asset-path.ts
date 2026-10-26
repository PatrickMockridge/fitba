export function assetPath(path: string): string {
  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  const value = path.startsWith("/") ? path : `/${path}`;
  return `${base}${value}`;
}
