export function hasPermission(permissionCode: string, permissions: string[] | null | undefined): boolean {
  const normalizedCode = permissionCode.trim();
  if (!normalizedCode || !permissions?.length) {
    return false;
  }

  return permissions.includes(normalizedCode);
}
